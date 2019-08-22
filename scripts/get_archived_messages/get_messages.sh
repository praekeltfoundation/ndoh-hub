#!/bin/bash
set -e

# Check if we have the required amount of arguments
if [ -z "$2" ] ; then
    echo "
Requires start and end date arguments in YYYY-MM-DD format
eg. $0 2019-02-18 2019-02-20
"
    exit 1
fi

d=$1
while [ "$d" != $2 ]; do
    filename="s3://prd-momconnect-archive/outbounds-$d.gz"
    # Skip files that don't exist
    if s3cmd info -q "$filename" 2> /dev/null; then
        s3cmd get -q "$filename" - \
        | gzip -d \
        # Search in parallel, and carry on if we don't find anything in this date
        | parallel --pipe grep -Ff identity_ids || true
    fi
    # Increment date by 1 day
    d=$(gdate -I -d "$d + 1 day")
done
