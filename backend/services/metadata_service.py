import json

from pathlib import Path

from datetime import datetime


class MetadataService:

    def create(self, csv_path, dataframe):

        metadata = {

            "rows": len(dataframe),

            "columns": list(dataframe.columns),

            "download_time": datetime.now().isoformat(),

            "start": str(dataframe.iloc[0]["date"]),

            "end": str(dataframe.iloc[-1]["date"])

        }

        meta_file = Path(csv_path).with_suffix(".json")

        with open(meta_file, "w") as f:

            json.dump(metadata, f, indent=4)