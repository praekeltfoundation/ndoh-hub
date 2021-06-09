import asyncio
import csv
import os
import time
from datetime import datetime, timedelta

import aiohttp
import psycopg2
from six.moves import urllib_parse

CONCURRENCY = 10
HUB_OUTPUT_FILE = "hub_babyswitches.csv"
RAPIDPRO_OUTPUT_FILE = "rapidpro_babyswitch_updates.csv"

LIMIT = 10_000_000
RAPIDPRO_URL = "https://rapidpro.prd.momconnect.co.za/"
RAPIDPRO_TOKEN = os.environ["RAPIDPRO_TOKEN"]

HUB_DB_PASSWORD = os.environ["HUB_PASS"]

total = 0
excluded = 0
start, d_print = time.time(), time.time()


async def get_rapidpro_contact(session, contact_id):
    url = urllib_parse.urljoin(RAPIDPRO_URL, f"/api/v2/contacts.json?uuid={contact_id}")
    headers = {
        "Authorization": f"TOKEN {RAPIDPRO_TOKEN}",
        "Content-Type": "application/json",
        "Connection": "Keep-Alive",
    }
    async with session.get(url, headers=headers) as response:
        response_body = await response.json()

        if response_body["results"]:
            return response_body["results"][0]

        return None


def in_postbirth_group(contact):
    for group in contact["groups"]:
        if "post" in group["name"].lower():
            return True

    return False


def get_contact_msisdn(contact):
    for urn in contact["urns"]:
        if "whatsapp" in urn:
            return "+" + urn.split(":")[1]


def get_baby_dob_field(fields):
    for i in range(1, 4):
        dob_field = f"baby_dob{i}"
        if not fields[dob_field]:
            return dob_field


def get_babyswitches(conn):
    babyswitches = {}
    cursor = conn.cursor("baby_switches")
    print("Fetching Baby Switches...")
    cursor.execute(
        f"""
        select contact_id, timestamp
        from eventstore_babyswitch
        order by timestamp asc
        limit {LIMIT}
        """
    )  # 158680
    total = 0
    start, d_print = time.time(), time.time()
    for (contact_id, timestamp) in cursor:
        babyswitches[contact_id] = timestamp

        if time.time() - d_print > 1:
            print(
                f"\rFetched {total} babyswitches at "
                f"{total/(time.time() - start):.0f}/s",
                end="",
            )
            d_print = time.time()
        total += 1
    print(f"\nFetched {total} babyswitches in {time.time() - start:.0f}s")
    print("-------------------------------------------")
    return babyswitches


def get_optouts(conn):
    optouts = {}

    print("Fetching Optouts...")
    cursor = conn.cursor("optouts")
    cursor.execute(
        f"""
        select contact_id, timestamp
        from eventstore_optout
        order by timestamp asc
        limit {LIMIT}
        """
    )  # 255855
    total = 0
    start, d_print = time.time(), time.time()
    for (contact_id, timestamp) in cursor:
        optouts[contact_id] = timestamp

        if time.time() - d_print > 1:
            print(
                f"\rFetched {total} optouts at " f"{total/(time.time() - start):.0f}/s",
                end="",
            )
            d_print = time.time()
        total += 1
    print(f"\nFetched {total} optouts in {time.time() - start:.0f}s")
    print("-------------------------------------------")
    return optouts


def get_registrations(conn, babyswitches, optouts):
    registrations = []

    print("Fetching Prebirth Registrations...")
    cursor = conn.cursor("prebirth_registrations")
    cursor.execute(
        f"""
        select contact_id, timestamp
        from eventstore_prebirthregistration
        where edd < '2021-04-20'
        order by timestamp asc
        limit {LIMIT}
        """
    )  # 216808
    total = 0
    start, d_print = time.time(), time.time()
    for (contact_id, timestamp) in cursor:
        if contact_id in babyswitches and timestamp < babyswitches[contact_id]:
            continue
        if contact_id in optouts and timestamp < optouts[contact_id]:
            continue
        registrations.append(contact_id)

        if time.time() - d_print > 1:
            print(
                f"\rFetched {total} registrations at "
                f"{total/(time.time() - start):.0f}/s",
                end="",
            )
            d_print = time.time()
        total += 1
    print(f"\nFetched {total} registrations in {time.time() - start:.0f}s")
    print("-------------------------------------------")
    return registrations


async def process_registration(session, contact_id, hub_writer, rp_writer):
    global total
    global excluded
    global d_print
    global start

    total += 1

    contact = await get_rapidpro_contact(session, contact_id)

    if contact:
        msisdn = get_contact_msisdn(contact)

        in_group = in_postbirth_group(contact)
        if (
            in_group
            or not msisdn
            or contact["fields"].get("preferred_channel") != "WhatsApp"
        ):
            excluded += 1
        else:
            baby_dob_field = get_baby_dob_field(contact["fields"])
            edd = str(contact["fields"]["edd"]).replace("Z", "")
            try:
                dob = datetime.fromisoformat(edd) + timedelta(days=14)
            except (TypeError, ValueError):
                excluded += 1
                return

            rp_writer.writerow(
                {
                    "contact_id": contact_id,
                    "baby_dob_field": baby_dob_field,
                    "baby_dob": dob.isoformat(),
                }
            )

            # write to csv for jembi and hub
            hub_writer.writerow(
                {
                    "contact_id": contact_id,
                    "msisdn": msisdn,
                    "timestamp": datetime.now().isoformat(),
                }
            )

    if time.time() - d_print > 1:
        print(
            f"\rProcessed {total}({excluded}) registrations at "
            f"{total/(time.time() - start):.0f}/s",
            end="",
        )
        d_print = time.time()


async def bounded_process_registration(session, contact_id, hub_writer, rp_writer, sem):
    async with sem:
        await process_registration(session, contact_id, hub_writer, rp_writer)


async def process_registrations(registrations):
    global total
    global start

    sema = asyncio.Semaphore(CONCURRENCY)

    print("Processing Registrations...")
    with open(HUB_OUTPUT_FILE, "w", newline="") as hub_target, open(
        RAPIDPRO_OUTPUT_FILE, "w", newline=""
    ) as rp_target:
        hub_writer = csv.DictWriter(
            hub_target, fieldnames=["contact_id", "msisdn", "timestamp"]
        )
        hub_writer.writeheader()
        rp_writer = csv.DictWriter(
            rp_target, fieldnames=["contact_id", "baby_dob_field", "baby_dob"]
        )
        rp_writer.writeheader()

        connector = aiohttp.TCPConnector(limit=CONCURRENCY)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = []
            for contact_id in registrations:
                tasks.append(
                    bounded_process_registration(
                        session, contact_id, hub_writer, rp_writer, sema
                    )
                )

            await asyncio.gather(*tasks)
        print(f"\nProcessed {total} registrations in {time.time() - start:.0f}s")


if __name__ == "__main__":
    conn = psycopg2.connect(
        dbname="hub", user="hub", password=HUB_DB_PASSWORD, host="localhost", port=7000
    )
    babyswitches = get_babyswitches(conn)
    optouts = get_optouts(conn)
    registrations = get_registrations(conn, babyswitches, optouts)

    asyncio.run(process_registrations(registrations))
