"""
Core Backtesting Engine - Institutional Grade
Runs backtests on historical data with proper simulation.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, field
from enum import Enum

from backend.services.database_service import db_service
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Trade:
    """Represents a completed trade."""
    entry_time: datetime
    exit_time: datetime
    asset: str
    side: str
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    pnl_percent: float
    holding_period: float


class BacktestEngine:
    """
    Professional backtesting engine with:
    - Realistic slippage modeling
    - Commission handling
    - Position sizing
    - Risk management
    """
    
    def __init__(self, initial_capital: float = 100000,
                 commission: float = 0.001,  # 0.1% per trade
                 slippage: float = 0.001):   # 0.1% slippage
        """
        Initialize backtest engine.
        
        Args:
            initial_capital: Starting capital
            commission: Commission rate (0.1% default)
            slippage: Slippage rate (0.1% default)
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.cash = initial_capital
        self.positions = {}  # asset -> {'size': float, 'entry_price': float, 'entry_time': datetime}
        self.trades = []
        self.equity_curve = []
        self.current_value = initial_capital
        self.logger = logger
        
        logger.info(f"BacktestEngine initialized (capital=${initial_capital:,.2f})")
    
    def run(self, strategy: Callable, 
            data: Dict[str, pd.DataFrame],
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None) -> Dict:
        """
        Run a backtest with a given strategy.
        
        Args:
            strategy: Strategy function that returns signals DataFrame
            data: Dictionary of asset data (key: asset, value: DataFrame with timestamp index)
            start_date: Start date
            end_date: End date
            
        Returns:
            Backtest results
        """
        # Reset state
        self.cash = self.initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        
        # Get date range
        all_dates = []
        for df in data.values():
            if df is not None and not df.empty:
                all_dates.extend(df.index.tolist())
        
        if not all_dates:
            return {'error': 'No data'}
        
        all_dates = sorted(set(all_dates))
        
        if start_date is None:
            start_date = all_dates[0]
        if end_date is None:
            end_date = all_dates[-1]
        
        # Filter data to date range
        filtered_data = {}
        assets = list(data.keys())
        
        for asset, df in data.items():
            mask = (df.index >= start_date) & (df.index <= end_date)
            filtered_data[asset] = df.loc[mask].copy()
        
        # Build unified DataFrame with all assets
        try:
            unified_df = self._build_unified_dataframe(filtered_data)
        except Exception as e:
            logger.error(f"Error building unified dataframe: {e}")
            return {'error': f'Data error: {e}'}
        
        if unified_df.empty:
            return {'error': 'No data after filtering'}
        
        # Generate signals
        try:
            signals_df = strategy(unified_df)
        except Exception as e:
            logger.error(f"Error generating signals: {e}")
            return {'error': f'Strategy error: {e}'}
        
        if signals_df.empty:
            return {'error': 'No signals generated'}
        
        # Process each timestamp
        self.equity_curve.append({
            'timestamp': unified_df.index[0],
            'value': self.initial_capital
        })
        
        for idx in range(1, len(unified_df)):
            timestamp = unified_df.index[idx]
            
            # Process signals for this timestamp
            if timestamp in signals_df.index:
                signal_row = signals_df.loc[timestamp]
                
                for asset in assets:
                    signal_col = f'{asset}_signal'
                    if signal_col in signal_row.index:
                        signal = signal_row[signal_col]
                        
                        # Only execute if signal changed (avoid repeated entries)
                        prev_signal = 0
                        if idx > 1:
                            prev_timestamp = unified_df.index[idx-1]
                            if prev_timestamp in signals_df.index:
                                prev_row = signals_df.loc[prev_timestamp]
                                if signal_col in prev_row.index:
                                    prev_signal = prev_row[signal_col]
                        
                        # Execute on signal change
                        if signal != 0 and signal != prev_signal:
                            price_col = f'{asset}_close'
                            if price_col in unified_df.columns:
                                current_price = unified_df.loc[timestamp, price_col]
                                
                                # Execute order
                                self._execute_order(
                                    asset=asset,
                                    side='BUY' if signal > 0 else 'SELL',
                                    price=current_price,
                                    size=abs(signal) * 100,  # Position size in units
                                    timestamp=timestamp
                                )
            
            # Update equity curve
            self.current_value = self._calculate_total_value(unified_df.loc[timestamp])
            self.equity_curve.append({
                'timestamp': timestamp,
                'value': self.current_value
            })
        
        # Close all open positions at the end
        if self.positions:
            last_timestamp = unified_df.index[-1]
            for asset, pos in list(self.positions.items()):
                price_col = f'{asset}_close'
                if price_col in unified_df.columns:
                    current_price = unified_df.loc[last_timestamp, price_col]
                    self._close_position(asset, current_price, last_timestamp)
        
        # Calculate results
        results = self._calculate_results()
        
        logger.info(f"Backtest complete: {len(self.trades)} trades")
        
        return results
    
    def _build_unified_dataframe(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Build a unified DataFrame with all assets."""
        unified = pd.DataFrame()
        
        for asset, df in data.items():
            if df is not None and not df.empty:
                if 'close' in df.columns:
                    unified[f'{asset}_close'] = df['close']
                else:
                    logger.warning(f"No 'close' column for {asset}")
        
        unified = unified.ffill().bfill()
        unified = unified.dropna()
        
        return unified
    
    def _execute_order(self, asset: str, side: str, price: float, 
                       size: float, timestamp: datetime):
        """Execute an order."""
        if side == 'BUY':
            # Check if we have enough cash
            cost = size * price * (1 + self.commission + self.slippage)
            if cost > self.cash:
                size = self.cash / (price * (1 + self.commission + self.slippage))
                cost = size * price * (1 + self.commission + self.slippage)
            
            if size > 0:
                self.cash -= cost
                
                if asset in self.positions:
                    existing = self.positions[asset]
                    total_size = existing['size'] + size
                    avg_price = (existing['size'] * existing['entry_price'] + size * price) / total_size
                    self.positions[asset] = {
                        'size': total_size,
                        'entry_price': avg_price,
                        'entry_time': existing['entry_time']
                    }
                else:
                    self.positions[asset] = {
                        'size': size,
                        'entry_price': price,
                        'entry_time': timestamp
                    }
                
                logger.debug(f"BUY {asset}: {size:.4f} @ {price:.4f}")
        
        elif side == 'SELL':
            if asset in self.positions:
                position = self.positions[asset]
                sell_size = min(size, position['size'])
                if sell_size > 0:
                    proceeds = sell_size * price * (1 - self.commission - self.slippage)
                    self.cash += proceeds
                    
                    # Calculate PnL
                    pnl = proceeds - (sell_size * position['entry_price'])
                    
                    self.trades.append({
                        'asset': asset,
                        'side': 'SELL',
                        'entry_price': position['entry_price'],
                        'exit_price': price,
                        'size': sell_size,
                        'entry_time': position['entry_time'],
                        'exit_time': timestamp,
                        'pnl': pnl,
                        'pnl_percent': (price - position['entry_price']) / position['entry_price'] * 100
                    })
                    
                    remaining = position['size'] - sell_size
                    if remaining > 0:
                        self.positions[asset]['size'] = remaining
                    else:
                        del self.positions[asset]
                    
                    logger.debug(f"SELL {asset}: {sell_size:.4f} @ {price:.4f} PnL: ${pnl:.2f}")
    
    def _close_position(self, asset: str, price: float, timestamp: datetime):
        """Close a position."""
        if asset in self.positions:
            position = self.positions[asset]
            proceeds = position['size'] * price * (1 - self.commission - self.slippage)
            self.cash += proceeds
            
            pnl = proceeds - (position['size'] * position['entry_price'])
            
            self.trades.append({
                'asset': asset,
                'side': 'CLOSE',
                'entry_price': position['entry_price'],
                'exit_price': price,
                'size': position['size'],
                'entry_time': position['entry_time'],
                'exit_time': timestamp,
                'pnl': pnl,
                'pnl_percent': (price - position['entry_price']) / position['entry_price'] * 100
            })
            
            del self.positions[asset]
            
            logger.debug(f"CLOSE {asset}: {position['size']:.4f} @ {price:.4f} PnL: ${pnl:.2f}")
    
    def _calculate_total_value(self, current_prices: pd.Series) -> float:
        """Calculate total portfolio value."""
        total = self.cash
        
        for asset, position in self.positions.items():
            price_col = f'{asset}_close'
            if price_col in current_prices.index:
                total += position['size'] * current_prices[price_col]
        
        return total
    
    def _calculate_results(self) -> Dict:
        """Calculate backtest results."""
        if not self.equity_curve:
            return {'error': 'No equity data'}
        
        equity_df = pd.DataFrame(self.equity_curve)
        equity_df = equity_df.set_index('timestamp')
        equity_df['returns'] = equity_df['value'].pct_change()
        
        # Basic metrics
        total_return = (equity_df['value'].iloc[-1] - equity_df['value'].iloc[0]) / equity_df['value'].iloc[0]
        days = (equity_df.index[-1] - equity_df.index[0]).days
        years = days / 365.25 if days > 0 else 1
        annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        volatility = equity_df['returns'].std() * np.sqrt(252)
        
        risk_free_rate = 0.02
        excess_returns = equity_df['returns'] - risk_free_rate / 252
        sharpe_ratio = (excess_returns.mean() / excess_returns.std()) * np.sqrt(252) if excess_returns.std() > 0 else 0
        
        downside_returns = equity_df['returns'][equity_df['returns'] < 0]
        sortino_ratio = (excess_returns.mean() * 252) / (downside_returns.std() * np.sqrt(252)) if len(downside_returns) > 0 and downside_returns.std() > 0 else 0
        
        peak = equity_df['value'].iloc[0]
        max_drawdown = 0
        for value in equity_df['value']:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        trade_pnls = [t.get('pnl', 0) for t in self.trades]
        wins = [p for p in trade_pnls if p > 0]
        losses = [p for p in trade_pnls if p < 0]
        
        win_rate = len(wins) / len(trade_pnls) if trade_pnls else 0
        total_wins = sum(wins) if wins else 0
        total_losses = abs(sum(losses)) if losses else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf') if total_wins > 0 else 0
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'total_trades': len(self.trades),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_pnl': sum(trade_pnls) if trade_pnls else 0,
            'trades': self.trades
        }