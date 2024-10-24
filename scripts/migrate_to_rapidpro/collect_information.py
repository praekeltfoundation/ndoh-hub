import contextlib
import json
import logging
import os
import time

import phonenumbers
import psycopg2

from ndoh_hub.constants import LANGUAGES


def get_addresses(addresses):
    addresses = addresses.get("msisdn") or {}
    result = []
    for addr, details in addresses.items():
        try:
            p = phonenumbers.parse(addr, "ZA")
            assert phonenumbers.is_possible_number(p)
            assert phonenumbers.is_valid_number(p)
            p = phonenumbers.format_number(p, phonenumbers.PhoneNumberFormat.E164)
        except Exception as _e:
            logging.exception("Error occurred")
            continue
        if details.get("default"):
            return [p]
        if not details.get("optedout"):
            result.append(p)
    return result


def process_identity(identities, id, details, failed_msgs_count):
    details = details or {}
    addresses = get_addresses(details.get("addresses", {}))
    if not addresses or "redacted" in addresses:
        return

    identities[id] = {
        "msisdns": addresses,
        "failed_msgs_count": failed_msgs_count,
        "uuid": id,
    }
    for k in [
        "operator_id",
        "passport_no",
        "passport_origin",
        "consent",
        "sa_id_no",
        "mom_given_name",
        "mom_family_name",
        "faccode",
        "id_type",
    ]:
        if details.get(k):
            identities[id][k] = details[k]
    language = (
        details.get("lang_code")
        or details.get("language")
        or details.get("preferred_language")
    )
    if language and language in LANGUAGES:
        identities[id]["language"] = language.rstrip("_ZA")
    pmtct_risk = details.get("pmtct", {}).get("risk_status", None)
    if pmtct_risk:
        identities[id]["pmtct_risk"] = pmtct_risk
    dob = details.get("mom_dob") or details.get("dob")
    if dob:
        identities[id]["mom_dob"] = dob


def process_optout(identities, id, created, reason):
    if not identities.get(id):
        return
    created = created.isoformat()
    timestamp = identities[id].get("optout_timestamp")
    if timestamp and timestamp > created:
        return
    identities[id]["optout_timestamp"] = created
    identities[id]["optout_reason"] = reason


def process_registration(identities, id, data):
    if not identities.get(id):
        return
    for k in [
        "edd",
        "faccode",
        "id_type",
        "mom_dob",
        "mom_given_name",
        "mom_family_name",
        "msisdn_device",
        "passport_no",
        "passport_origin",
        "sa_id_no",
        "consent",
    ]:
        if data.get(k) and not identities[id].get(k):
            identities[id][k] = data[k]
    if data.get("baby_dob"):
        if not identities[id].get("baby_dobs"):
            identities[id]["baby_dobs"] = [data["baby_dob"]]
        else:
            identities[id]["baby_dobs"].append(data["baby_dob"])
    uuid_device = data.get("uuid_device") or data.get("operator_id")
    if uuid_device and not identities[id].get("msisdn_device"):
        with contextlib.suppress(Exception):
            identities[id]["msisdn_device"] = identities[uuid_device]["msisdns"][0]
    if (
        data.get("language")
        and not identities[id].get("language")
        and data["language"] in LANGUAGES
    ):
        identities[id]["language"] = data["language"].rstrip("_ZA")


def process_change(identities, id, action, data, created):
    if not identities.get(id):
        return

    created = created.isoformat()
    if "optout" in action:
        timestamp = identities[id].get("optout_timestamp")
        if timestamp and timestamp > created:
            return
        identities[id]["optout_timestamp"] = created
        if data.get("reason"):
            identities[id]["optout_reason"] = data["reason"]
    elif action == "baby_switch":
        baby_dobs = identities[id].get("baby_dobs")
        if not baby_dobs:
            identities[id]["baby_dobs"] = [created]
        else:
            identities[id]["baby_dobs"].append(created)


def process_subscription(identities, id, name, created_at):
    if not identities.get(id):
        return

    created_at = created_at.isoformat()

    if "whatsapp" in name:
        identities[id]["channel"] = "WhatsApp"
    else:
        if not identities[id].get("channel"):
            identities[id]["channel"] = "SMS"

    if "pmtct" in name:
        identities[id]["pmtct_messaging"] = "TRUE"
    elif "loss" in name:
        identities[id]["optout_reason"] = name.split(".")[0].split("_")[-1]
        identities[id]["optout_timestamp"] = created_at
        identities[id]["loss_messaging"] = "TRUE"
    elif (
        "momconnect_prebirth.patient" in name
        or "momconnect_prebirth.hw_partial" in name
    ):
        identities[id]["public_messaging"] = "TRUE"
        identities[id]["public_registration_date"] = created_at
    elif "momconnect_prebirth.hw_full" in name:
        identities[id]["prebirth_messaging"] = name[-1]
    elif "momconnect_postbirth.hw_full" in name:
        identities[id]["postbirth_messaging"] = "TRUE"
    else:
        return


def merge_dicts(d1, d2):
    for k, v in d2.items():
        if isinstance(v, list):
            d1[k] = d1.get(k, []) + v
        else:
            d1[k] = v
    return d1


def deduplicate_msisdns(identities):
    msisdns: dict = {}
    total = 0
    start, d_print = time.time(), time.time()

    for identity in identities.values():
        for msisdn in identity.pop("msisdns"):
            msisdns[msisdn] = merge_dicts(
                msisdns.get(msisdn, {"msisdn": msisdn}), identity
            )
        if time.time() - d_print > 1:
            print(
                f"\rProcessed {total} msisdns at {total/(time.time() - start):.0f}/s",
                end="",
            )
            d_print = time.time()
        total += 1
    print(f"\nProcessed {total} msisdns in {time.time() - start:.0f}s")
    return msisdns


if __name__ == "__main__":
    identities: dict = {}

    conn = psycopg2.connect(
        dbname="identitystore",
        user="identitystore",
        password=os.environ["IDENTITY_PASS"],
        host="localhost",
        port=7000,
    )
    cursor = conn.cursor("identity_store_identities")
    print("Processing identities...")
    cursor.execute(
        """
    SELECT
        id, details, failed_message_count
    FROM
        identities_identity
    """
    )
    total = 0
    start, d_print = time.time(), time.time()
    for id, details, failed_msgs_count in cursor:
        process_identity(identities, id, details, failed_msgs_count)

        if time.time() - d_print > 1:
            print(
                f"\rProcessed {total} identities at "
                f"{total/(time.time() - start):.0f}/s",
                end="",
            )
            d_print = time.time()
        total += 1
    print(f"\nProcessed {total} identities in {time.time() - start:.0f}s")

    print("Processing opt outs...")
    cursor = conn.cursor("identity_store_optouts")
    cursor.execute(
        """
    SELECT
        identity_id, created_at, reason
    FROM
        identities_optout
    """
    )
    total = 0
    start, d_print = time.time(), time.time()
    for id, created, reason in cursor:
        process_optout(identities, id, created, reason)
        if time.time() - d_print > 1:
            print(
                f"\rProcessed {total} optouts at {total/(time.time() - start):.0f}/s",
                end="",
            )
            d_print = time.time()
        total += 1
    print(f"\nProcessed {total} optouts in {time.time() - start:.0f}s")

    print("Processing Registrations...")
    conn = psycopg2.connect(
        dbname="hub",
        user="hub",
        password=os.environ["HUB_PASS"],
        host="localhost",
        port=7000,
    )
    cursor = conn.cursor("hub_registrations")
    cursor.execute(
        """
    SELECT
        registrant_id, data
    FROM
        registrations_registration
    WHERE
        validated=true
    ORDER BY
        created_at ASC
    """
    )
    total = 0
    start, d_print = time.time(), time.time()
    for id, data in cursor:
        process_registration(identities, id, data)
        if time.time() - d_print > 1:
            print(
                f"\rProcessed {total} registrations at "
                f"{total/(time.time() - start):.0f}/s",
                end="",
            )
            d_print = time.time()
        total += 1
    print(f"\nProcessed {total} registrations in {time.time() - start:.0f}s")

    print("Processing Changes...")
    cursor = conn.cursor("hub_changes")
    cursor.execute(
        """
    SELECT
        registrant_id, action, data, created_at
    FROM
        changes_change
    WHERE
        validated=true
    ORDER BY
        created_at ASC
    """
    )
    total = 0
    start, d_print = time.time(), time.time()
    for id, action, data, created in cursor:
        process_change(identities, id, action, data, created)
        if time.time() - d_print > 1:
            print(
                f"\rProcessed {total} changes at {total/(time.time() - start):.0f}/s",
                end="",
            )
            d_print = time.time()
        total += 1
    print(f"\nProcessed {total} changes in {time.time() - start:.0f}s")

    print("Processing subscriptions...")
    conn = psycopg2.connect(
        dbname="stage_based_messaging",
        user="stage_based_messaging",
        password=os.environ["STAGE_PASS"],
        host="localhost",
        port=7000,
    )
    cursor = conn.cursor("stage_subscriptions")
    cursor.execute(
        """
    SELECT
        subscription.identity, messageset.short_name, subscription.created_at
    FROM
        subscriptions_subscription as subscription
    JOIN
        contentstore_messageset as messageset
    ON
        subscription.messageset_id = messageset.id
    WHERE
        subscription.active=true and
        subscription.completed=false and
        subscription.process_status=0
    """
    )
    total = 0
    start, d_print = time.time(), time.time()
    for id, name, created in cursor:
        process_subscription(identities, id, name, created)
        if time.time() - d_print > 1:
            print(
                f"\rProcessed {total} subscriptions at "
                f"{total/(time.time() - start):.0f}/s",
                end="",
            )
            d_print = time.time()
        total += 1
    print(f"\nProcessed {total} subscriptions in {time.time() - start:.0f}s")

    print("Deduplicating msisdns")
    identities = deduplicate_msisdns(identities)

    print("Writing results to file..")
    start = time.time()
    with open("results.json", "w") as f:
        for i in identities.values():
            f.write(json.dumps(i))
            f.write("\n")
    print(f"Wrote results to file in {time.time() - start:.0f}s")
