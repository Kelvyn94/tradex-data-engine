from pathlib import Path

from backend.config.paths import RAW_DATA_PATH


class StorageService:

    def save(self, symbol, interval, dataframe):

        folder = Path(RAW_DATA_PATH) / symbol

        folder.mkdir(parents=True, exist_ok=True)

        file = folder / f"{interval}.csv"

        dataframe.to_csv(file, index=False)

        return file