# Jembi App Registration

This endpoint is designed for new registrations created in Jembi's app to be
sent to us.

The endpoint is available as an HTTP POST to /api/v1/jembiregistration/.

It receives a JSON data in the body of the request which contains the data of
the registration. This data is described in the [registration
fields](#registration-fields) section.

Status updates can be received by specifying a callback URL, or by making a GET
request to /api/v1/jembiregistration/{registration-id}/ . The format of this
status response can be found in the [registration status
fields](#registration-status-fields) section.


## Websocket

The websocket can be found at the same /api/v1/jembiregistration/ endpoint.

Frames are sent using JSON, in the following format:
```json
{
    "action": "...",
    "data": {
        "...": "..."
    }
}
```

`action` can be either `registration` or `status`.

For `registration`, `data` should be the same data sent in [registration
fields](#registration-fields).

For `status`, `data` should have one key, `id`, whose value is the ID (either
external or internal) of the registration that you want to query the status of.

Response frames are sent in JSON, in the same format detailed in [registration
status fields](#registration-status-fields). Status results of registrations
made through the HTTP endpoint are also sent over the websocket.


## Authorization

Authorization is done through tokens, in the authorization header,
eg. `Authorization: Token 4e4448a20bab4f89b9d1dee9641a5d91`

For the websocket, authorization is done through the query parameters, by
passing a token, eg. `?token=4e4448a20bab4f89b9d1dee9641a5d91`


## Registration fields
`external_id` - The ID of the registration in the external service that is
creating it. Optional, defaults to None. If supplied, will be used as the ID in
all status updates. Maximum length of 100 characters allowed. Must be unique.

`mom_given_name` - The given name of the mother. Optional.

`mom_family_name` - The family name of the mother. Optional.

`mom_msisdn` - The phone number of the mother. Required. See
[MSISDNs](#msisdns) for more information on the format of MSISDNs.

`hcw_msisdn` - The phone number of the Health Care Worker (eg. Nurse) that
registered the mother. Required. See [MSISDNs](#msisdns) for more information
on the format of MSISDNs.

`mom_id_type` - The type of identification that the mother used for the
registration. Required. Can be one of "sa_id", "passport", or "none". If
"sa_id", then the "mom_sa_id_no" field must be populated. If "passport", then
both the "mom_passport_no" and "mom_passport_origin" fields must be populated.

`mom_sa_id_no` - The South African SA ID number that the mother used to
register. Required if "mom_id_type" is "sa_id", otherwise optional.

`mom_passport_no` - The passport number that the mother used to register.
Required if "mom_id_type" is "passport", otherwise optional.

`mom_passport_origin` - The country code of the origin of the passport that
the mother used to register. Required if "mom_id_type" is "passport", otherwise
optional. Must be one of "na", "bw", "mz", "sz", "ls", "cu", "zw", "mw", "ng",
"cd", "so", or "other".

`mom_dob` - An ISO 8601 date of when the mother was born. Required.

`mom_lang` - The language code for the language that the mother would prefer
to receive communications in. Required. Must be one of:
"zul_ZA" - isiZulu
"xho_ZA" - isiXhosa
"afr_ZA" - Afrikaans
"eng_ZA" - English
"nso_ZA" - Sesotho sa Leboa / Pedi
"tsn_ZA" - Setswana
"sot_ZA" - Sesotho
"tso_ZA" - Xitsonga
"ssw_ZA" - siSwati
"ven_ZA" - Tshivenda
"nbl_ZA" - isiNdebele

`mom_email` - The email address of the mother. Not required.

`mom_edd` - An ISO 8601 date representing the estimated due date of the
mother. Required.

`mom_consent` - Boolean. Whether the mother has consented to us storing their
information and sending them messages, possibly on weekends and public
holidays. Defaults to False. Must be True.

`mom_opt_in` - Boolean. If the mother has previously opted out, whether or
not to opt the mother back in and continue with the registration, or to cancel
the registration. Defaults to False.

`mom_pmtct` - Boolean. Whether the mother would like to receive additional
messages around the prevention of mother-to-child transmission of HIV/AIDS.
Defaults to False.

`mom_whatsapp` - Boolean. If the mother is registered on the WhatsApp
service, whether or not to send her messages over WhatsApp instead of SMS.
Defaults to False.

`clinic_code` - The code of the clinic where the mother was registered.
Required.

`mha` - An integer ID for the application that created this registration.
Required.

`callback_url` - The URL to call back with the results of the registration.
Optional. See (registration status fields)[#registration-status-fields] for
more information on the format of the status that will be sent back to this
URL.

`callback_auth_token` - The authorization token to use when calling back with
the results of the registration. Optional.

`created` - An ISO 8601 date and time representing when the registration was
created.

Example:
```json
{
    "mom_given_name": "Jane",
    "mom_family_name": "Doe",
    "mom_msisdn": "+27820000000",
    "hcw_msisdn": "+27821111111",
    "mom_id_type": "sa_id",
    "mom_sa_id_no": "8808081234567",
    "mom_dob": "1989-08-08",
    "mom_lang": "xho_ZA",
    "mom_email": "janedoe@example.org",
    "mom_edd": "2018-06-06",
    "mom_consent": true,
    "mom_opt_in": true,
    "mom_pmtct": false,
    "mom_whatsapp": true,
    "clinic_code": "12345",
    "mha": 2,
    "callback_url": "http://www.example.org",
    "callback_auth_token": "4c5b5963a0a34a5993fac78f2ca3b673",
    "created": "2018-03-07T16:25:32+02:00"
}
```


## MSISDNs
MSISDNs are stored as E.164 international numbers. The API endpoint accepts a
variety of formats, with a default country code of South Africa if none is
supplied. The number is also validated to ensure that it's a valid format for a
phone number (number of digits, etc).

Example: 0820000000 will be converted and stored as +27820000000.


## Dates and times
Dates and times should be provided according to the [ISO
8601](https://en.wikipedia.org/wiki/ISO_8601) format. Some fields require just
the date part, and some fields require both date and time.

Date example: `2018-03-07`

Date + time example: `2018-03-07T13:13:20+00:00`


## Registration status fields
`registration_id` - If supplied, the external ID, otherwise the internal ID of
the registration

`registration_data` - The data stored for this registration

`status` - The current status of this registration. Either "succeeded",
"validation_failed", "failed", or "processing"

`error` - Only present when the status is "validation_failed" or "failed". In
the case of "validation_failed", this will be an object where the keys are the
fields that failed validation, and the values are the description of the error
on that field. In the case of "failed", there will be a "type", which is the
type of failure, "message", which will be the failure message, and "traceback",
which will be the traceback info of the error.
