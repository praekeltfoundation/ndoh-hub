# ndoh-hub
NDOH Registration and Change service for MomConnect and NurseConnect

## Registration validity requirements
All registrations should have the following information:
- identity (identity-store id)
- registered_by (identity-store id)
- language (this will also be stored to the identity)
- message_type (this will also be stored to the identity)

Specific stages of pregnancy will require additional information:
- prebirth: last_period_date
- postbirth: baby_dob
- loss: loss_reason

Registrations that show a pregnancy period shorter than 1 week or longer than 42 weeks will be rejected server side.
