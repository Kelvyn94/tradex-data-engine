"""
Intelligent rate limiter for API services.
Distributes requests evenly throughout the day to avoid hitting limits.
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging
from collections import deque

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Intelligent rate limiter that distributes requests evenly.
    Prevents hitting daily limits by spacing requests throughout the day.
    """
    
    def __init__(self, service_name: str, daily_limit: int, 
                 min_interval: float = 1.0, start_hour: int = 0, end_hour: int = 23):
        """
        Initialize rate limiter.
        
        Args:
            service_name: Name of the service (for logging)
            daily_limit: Maximum requests per day
            min_interval: Minimum seconds between requests
            start_hour: Hour to start counting (0-23)
            end_hour: Hour to stop counting (0-23)
        """
        self.service_name = service_name
        self.daily_limit = daily_limit
        self.min_interval = min_interval
        self.start_hour = start_hour
        self.end_hour = end_hour
        
        # Tracking
        self.requests_today = 0
        self.last_request_time = 0
        self.request_times = deque(maxlen=daily_limit)
        self.reset_time = datetime.now().replace(hour=start_hour, minute=0, second=0, microsecond=0)
        
        # Lock for thread safety
        self.lock = threading.Lock()
        
        # Calculate optimal interval
        self.optimal_interval = self._calculate_optimal_interval()
        
        logger.info(f"RateLimiter initialized for {service_name}: "
                   f"limit={daily_limit}, interval={self.optimal_interval:.1f}s")
    
    def _calculate_optimal_interval(self) -> float:
        """Calculate optimal interval to evenly distribute requests."""
        # Hours available in a day
        active_hours = self.end_hour - self.start_hour + 1
        if active_hours <= 0:
            active_hours = 24
        
        # Total seconds in active period
        active_seconds = active_hours * 3600
        
        # Optimal interval = total seconds / daily limit
        interval = active_seconds / self.daily_limit
        
        # Ensure minimum interval
        return max(interval, self.min_interval)
    
    def _is_reset_time(self) -> bool:
        """Check if we should reset the counter."""
        now = datetime.now()
        reset_time = now.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
        
        # If current time is after reset time and last reset was before
        if now >= reset_time and self.reset_time < reset_time:
            return True
        
        # If we crossed midnight
        if now.date() != self.reset_time.date():
            return True
        
        return False
    
    def _reset_if_needed(self):
        """Reset counter if needed."""
        if self._is_reset_time():
            with self.lock:
                self.requests_today = 0
                self.request_times.clear()
                self.reset_time = datetime.now().replace(
                    hour=self.start_hour, minute=0, second=0, microsecond=0
                )
                logger.info(f"{self.service_name} rate limit counter reset")
    
    def _get_available_today(self) -> int:
        """Get remaining requests for today."""
        self._reset_if_needed()
        return max(0, self.daily_limit - self.requests_today)
    
    def _get_wait_time(self) -> float:
        """Calculate wait time before next request."""
        now = time.time()
        
        # Check minimum interval
        elapsed = now - self.last_request_time
        if elapsed < self.min_interval:
            return self.min_interval - elapsed
        
        # Check if we're approaching the limit
        remaining = self._get_available_today()
        if remaining <= 0:
            # Wait until next day or reset time
            now_dt = datetime.now()
            reset_dt = now_dt.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
            if now_dt >= reset_dt:
                reset_dt += timedelta(days=1)
            wait_seconds = (reset_dt - now_dt).total_seconds()
            logger.warning(f"{self.service_name} daily limit reached. Next reset in {wait_seconds/3600:.1f}h")
            return wait_seconds + 60  # Add 1 minute buffer
        
        # Calculate time until next evenly spaced request
        # We want to use exactly daily_limit requests per day
        if self.requests_today > 0:
            # How many requests should we have made by now?
            now_dt = datetime.now()
            seconds_today = (now_dt - self.reset_time).total_seconds()
            expected_requests = seconds_today / self.optimal_interval
            
            # If we're ahead of schedule, wait longer
            if self.requests_today > expected_requests:
                # Wait until we're back on schedule
                wait_time = (self.requests_today * self.optimal_interval) - seconds_today
                return max(wait_time, self.min_interval)
        
        return 0
    
    def wait_if_needed(self) -> bool:
        """
        Wait if needed to stay within rate limits.
        
        Returns:
            True if request can proceed, False if limit reached
        """
        self._reset_if_needed()
        
        # Check if we have requests available
        if self._get_available_today() <= 0:
            logger.warning(f"{self.service_name} daily limit reached ({self.daily_limit})")
            return False
        
        # Calculate wait time
        wait_time = self._get_wait_time()
        
        if wait_time > 0:
            logger.debug(f"{self.service_name} rate limiting: waiting {wait_time:.1f}s")
            time.sleep(wait_time)
        
        # Record request
        with self.lock:
            self.requests_today += 1
            self.last_request_time = time.time()
            self.request_times.append(self.last_request_time)
        
        return True
    
    def get_status(self) -> Dict:
        """Get current rate limiter status."""
        self._reset_if_needed()
        remaining = self._get_available_today()
        used = self.daily_limit - remaining
        
        # Calculate usage percentage
        usage_percent = (used / self.daily_limit) * 100 if self.daily_limit > 0 else 0
        
        # Calculate time until next request if needed
        wait_time = self._get_wait_time()
        
        return {
            'service': self.service_name,
            'daily_limit': self.daily_limit,
            'requests_used': used,
            'requests_remaining': remaining,
            'usage_percent': round(usage_percent, 1),
            'optimal_interval': round(self.optimal_interval, 1),
            'wait_time_if_needed': round(wait_time, 1),
            'reset_time': self.reset_time.isoformat()
        }

class RateLimiterManager:
    """
    Manages multiple rate limiters for different services.
    """
    
    def __init__(self):
        self.limiters: Dict[str, RateLimiter] = {}
        logger.info("RateLimiterManager initialized")
    
    def register(self, service_name: str, daily_limit: int, 
                min_interval: float = 1.0) -> RateLimiter:
        """
        Register a new rate limiter.
        
        Args:
            service_name: Name of the service
            daily_limit: Maximum requests per day
            min_interval: Minimum seconds between requests
            
        Returns:
            RateLimiter instance
        """
        limiter = RateLimiter(
            service_name=service_name,
            daily_limit=daily_limit,
            min_interval=min_interval
        )
        self.limiters[service_name] = limiter
        logger.info(f"Registered rate limiter for {service_name}")
        return limiter
    
    def get_limiter(self, service_name: str) -> Optional[RateLimiter]:
        """Get a rate limiter by name."""
        return self.limiters.get(service_name)
    
    def get_all_status(self) -> Dict:
        """Get status of all limiters."""
        return {
            name: limiter.get_status() 
            for name, limiter in self.limiters.items()
        }

# Global rate limiter manager
rate_limiter_manager = RateLimiterManager()

# Register default limiters
news_limiter = rate_limiter_manager.register(
    service_name='newsapi',
    daily_limit=100,  # NewsAPI free tier
    min_interval=2.0  # Minimum 2 seconds between requests
)

fred_limiter = rate_limiter_manager.register(
    service_name='fred',
    daily_limit=1000,  # FRED free tier
    min_interval=1.0   # Minimum 1 second between requests
)