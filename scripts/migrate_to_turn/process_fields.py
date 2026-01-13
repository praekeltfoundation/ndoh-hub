import json
from datetime import datetime

import pytz


def is_datetime(date):
    try:
        datetime.fromisoformat(date)
    except Exception:
        return False
    return True


def to_lowercase(value):
    if isinstance(value, str):
        return value.lower()
    return value


def process_datetime(value):
    if not value:
        return

    value = value.replace("Z", "").split("+")[0]
    if is_datetime(value):
        value = datetime.fromisoformat(value)
        value = value.astimezone(pytz.utc).isoformat()
        return value


def get_user_tier(contact):
    # TODO: figure out user tier based on rapidpro fields
    return None


def get_user_type(contact):
    # TODO: figure out user type based on rapidpro fields
    return None


def get_user_babies(contact):
    babies = []
    fields = getattr(contact, "fields", {}) or {}
    for index in range(1, 4):
        dob = fields.get(f"baby_dob{index}")
        if not dob:
            continue

        value = dob.replace("Z", "").split("+")[0]
        if not is_datetime(value):
            continue

        birth_date = datetime.fromisoformat(value)
        babies.append(
            {
                "all_vaccines_received": "all",
                "appointments_attended": 0,
                "baby_birth_day": birth_date.day,
                "baby_birth_month": birth_date.month,
                "baby_birth_year": birth_date.year,
                "name": "",
                "next_vacc_day": 0,
                "next_vacc_month": 0,
                "next_vacc_year": 0,
                "pregnancy_edd": 0,
                "vaccination_status_at_reg": "all",
            }
        )

    if babies:
        return json.dumps(babies)
