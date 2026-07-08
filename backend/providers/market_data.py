from backend.config.settings import ASSETS
from backend.utils.logger import log
from backend.providers.downloader import DataDownloader


class MarketDataService:

    def __init__(self):
        log("Market Data Service Started")
        log(f"Assets Loaded: {len(ASSETS)}")

        self.downloader = DataDownloader()

    def initialize(self):
        self.downloader.initialize()
        self.downloader.show_location()

    def show_assets(self):
        for asset in ASSETS:
            print(asset)


if __name__ == "__main__":
    service = MarketDataService()
    service.initialize()
    service.show_assets()