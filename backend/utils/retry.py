import time


def retry(function, retries=3):

    for attempt in range(retries):

        try:

            return function()

        except Exception:

            if attempt == retries - 1:

                raise

            time.sleep(2)