import datetime
import pytz


class DateTimeHelper:
    def __init__(self, timezone):
        self.timezone = timezone

    def get_date(self):
        local_timezone = pytz.timezone(self.timezone)
        local_dt = datetime.datetime.now(local_timezone)
        return local_dt.date(), local_dt.hour, local_dt.weekday()
