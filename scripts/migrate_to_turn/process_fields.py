import json
from calendar import monthrange
from datetime import date, datetime, timedelta

import pytz

VACCINE_SCHEDULE = (
    (6, "W", "6 week"),
    (10, "W", "10 week"),
    (14, "W", "14 week"),
    (6, "M", "6 month"),
    (9, "M", "9 month"),
    (12, "M", "12 month"),
)


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


def process_opted_in(value, import_as_opted_out=False):
    if import_as_opted_out:
        return "false"

    if not value:
        return "true"

    value = str(value).upper()
    if value == "TRUE":
        return "false"
    return "true"


def process_truthy(value):
    if value is None:
        return "false"
    value = str(value).strip()
    if value.upper() in ("", "FALSE", "NO", "0"):
        return "false"

    return "true"


def get_user_dob_year(value):
    if value is None:
        return ""

    try:
        age = int(str(value).strip())
    except (TypeError, ValueError):
        return ""

    if age < 0:
        return ""

    return datetime.now(pytz.utc).year - age


def has_active_baby(contact):
    return _has_baby_in_age_range(contact, 0, 365)


def has_active_baby_between_1_and_2(contact):
    return _has_baby_in_age_range(contact, 366, 730)


def _has_baby_in_age_range(contact, min_age_days, max_age_days):
    now = datetime.now(pytz.utc)
    for baby in _get_valid_babies(contact):
        birth_date = baby["birth_date"]
        age_days = (now - birth_date).days
        if min_age_days <= age_days <= max_age_days:
            return True
    return False


def _add_months(value, months):
    year = value.year + (value.month - 1 + months) // 12
    month = (value.month - 1 + months) % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _normalize_birth_date(dob):
    value = dob.replace("Z", "").split("+")[0]
    if not is_datetime(value):
        return

    birth_date = datetime.fromisoformat(value)
    if birth_date.tzinfo is None:
        birth_date = birth_date.replace(tzinfo=pytz.utc)
    else:
        birth_date = birth_date.astimezone(pytz.utc)
    return birth_date


def _get_next_vaccine(birth_date, now=None):
    now = now or datetime.now(pytz.utc)
    now_date = now.date()

    for value, unit, text in VACCINE_SCHEDULE:
        if unit == "W":
            due_date = birth_date + timedelta(weeks=value)
        else:
            due_date = _add_months(birth_date, value)

        if due_date.date() >= now_date:
            return {
                "day": due_date.day,
                "month": due_date.month,
                "year": due_date.year,
                "text": text,
                "date": due_date,
            }

    return {"day": 0, "month": 0, "year": 0, "text": "", "date": None}


def _get_valid_babies(contact):
    babies = []
    fields = getattr(contact, "fields", {}) or {}
    for index in range(1, 4):
        dob = fields.get(f"baby_dob{index}")
        if not dob:
            continue

        birth_date = _normalize_birth_date(dob)
        if not birth_date:
            continue

        babies.append(
            {
                "field_index": index,
                "dob": dob,
                "birth_date": birth_date,
                "name": "",
            }
        )

    return babies


def get_next_pnc_appointment_fields(contact):
    postbirth_messaging = (getattr(contact, "fields", {}) or {}).get(
        "postbirth_messaging"
    )
    if process_truthy(postbirth_messaging) != "true":
        return {
            "next_pnc_appointment_date": "",
            "next_pnc_appointment_child_index": "",
            "next_pnc_appointment_text": "",
            "next_pnc_appointment_child_name": "",
        }

    now = datetime.now(pytz.utc)
    candidates = []

    for babies_index, baby in enumerate(_get_valid_babies(contact)):
        age_days = (now - baby["birth_date"]).days
        if not (0 <= age_days <= 365):
            continue

        next_vaccine = _get_next_vaccine(baby["birth_date"], now)
        if not next_vaccine["date"]:
            continue

        candidates.append(
            {
                "date": next_vaccine["date"],
                "child_index": babies_index,
                "text": next_vaccine["text"],
                "child_name": baby["name"],
            }
        )

    if not candidates:
        return {
            "next_pnc_appointment_date": "",
            "next_pnc_appointment_child_index": 0,
            "next_pnc_appointment_text": "",
            "next_pnc_appointment_child_name": "",
        }

    next_appointment = min(candidates, key=lambda appointment: appointment["date"])
    return {
        "next_pnc_appointment_date": next_appointment["date"].isoformat(),
        "next_pnc_appointment_child_index": next_appointment["child_index"],
        "next_pnc_appointment_text": next_appointment["text"],
        "next_pnc_appointment_child_name": next_appointment["child_name"],
    }


def get_user_type(contact):
    # Ineligible: We don't save anything on rapidpro to identify ineligible users
    # Push Basic User: Clinic code is required in rapdidpro so these don't exist

    def get_truthy_field(field_name):
        return process_truthy(contact.fields.get(field_name)) == "true"

    opted_out = get_truthy_field("opted_out")
    prebirth_messaging = get_truthy_field("prebirth_messaging")
    postbirth_messaging = get_truthy_field("postbirth_messaging")
    public_messaging = get_truthy_field("public_messaging")

    supporter = get_truthy_field("supporter")
    supp_status = (contact.fields.get("supp_status") or "").strip().lower()

    user_type = "lead"

    if opted_out:
        user_type = "deregistered_user"
    elif supporter:
        # We need to update these to send them a message about not getting messages
        # anymore
        user_type = "supporter" if supp_status == "registered" else "supporter_lead"
    elif prebirth_messaging or postbirth_messaging:
        user_type = "comprehensive_user"

        if (
            not prebirth_messaging
            and postbirth_messaging
            and not has_active_baby(contact)
        ):
            user_type = "alumni_user"

            if has_active_baby_between_1_and_2(contact):
                # For these we'll start a journey letting them know they won't be
                # gettting messages anymore and then updating them to alumnni_user
                user_type = "alumni_user_1_year"
    elif public_messaging:
        user_type = "public_user"

    return user_type


def get_user_babies(contact):
    babies = []
    now = datetime.now(pytz.utc)
    for baby in _get_valid_babies(contact):
        birth_date = baby["birth_date"]
        age_days = (now - birth_date).days
        next_vaccine = {"day": 0, "month": 0, "year": 0, "text": ""}
        if 0 <= age_days <= 365:
            next_vaccine = _get_next_vaccine(birth_date, now)

        babies.append(
            {
                "all_vaccines_received": "",
                "appointments_attended": 0,
                "baby_birth_day": birth_date.day,
                "baby_birth_month": birth_date.month,
                "baby_birth_year": birth_date.year,
                "name": baby["name"],
                "next_vacc_day": next_vaccine["day"],
                "next_vacc_month": next_vaccine["month"],
                "next_vacc_text": next_vaccine["text"],
                "next_vacc_year": next_vaccine["year"],
                "pregnancy_edd": 0,
                "vaccination_status_at_reg": "",
            }
        )

    if babies:
        return json.dumps(babies)


def get_youngest_dob(contact):
    babies = _get_valid_babies(contact)
    if not babies:
        return

    youngest_birth_date = max(babies, key=lambda baby: baby["birth_date"])["birth_date"]
    return youngest_birth_date.astimezone(pytz.utc).isoformat()


def process_baby_loss_status(contact):
    loss_messaging = contact.fields.get("loss_messaging")
    optout_reason = contact.fields.get("optout_reason")
    if loss_messaging == "TRUE" and optout_reason == "baby_loss":
        return "true"


def process_pregnancy_loss_status(contact):
    loss_messaging = contact.fields.get("loss_messaging")
    optout_reason = contact.fields.get("optout_reason")
    if loss_messaging == "TRUE" and optout_reason in ("miscarriage", "stillbirth"):
        return "true"


def get_pregnancy_in_weeks(contact):
    edd = (getattr(contact, "fields", {}) or {}).get("edd")
    if not edd:
        return ""

    try:
        edd_date = datetime.fromisoformat(edd.replace("Z", "").split("+")[0])
    except (AttributeError, TypeError, ValueError):
        return ""

    now = datetime.now(pytz.utc)
    exp_year = now.year + int(now.month > edd_date.month)
    try:
        exp_date = date(exp_year, edd_date.month, edd_date.day)
    except ValueError:
        return ""

    conception_date = exp_date - timedelta(weeks=40)
    days_since_conception = (
        (now.year - conception_date.year) * 365.25
        + (now.month - conception_date.month) * 30.4
        + (now.day - conception_date.day)
    )
    return str(int(days_since_conception / 7))
