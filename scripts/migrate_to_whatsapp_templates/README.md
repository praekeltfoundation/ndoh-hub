Migrate to WhatsApp templates
-----------------------------
This folder contains scripts that are useful for migrating existing MomConnect WhatsApp
message sets into ones that are compatible with the new WhatsApp templates.

To use them, use the seed-services-cli to export the current messages. The scripts can
then be used to convert those messages into ones compatible with the new WhatsApp API.
The result of the scripts can then be sent to the seed-services-cli to upload and update
what is in the content store.

Using the scripts is fairly simple. They take in the exported messages on stdin, and
write the output to stdout
