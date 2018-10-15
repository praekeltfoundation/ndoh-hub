import csv

from sqlalchemy import MetaData, create_engine
from sqlalchemy.sql import select

# This is an example script and should not be used directly.

# Takes a Jembi provided CSV file of MSISDNs to deactivate and looks up
# the Identity Store ID for each MSISDN and rewrites a new CSV file including
# the Identity Store ID as the last column.
# This is required to make this once off process as fast as possible by
# bypassing the Identity Store API.

engine = create_engine("postgresql://postgres:@localhost/seed_identity_store")
meta = MetaData()
meta.reflect(bind=engine)
tbl = meta.tables["identities_msisdns"]
# The above table doesn't naturally exist in the IS DB, it is created with
# the following raw SQL:
# SELECT
#    id, jsonb_object_keys(details -> 'addresses' -> 'msisdn') AS msisdn
# INTO identities_msisdns
# FROM identities_identity;
# CREATE INDEX identities_msisdns_idx ON identities_msisdns (msisdn);
con = engine.connect()

fn = "jembi.csv"
with open(fn) as csv_file, open("output.csv", "w") as out_file:
    reader = csv.reader(csv_file, delimiter=";")
    writer = csv.writer(out_file, delimiter=";")
    for row in reader:
        msisdn = "+{0}".format(row[1])
        res = con.execute(select([tbl.c.id]).where(tbl.c.msisdn == msisdn)).fetchone()
        new_row = list(row)
        if res:
            new_row.append(res["id"])
        else:
            print("no msisdn match for {}".format(msisdn))
            new_row.append("")
        writer.writerow(new_row)
