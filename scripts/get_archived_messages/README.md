Get archived messages
---------------------
These scripts allow us to fetch and filter the archived messages that are currently
sitting in S3. It will filter the messages to only return messages from identities
listed in `identity_ids`. It returns the messages to stdout.

Dependancies:
 - s3cmd
 - GNU date available at `gdate`
 - GNU parallel available at `parallel`

The first argument is the start date (inclusive), and the second argument is the end
date (non-inclusive). Dates are in YYYY-MM-DD format.
