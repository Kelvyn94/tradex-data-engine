from dataclasses import dataclass


@dataclass
class DownloadReport:

    asset: str

    timeframe: str

    rows: int

    success: bool

    elapsed: float