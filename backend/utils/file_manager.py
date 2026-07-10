from pathlib import Path

from backend.config.paths import RAW


class FileManager:

    @staticmethod
    def create_asset_folder(asset):

        folder = RAW / asset

        folder.mkdir(parents=True, exist_ok=True)

        return folder

    @staticmethod
    def csv_path(asset, timeframe):

        folder = FileManager.create_asset_folder(asset)

        return folder / f"{timeframe}.csv"