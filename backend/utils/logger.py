from datetime import datetime

from backend.config.paths import LOGS

LOGS.mkdir(exist_ok=True)

log_file = LOGS / f"{datetime.now():%Y-%m-%d}.log"


def log(message: str):

    timestamp = datetime.now().strftime("%H:%M:%S")

    text = f"[{timestamp}] {message}"

    print(text)

    with open(log_file, "a", encoding="utf8") as f:
        f.write(text + "\n")