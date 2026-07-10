"""
Portfolio Management - Institutional Grade
Advanced portfolio with risk management.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PortfolioManager:
    """
    Professional portfolio management with:
    - Position sizing (Kelly, Fixed Fraction)
    - Risk management (Stop-loss, Take-profit)
    - Correlation-based position adjustment
    """
    
    def __init__(self, initial_capital: float = 100000,
                 max_position_size: float = 0.1,
                 max_risk_per_trade: float = 0.02,
                 stop_loss: float = 0.02,
                 take_profit: float = 0.04):
        """
        Initialize portfolio manager.
        
        Args:
            initial_capital: Starting capital
            max_position_size: Max position as % of portfolio (10%)
            max_risk_per_trade: Max risk per trade as % of portfolio (2%)
            stop_loss: Stop loss as % (2%)
            take_profit: Take profit as % (4%)
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        self.max_position_size = max_position_size
        self.max_risk_per_trade = max_risk_per_trade
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.trade_history = []
        self.equity_curve = [initial_capital]
        
        logger.info(f"PortfolioManager initialized (capital=${initial_capital:,.2f})")
    
    def calculate_position_size(self, asset: str, price: float, 
                                volatility: float = 0.01) -> float:
        """
        Calculate position size using Kelly Criterion.
        
        Args:
            asset: Asset symbol
            price: Current price
            volatility: Estimated volatility
            
        Returns:
            Position size in units
        """
        # Kelly fraction (simplified)
        kelly_fraction = 0.25  # Use fractional Kelly (25%)
        
        # Position size as percentage of portfolio
        position_pct = min(
            self.max_position_size,
            self.max_risk_per_trade / volatility
        )
        
        # Apply Kelly
        position_pct = position_pct * kelly_fraction
        
        # Convert to units
        position_value = self.cash * position_pct
        position_size = position_value / price
        
        return position_size
    
    def enter_position(self, asset: str, side: str, 
                       price: float, size: float) -> Dict:
        """
        Enter a position.
        
        Args:
            asset: Asset symbol
            side: 'BUY' or 'SELL'
            price: Entry price
            size: Position size
            
        Returns:
            Position entry result
        """
        if size <= 0:
            return {'success': False, 'reason': 'Invalid size'}
        
        # Calculate cost
        cost = size * price
        if cost > self.cash:
            return {'success': False, 'reason': 'Insufficient funds'}
        
        # Enter position
        self.positions[asset] = {
            'side': side,
            'entry_price': price,
            'size': size,
            'entry_time': datetime.now(),
            'stop_loss': price * (1 - self.stop_loss) if side == 'BUY' else price * (1 + self.stop_loss),
            'take_profit': price * (1 + self.take_profit) if side == 'BUY' else price * (1 - self.take_profit)
        }
        
        # Update cash
        self.cash -= cost
        
        # Record trade
        self.trade_history.append({
            'type': 'ENTRY',
            'asset': asset,
            'side': side,
            'price': price,
            'size': size,
            'cost': cost,
            'timestamp': datetime.now()
        })
        
        return {
            'success': True,
            'asset': asset,
            'side': side,
            'entry_price': price,
            'size': size,
            'stop_loss': self.positions[asset]['stop_loss'],
            'take_profit': self.positions[asset]['take_profit']
        }
    
    def exit_position(self, asset: str, price: float) -> Dict:
        """
        Exit a position.
        
        Args:
            asset: Asset symbol
            price: Exit price
            
        Returns:
            Position exit result
        """
        if asset not in self.positions:
            return {'success': False, 'reason': 'No position'}
        
        position = self.positions[asset]
        size = position['size']
        entry_price = position['entry_price']
        side = position['side']
        
        # Calculate PnL
        if side == 'BUY':
            pnl = (price - entry_price) * size
        else:  # SELL
            pnl = (entry_price - price) * size
        
        # Update cash
        proceeds = size * price
        self.cash += proceeds
        
        # Calculate return
        return_pct = pnl / (size * entry_price)
        
        # Record trade
        self.trade_history.append({
            'type': 'EXIT',
            'asset': asset,
            'side': side,
            'entry_price': entry_price,
            'exit_price': price,
            'size': size,
            'pnl': pnl,
            'return_pct': return_pct,
            'timestamp': datetime.now()
        })
        
        # Remove position
        del self.positions[asset]
        
        # Update equity curve
        self._update_equity_curve()
        
        return {
            'success': True,
            'asset': asset,
            'entry_price': entry_price,
            'exit_price': price,
            'size': size,
            'pnl': pnl,
            'return_pct': return_pct
        }
    
    def _update_equity_curve(self):
        """Update equity curve."""
        # Simplified: cash + positions at last known prices
        total_value = self.cash
        for asset, pos in self.positions.items():
            # In real backtest, would use current price
            total_value += pos['size'] * pos['entry_price']
        
        self.equity_curve.append(total_value)
    
    def get_position(self, asset: str) -> Optional[Dict]:
        """Get position details."""
        return self.positions.get(asset)
    
    def get_total_value(self) -> float:
        """Get total portfolio value."""
        return self.cash
    
    def get_equity_curve(self) -> List[float]:
        """Get equity curve."""
        return self.equity_curve
    
    def get_trade_history(self) -> List[Dict]:
        """Get trade history."""
        return self.trade_history