from datetime import datetime
from dateutil.relativedelta import relativedelta


class DateUtils:

    @staticmethod
    def years_ago(years: int):

        return (
            datetime.now()
            - relativedelta(years=years)
        ).strftime("%Y-%m-%d")