Add Field For Contacts Stuck In The Registration Consent State
----------------------
The add_field_to_stuck_registration_contacts.py script takes in a CSV in stdin,
and outputs a CSV on stdout. The input CSV is contacts in the stuck state
since the implementation on asking for consent in a clinic prebirth & postbirth
registration.
The output CSV contains the same data as the input CSV, but with and additional
field that notes that an sms should be sent to that contact to complete their
registration.

Use add_field_to_stuck_registration_contacts.py --help to see all of the configuration options.
