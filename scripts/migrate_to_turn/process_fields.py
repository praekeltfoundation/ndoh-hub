from datetime import datetime

import pytz


def is_datetime(date):
    try:
        datetime.fromisoformat(date)
    except Exception:
        return False
    return True


def process_datetime(value):
    if is_datetime(value):
        value = datetime.fromisoformat(value)
        value = value.astimezone(pytz.utc).isoformat()
        return value
