"""
AI insight generation service for market analysis.
Combines technical, sentiment, and macro insights with rate limiting.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
import time
from functools import lru_cache

from backend.services.database_service import db_service
from backend.services.sentiment_service import SentimentService
from backend.services.macro_service import MacroService
from backend.indicators import calculate_sma, calculate_rsi, calculate_macd, calculate_bollinger

logger = logging.getLogger(__name__)

class AIInsightService:
    """Service for generating AI-powered market insights with rate limiting."""
    
    def __init__(self):
        self.insight_types = [
            'TREND', 'REVERSAL', 'BREAKOUT', 'VOLATILITY', 
            'SUPPORT_RESISTANCE', 'DIVERGENCE', 'PATTERN',
            'SENTIMENT', 'MACRO'
        ]
        # Rate limiting settings
        self.last_request_time = {}
        self.min_request_interval = 2  # seconds between requests to same API
        logger.info("AI Insight Service initialized with rate limiting")
    
    def _rate_limit(self, service_name: str):
        """Apply rate limiting to prevent API throttling."""
        current_time = time.time()
        if service_name in self.last_request_time:
            elapsed = current_time - self.last_request_time[service_name]
            if elapsed < self.min_request_interval:
                wait_time = self.min_request_interval - elapsed
                logger.debug(f"Rate limiting {service_name}: waiting {wait_time:.1f}s")
                time.sleep(wait_time)
        self.last_request_time[service_name] = current_time
    
    def generate_enhanced_insights(self, asset: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Generate enhanced insights combining technical, sentiment, and macro.
        """
        all_insights = []
        
        # Get technical insights (always works if data exists)
        logger.info("Generating technical insights...")
        technical_insights = self.generate_insights(asset)
        if technical_insights:
            all_insights.extend(technical_insights)
            logger.info(f"Generated {len(technical_insights)} technical insights")
        else:
            logger.warning("No technical insights generated - check if data exists")
        
        # Get sentiment insights (uses NewsAPI)
        try:
            logger.info("Generating sentiment insights...")
            sentiment_service = SentimentService()
            sentiment_insights = sentiment_service.get_sentiment_insights()
            if sentiment_insights:
                all_insights.extend(sentiment_insights)
                logger.info(f"Generated {len(sentiment_insights)} sentiment insights")
        except Exception as e:
            logger.error(f"Error getting sentiment insights: {e}")
        
        # Get macro insights (uses FRED)
        try:
            logger.info("Generating macro insights...")
            macro_service = MacroService()
            macro_insights = macro_service.get_macro_insights()
            if macro_insights:
                all_insights.extend(macro_insights)
                logger.info(f"Generated {len(macro_insights)} macro insights")
        except Exception as e:
            logger.error(f"Error getting macro insights: {e}")
        
        # Combine and deduplicate
        if all_insights:
            combined = self._combine_insights(all_insights)
            logger.info(f"Total combined insights: {len(combined)}")
            return combined
        else:
            logger.warning("No insights generated - check data availability")
            return []
    
    def generate_insights(self, asset: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Generate technical insights for all assets or a specific asset.
        No API calls, safe to run frequently.
        """
        if asset:
            assets = [asset]
        else:
            from backend.config.settings import settings
            assets = settings.ASSETS
        
        all_insights = []
        
        for asset_symbol in assets:
            try:
                # Get latest data
                df = self._get_asset_data(asset_symbol)
                if df.empty:
                    logger.warning(f"No data found for {asset_symbol}")
                    continue
                
                # Generate insights
                insights = self._analyze_asset(df, asset_symbol)
                all_insights.extend(insights)
                logger.info(f"Generated {len(insights)} insights for {asset_symbol}")
                
            except Exception as e:
                logger.error(f"Error generating insights for {asset_symbol}: {e}")
        
        return all_insights
    
    def _get_asset_data(self, asset: str, timeframe: str = 'daily', 
                        days: int = 90) -> pd.DataFrame:
        """Get asset data from database."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        df = db_service.get_candles(asset, timeframe, start_date, end_date)
        
        if df.empty:
            logger.warning(f"No data found for {asset}")
            return df
        
        logger.info(f"Retrieved {len(df)} candles for {asset}")
        return df
    
    def _analyze_asset(self, df: pd.DataFrame, asset: str) -> List[Dict[str, Any]]:
        """Analyze an asset and generate technical insights."""
        insights = []
        
        # Check if we have enough data
        if len(df) < 50:
            logger.warning(f"Not enough data for {asset} (only {len(df)} candles)")
            return insights
        
        # 1. Trend Detection
        trend_insight = self._detect_trend(df, asset)
        if trend_insight:
            insights.append(trend_insight)
        
        # 2. RSI Analysis
        rsi_insight = self._analyze_rsi(df, asset)
        if rsi_insight:
            insights.append(rsi_insight)
        
        # 3. MACD Analysis
        macd_insight = self._analyze_macd(df, asset)
        if macd_insight:
            insights.append(macd_insight)
        
        # 4. Support/Resistance Detection
        sr_insight = self._detect_support_resistance(df, asset)
        if sr_insight:
            insights.append(sr_insight)
        
        # 5. Volatility Analysis
        volatility_insight = self._analyze_volatility(df, asset)
        if volatility_insight:
            insights.append(volatility_insight)
        
        # 6. Pattern Detection
        pattern_insight = self._detect_patterns(df, asset)
        if pattern_insight:
            insights.append(pattern_insight)
        
        return insights
    
    def _detect_trend(self, df: pd.DataFrame, asset: str) -> Optional[Dict[str, Any]]:
        """Detect trend direction and strength."""
        try:
            close = df['close'].values
            last_price = close[-1]
            
            # Calculate EMAs
            ema_20 = calculate_sma(df, 20).values
            ema_50 = calculate_sma(df, 50).values
            
            if len(ema_20) < 50 or len(ema_50) < 50:
                return None
            
            # Check for NaN values
            if pd.isna(ema_20[-1]) or pd.isna(ema_50[-1]):
                return None
            
            # Determine trend
            if last_price > ema_20[-1] > ema_50[-1]:
                trend = 'BULLISH'
                strength = 'STRONG'
                description = f"{asset} is in a strong bullish trend, trading above both 20 and 50-day EMAs"
            elif last_price > ema_20[-1] and last_price < ema_50[-1]:
                trend = 'BULLISH'
                strength = 'MODERATE'
                description = f"{asset} showing moderate bullish momentum, above 20-day EMA but below 50-day EMA"
            elif last_price < ema_20[-1] < ema_50[-1]:
                trend = 'BEARISH'
                strength = 'STRONG'
                description = f"{asset} is in a strong bearish trend, trading below both 20 and 50-day EMAs"
            elif last_price < ema_20[-1] and last_price > ema_50[-1]:
                trend = 'BEARISH'
                strength = 'MODERATE'
                description = f"{asset} showing moderate bearish momentum, below 20-day EMA but above 50-day EMA"
            else:
                trend = 'NEUTRAL'
                strength = 'WEAK'
                description = f"{asset} is in a neutral trend with no clear direction"
            
            return {
                'asset_symbol': asset,
                'insight_type': 'TREND',
                'title': f"{trend} Trend Detected",
                'description': description,
                'confidence': 0.7 if strength == 'STRONG' else 0.5,
                'supporting_data': {
                    'trend': trend,
                    'strength': strength,
                    'ema_20': float(ema_20[-1]),
                    'ema_50': float(ema_50[-1]),
                    'current_price': float(last_price)
                }
            }
        except Exception as e:
            logger.error(f"Error detecting trend for {asset}: {e}")
            return None
    
    def _analyze_rsi(self, df: pd.DataFrame, asset: str) -> Optional[Dict[str, Any]]:
        """Analyze RSI for overbought/oversold conditions."""
        try:
            rsi = calculate_rsi(df, 14)
            
            if rsi is None or len(rsi) < 2:
                return None
            
            current_rsi = rsi.iloc[-1]
            previous_rsi = rsi.iloc[-2]
            
            # Check for NaN
            if pd.isna(current_rsi):
                return None
            
            if current_rsi > 70:
                signal = 'OVERBOUGHT'
                description = f"{asset} is overbought with RSI at {current_rsi:.1f}, suggesting potential reversal"
                confidence = 0.6
            elif current_rsi < 30:
                signal = 'OVERSOLD'
                description = f"{asset} is oversold with RSI at {current_rsi:.1f}, suggesting potential bounce"
                confidence = 0.6
            elif current_rsi > 50 and previous_rsi < 50:
                signal = 'BULLISH_CROSS'
                description = f"{asset} RSI crossed above 50, indicating bullish momentum"
                confidence = 0.5
            elif current_rsi < 50 and previous_rsi > 50:
                signal = 'BEARISH_CROSS'
                description = f"{asset} RSI crossed below 50, indicating bearish momentum"
                confidence = 0.5
            else:
                return None
            
            return {
                'asset_symbol': asset,
                'insight_type': 'REVERSAL',
                'title': f"RSI {signal.replace('_', ' ')}",
                'description': description,
                'confidence': confidence,
                'supporting_data': {
                    'rsi': float(current_rsi),
                    'signal': signal
                }
            }
        except Exception as e:
            logger.error(f"Error analyzing RSI for {asset}: {e}")
            return None
    
    def _analyze_macd(self, df: pd.DataFrame, asset: str) -> Optional[Dict[str, Any]]:
        """Analyze MACD for momentum shifts."""
        try:
            macd_data = calculate_macd(df)
            
            if macd_data is None:
                return None
            
            macd_line = macd_data['macd'].iloc[-1]
            signal_line = macd_data['signal'].iloc[-1]
            histogram = macd_line - signal_line
            
            # Check for NaN
            if pd.isna(macd_line) or pd.isna(signal_line):
                return None
            
            # Detect crossovers
            if len(macd_data['macd']) > 2:
                prev_hist = macd_data['macd'].iloc[-2] - macd_data['signal'].iloc[-2]
                
                if histogram > 0 and prev_hist <= 0:
                    return {
                        'asset_symbol': asset,
                        'insight_type': 'BREAKOUT',
                        'title': "Bullish MACD Crossover",
                        'description': f"{asset} MACD line crossed above signal line, indicating bullish momentum",
                        'confidence': 0.65,
                        'supporting_data': {
                            'macd': float(macd_line),
                            'signal': float(signal_line),
                            'histogram': float(histogram)
                        }
                    }
                elif histogram < 0 and prev_hist >= 0:
                    return {
                        'asset_symbol': asset,
                        'insight_type': 'BREAKOUT',
                        'title': "Bearish MACD Crossover",
                        'description': f"{asset} MACD line crossed below signal line, indicating bearish momentum",
                        'confidence': 0.65,
                        'supporting_data': {
                            'macd': float(macd_line),
                            'signal': float(signal_line),
                            'histogram': float(histogram)
                        }
                    }
            
            return None
        except Exception as e:
            logger.error(f"Error analyzing MACD for {asset}: {e}")
            return None
    
    def _detect_support_resistance(self, df: pd.DataFrame, asset: str) -> Optional[Dict[str, Any]]:
        """Detect support and resistance levels."""
        try:
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            
            # Find recent highs and lows
            lookback = 20
            if len(high) < lookback:
                return None
            
            recent_high = np.max(high[-lookback:])
            recent_low = np.min(low[-lookback:])
            current = close[-1]
            
            # Check if near support or resistance
            distance_to_resistance = (recent_high - current) / recent_high * 100
            distance_to_support = (current - recent_low) / current * 100
            
            if distance_to_resistance < 1 and distance_to_resistance > 0:
                return {
                    'asset_symbol': asset,
                    'insight_type': 'SUPPORT_RESISTANCE',
                    'title': "Near Resistance Level",
                    'description': f"{asset} is trading within 1% of recent resistance at {recent_high:.4f}",
                    'confidence': 0.55,
                    'supporting_data': {
                        'resistance': float(recent_high),
                        'support': float(recent_low),
                        'current': float(current)
                    }
                }
            elif distance_to_support < 1 and distance_to_support > 0:
                return {
                    'asset_symbol': asset,
                    'insight_type': 'SUPPORT_RESISTANCE',
                    'title': "Near Support Level",
                    'description': f"{asset} is trading within 1% of recent support at {recent_low:.4f}",
                    'confidence': 0.55,
                    'supporting_data': {
                        'resistance': float(recent_high),
                        'support': float(recent_low),
                        'current': float(current)
                    }
                }
            
            return None
        except Exception as e:
            logger.error(f"Error detecting support/resistance for {asset}: {e}")
            return None
    
    def _analyze_volatility(self, df: pd.DataFrame, asset: str) -> Optional[Dict[str, Any]]:
        """Analyze volatility conditions."""
        try:
            close = df['close'].values
            returns = np.diff(close) / close[:-1]
            
            if len(returns) < 20:
                return None
            
            # Calculate volatility
            volatility = np.std(returns[-20:]) * np.sqrt(252) * 100  # Annualized
            avg_volatility = np.std(returns) * np.sqrt(252) * 100
            
            if volatility > avg_volatility * 1.5:
                return {
                    'asset_symbol': asset,
                    'insight_type': 'VOLATILITY',
                    'title': "High Volatility Detected",
                    'description': f"{asset} is experiencing elevated volatility at {volatility:.1f}% annualized",
                    'confidence': 0.6,
                    'supporting_data': {
                        'volatility': float(volatility),
                        'average_volatility': float(avg_volatility)
                    }
                }
            elif volatility < avg_volatility * 0.7:
                return {
                    'asset_symbol': asset,
                    'insight_type': 'VOLATILITY',
                    'title': "Low Volatility Detected",
                    'description': f"{asset} volatility is compressed at {volatility:.1f}%, potential breakout ahead",
                    'confidence': 0.5,
                    'supporting_data': {
                        'volatility': float(volatility),
                        'average_volatility': float(avg_volatility)
                    }
                }
            
            return None
        except Exception as e:
            logger.error(f"Error analyzing volatility for {asset}: {e}")
            return None
    
    def _detect_patterns(self, df: pd.DataFrame, asset: str) -> Optional[Dict[str, Any]]:
        """Detect common chart patterns."""
        try:
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            
            if len(high) < 6:
                return None
            
            # Check for higher highs
            if high[-1] > high[-2] > high[-3] and close[-1] > close[-2] > close[-3]:
                return {
                    'asset_symbol': asset,
                    'insight_type': 'PATTERN',
                    'title': "Ascending Pattern Detected",
                    'description': f"{asset} showing higher highs and higher closes, indicating upward momentum",
                    'confidence': 0.5,
                    'supporting_data': {
                        'pattern': 'ASCENDING',
                        'current_price': float(close[-1])
                    }
                }
            
            # Check for lower lows
            if low[-1] < low[-2] < low[-3] and close[-1] < close[-2] < close[-3]:
                return {
                    'asset_symbol': asset,
                    'insight_type': 'PATTERN',
                    'title': "Descending Pattern Detected",
                    'description': f"{asset} showing lower lows and lower closes, indicating downward momentum",
                    'confidence': 0.5,
                    'supporting_data': {
                        'pattern': 'DESCENDING',
                        'current_price': float(close[-1])
                    }
                }
            
            return None
        except Exception as e:
            logger.error(f"Error detecting patterns for {asset}: {e}")
            return None
    
    def _combine_insights(self, insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Combine and deduplicate insights.
        """
        # Group by asset and type
        seen = set()
        unique_insights = []
        
        for insight in insights:
            key = f"{insight.get('asset_symbol')}_{insight.get('insight_type')}"
            if key not in seen:
                seen.add(key)
                unique_insights.append(insight)
        
        # Sort by confidence
        unique_insights.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        return unique_insights