GrowGreat Campaign Extract
--------------------------
This folder contains scripts to extract the required MSISDNs for a message send
for a campaign for GrowGreat.

These scripts require you to have SSH access into the database VMs, in order to
get the required information from the database.

The should be executed in this order:

get_registrations.sh - Filters registrations according to the criteria, to get
a list of identity UUIDs that we want to send messages to.

get_current_channel.sh - takes the list of identity UUIDs (from
get_registrations.sh) and outputs the list of identities with their
current active channel

filter.sh - takes the output from get_current_channel.sh, and filters according
to the first argument. Also removes the channel. Allows you to split according
to channel.

get_msisdn.sh - takes in identity ids, and returns msisdns for those identities

If the number of elements in large, then you might run into an "Argument list too long" error. In this case, using GNU Parallel can help, eg:

cat registrations.csv | parallel --pipe -N 1000 ./get_current_channel.sh > output.csv
