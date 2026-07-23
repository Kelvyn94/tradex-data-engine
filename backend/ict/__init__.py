"""
ICT (Inner Circle Trader) Analysis Module
Complete ICT implementation for TradeX Data Engine.
"""

from backend.ict.market_structure import MarketStructure
from backend.ict.bos import BOSDetector
from backend.ict.choch import CHOCHDetector
from backend.ict.order_blocks import OrderBlockDetector
from backend.ict.fvg import FVGDetector
from backend.ict.liquidity import LiquidityDetector
from backend.ict.sessions import SessionAnalyzer
from backend.ict.killzone import KillzoneDetector
from backend.ict.premium_discount import PremiumDiscountAnalyzer
from backend.ict.mitigation import MitigationAnalyzer
from backend.ict.dealing_range import DealingRangeAnalyzer
from backend.ict.quarterly_theory import QuarterlyTheoryAnalyzer
from backend.ict.smt import SMTAnalyzer

# ICTService (backend/services/ict_service.py) intentionally is NOT
# re-exported here. It imports FROM these submodules (market_structure,
# bos, choch, ...) to build its combined analysis; re-exporting it from
# this package's __init__ would mean this package imports back from a
# module that imports from this package — a circular import. It was
# never triggered because nothing imported ict_service.py until
# api/routes/ict_routes.py started doing so; import ICTService directly
# from backend.services.ict_service instead.
__all__ = [
    'MarketStructure',
    'BOSDetector',
    'CHOCHDetector',
    'OrderBlockDetector',
    'FVGDetector',
    'LiquidityDetector',
    'SessionAnalyzer',
    'KillzoneDetector',
    'PremiumDiscountAnalyzer',
    'MitigationAnalyzer',
    'DealingRangeAnalyzer',
    'QuarterlyTheoryAnalyzer',
    'SMTAnalyzer',
]