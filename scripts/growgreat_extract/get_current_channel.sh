#!/bin/sh

ids=""

while read -r line; do
    ids="$ids'$line',"
done

ids=${ids%?};

ssh -C prd-ndoh-db03.za.p16n.org "sudo -u postgres psql -d stage_based_messaging -c \"copy (
select
    subscription.identity,
    case
        when messageset.short_name ilike '%whatsapp%' then 'whatsapp'
        else 'sms'
    end
from 
    subscriptions_subscription as subscription
join
    contentstore_messageset as messageset
on
    subscription.messageset_id = messageset.id
where
    subscription.identity in ($ids) and
    active=true and
    completed=false and
    process_status=0
) to STDOUT with CSV DELIMITER ','\"" | sort | uniq
