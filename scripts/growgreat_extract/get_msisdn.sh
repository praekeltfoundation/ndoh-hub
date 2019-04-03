#!/bin/sh

ids=""

while read -r line; do
    ids="$ids'$line',"
done

ids=${ids%?};

ssh -C prd-ndoh-db03.za.p16n.org "sudo -u postgres psql -d identitystore -c \"copy (
select
    identity.details
from 
    identities_identity as identity
where
    identity.id in ($ids)
) to STDOUT \"" | python msisdn_from_details.py
