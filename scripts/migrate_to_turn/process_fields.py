import json
from datetime import date, datetime, timedelta

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
    now = datetime.now(pytz.utc)
    fields = getattr(contact, "fields", {}) or {}
    for index in range(1, 4):
        dob = fields.get(f"baby_dob{index}")
        if not dob:
            continue
        value = dob.replace("Z", "").split("+")[0]
        if not is_datetime(value):
            continue
        birth_date = datetime.fromisoformat(value)
        if birth_date.tzinfo is None:
            birth_date = birth_date.replace(tzinfo=pytz.utc)
        age_days = (now - birth_date).days
        if 0 <= age_days <= 365:
            return True
    return False


def has_active_baby_between_1_and_2(contact):
    now = datetime.now(pytz.utc)
    fields = getattr(contact, "fields", {}) or {}
    for index in range(1, 4):
        dob = fields.get(f"baby_dob{index}")
        if not dob:
            continue
        value = dob.replace("Z", "").split("+")[0]
        if not is_datetime(value):
            continue
        birth_date = datetime.fromisoformat(value)
        if birth_date.tzinfo is None:
            birth_date = birth_date.replace(tzinfo=pytz.utc)
        age_days = (now - birth_date).days
        if 365 < age_days <= 730:
            return True
    return False


def get_valid_baby_dobs(contact):
    valid_baby_dobs = []
    fields = getattr(contact, "fields", {}) or {}
    for index in range(1, 4):
        dob = fields.get(f"baby_dob{index}")
        if not dob:
            continue

        value = dob.replace("Z", "").split("+")[0]
        if not is_datetime(value):
            continue

        valid_baby_dobs.append((dob, datetime.fromisoformat(value)))

    return valid_baby_dobs


def get_user_type(contact):
    # Ineligible: We don't save anything on rapidpro to identify ineligible users
    # Push Basic User: Clinic code is required in rapdidpro so these don't exist

    def get_truthy_field(field_name):
        return process_truthy(contact.fields.get(field_name)) == "true"

    opted_out = get_truthy_field("opted_out")
    prebirth_messaging = get_truthy_field("prebirth_messaging")
    postbirth_messaging = get_truthy_field("postbirth_messaging")

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

    # TODO: add specific public user type

    return user_type


def get_user_babies(contact):
    babies = []
    for _, birth_date in get_valid_baby_dobs(contact):
        babies.append(
            {
                "all_vaccines_received": "",
                "appointments_attended": 0,
                "baby_birth_day": birth_date.day,
                "baby_birth_month": birth_date.month,
                "baby_birth_year": birth_date.year,
                "name": "",
                "next_vacc_day": 0,
                "next_vacc_month": 0,
                "next_vacc_year": 0,
                "pregnancy_edd": 0,
                "vaccination_status_at_reg": "",
            }
        )

    if babies:
        return json.dumps(babies)


def get_youngest_dob(contact):
    baby_dobs = get_valid_baby_dobs(contact)
    if not baby_dobs:
        return

    youngest_dob = max(baby_dobs, key=lambda dob: dob[1])[0]
    return process_datetime(youngest_dob)


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


def get_next_pnc_appointment_child_index(contact):
    postbirth_messaging = (getattr(contact, "fields", {}) or {}).get(
        "postbirth_messaging"
    )
    if process_truthy(postbirth_messaging) == "true":
        return 0
    return ""
