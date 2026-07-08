from pathlib import Path
from backend.utils.logger import log


class DataDownloader:
    def __init__(self):
        self.raw_folder = Path("data/raw")

    def initialize(self):
        self.raw_folder.mkdir(parents=True, exist_ok=True)
        log("Raw data folder verified.")

    def show_location(self):
        log(f"Raw data path: {self.raw_folder.resolve()}")