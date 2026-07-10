from dataclasses import dataclass


@dataclass
class Asset:
    name: str
    yahoo_symbol: str
    tradermade_symbol: str
    asset_type: str