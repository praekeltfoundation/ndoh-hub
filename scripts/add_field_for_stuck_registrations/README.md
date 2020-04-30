Add Field For Contacts Stuck In The Registration Consent State
----------------------
The add_field_to_stuck_registration_contacts.py script takes in a CSV in stdin
The input CSV is uuids of contacts in the stuck state
since the implementation on asking for consent in a clinic prebirth & postbirth
registration.

The script adds a stuck_in_consent_state field to the Contacts
