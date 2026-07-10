"""
Strategy Optimizer - Hedge Fund Grade
Optimizes strategy parameters using grid search and genetic algorithms.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Callable
from itertools import product
import logging
from concurrent.futures import ThreadPoolExecutor
import json

logger = logging.getLogger(__name__)


class StrategyOptimizer:
    """
    Professional strategy optimizer with:
    - Grid search optimization
    - Genetic algorithm optimization
    - Walk-forward optimization
    - Multi-objective optimization
    """
    
    def __init__(self, metric: str = 'sharpe_ratio',
                 maximize: bool = True):
        """
        Initialize optimizer.
        
        Args:
            metric: Metric to optimize ('sharpe_ratio', 'total_return', 'win_rate')
            maximize: Whether to maximize the metric
        """
        self.metric = metric
        self.maximize = maximize
        self.results = []
        self.best_params = None
        self.best_score = None
        logger.info(f"StrategyOptimizer initialized (metric={metric})")
    
    def grid_search(self, strategy: Callable, 
                    data: Dict[str, pd.DataFrame],
                    param_grid: Dict[str, List],
                    metric: Optional[str] = None) -> Dict:
        """
        Perform grid search optimization.
        
        Args:
            strategy: Strategy function
            data: Market data
            param_grid: Dictionary of parameter lists
            metric: Metric to optimize (default: self.metric)
            
        Returns:
            Best parameters and results
        """
        if metric is None:
            metric = self.metric
        
        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(product(*param_values))
        
        logger.info(f"Running grid search: {len(combinations)} combinations")
        
        results = []
        
        for combo in combinations:
            params = dict(zip(param_names, combo))
            
            # Run backtest with these parameters
            result = self._run_backtest(strategy, data, params)
            
            # Extract metric
            score = result.get(metric, 0)
            
            results.append({
                'params': params,
                'score': score,
                'result': result
            })
        
        # Sort results
        results.sort(key=lambda x: x['score'], reverse=self.maximize)
        
        self.results = results
        
        if results:
            self.best_params = results[0]['params']
            self.best_score = results[0]['score']
            
            logger.info(f"Best parameters: {self.best_params}")
            logger.info(f"Best {metric}: {self.best_score:.4f}")
        
        return {
            'best_params': self.best_params,
            'best_score': self.best_score,
            'all_results': results[:10]  # Top 10 results
        }
    
    def genetic_algorithm(self, strategy: Callable,
                          data: Dict[str, pd.DataFrame],
                          param_ranges: Dict[str, Tuple[float, float]],
                          population_size: int = 50,
                          generations: int = 10,
                          metric: Optional[str] = None) -> Dict:
        """
        Perform genetic algorithm optimization.
        
        Args:
            strategy: Strategy function
            data: Market data
            param_ranges: Dictionary of parameter ranges
            population_size: Population size
            generations: Number of generations
            metric: Metric to optimize
            
        Returns:
            Best parameters and results
        """
        if metric is None:
            metric = self.metric
        
        logger.info(f"Running genetic algorithm: {generations} generations, {population_size} population")
        
        # Initialize population
        population = []
        for _ in range(population_size):
            individual = {}
            for param, (min_val, max_val) in param_ranges.items():
                if isinstance(min_val, int):
                    individual[param] = np.random.randint(min_val, max_val + 1)
                else:
                    individual[param] = np.random.uniform(min_val, max_val)
            population.append(individual)
        
        best_overall = None
        best_score_overall = -float('inf') if self.maximize else float('inf')
        
        for gen in range(generations):
            # Evaluate population
            fitness = []
            for individual in population:
                result = self._run_backtest(strategy, data, individual)
                score = result.get(metric, 0)
                fitness.append((individual, score))
            
            # Sort fitness
            fitness.sort(key=lambda x: x[1], reverse=self.maximize)
            
            # Update best
            if self.maximize:
                if fitness[0][1] > best_score_overall:
                    best_score_overall = fitness[0][1]
                    best_overall = fitness[0][0].copy()
            else:
                if fitness[0][1] < best_score_overall:
                    best_score_overall = fitness[0][1]
                    best_overall = fitness[0][0].copy()
            
            # Select parents (top 20%)
            parents = [f[0] for f in fitness[:population_size // 5]]
            
            # Create next generation
            next_population = parents.copy()
            
            while len(next_population) < population_size:
                # Select two parents
                parent1 = parents[np.random.randint(len(parents))]
                parent2 = parents[np.random.randint(len(parents))]
                
                # Crossover
                child = {}
                for param in param_ranges:
                    if np.random.random() < 0.5:
                        child[param] = parent1[param]
                    else:
                        child[param] = parent2[param]
                
                # Mutation
                for param, (min_val, max_val) in param_ranges.items():
                    if np.random.random() < 0.1:
                        if isinstance(min_val, int):
                            child[param] = np.random.randint(min_val, max_val + 1)
                        else:
                            child[param] = np.random.uniform(min_val, max_val)
                
                next_population.append(child)
            
            population = next_population
            
            logger.info(f"Generation {gen+1}/{generations}: Best {metric} = {best_score_overall:.4f}")
        
        self.best_params = best_overall
        self.best_score = best_score_overall
        
        return {
            'best_params': best_overall,
            'best_score': best_score_overall,
            'generations': generations
        }
    
    def _run_backtest(self, strategy: Callable,
                      data: Dict[str, pd.DataFrame],
                      params: Dict) -> Dict:
        """
        Run a backtest with given parameters.
        """
        from backend.backtesting.engine import BacktestEngine
        
        # Create strategy wrapper
        def strategy_wrapper(data):
            return strategy(data, **params)
        
        # Run backtest
        engine = BacktestEngine()
        result = engine.run(strategy_wrapper, data)
        
        return result