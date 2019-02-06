# Changelog

## 0.6.3 (2019-02-06)
1. Add endpoint for receiving failed address lookup webhooks from the message sender
   ([#200](https://github.com/praekeltfoundation/ndoh-hub/pull/200))
1. Change to new Turn API for context objects
   ([#201](https://github.com/praekeltfoundation/ndoh-hub/pull/201))
   ([#202](https://github.com/praekeltfoundation/ndoh-hub/pull/202))
1. Add flag for toggling the WhatsApp unsent event action
   ([#203](https://github.com/praekeltfoundation/ndoh-hub/pull/203))

## 0.6.2 (2019-01-31)
1. Add retries for HTTP failures for process_whatsapp_system_event task
   ([#198](https://github.com/praekeltfoundation/ndoh-hub/pull/198))
1. Fix loss switch change missing language code
   ([#199](https://github.com/praekeltfoundation/ndoh-hub/pull/199))

## 0.6.1 (2019-01-09)
1. Add handling for additional message types from Turn
   ([#197](https://github.com/praekeltfoundation/ndoh-hub/pull/197))

## 0.6.0 (2018-12-18)
1. Add WhatsApp message expiry event handling
   ([#190](https://github.com/praekeltfoundation/ndoh-hub/pull/190))
1. Bug fixes for submission of Turn helpdesk responses to DHIS2
   ([#191](https://github.com/praekeltfoundation/ndoh-hub/pull/191))
1. Updating of translations for SMSes
   ([#192](https://github.com/praekeltfoundation/ndoh-hub/pull/192))
1. Adding prometheus metrics
   ([#193](https://github.com/praekeltfoundation/ndoh-hub/pull/193))

## 0.5.0 (2018-11-28)
1. Fix author field for helpdesk submissions to OpenHIM
   ([#188](https://github.com/praekeltfoundation/ndoh-hub/pull/188))
1. Remove websockets + django channels
   ([#189](https://github.com/praekeltfoundation/ndoh-hub/pull/189))

## 0.4.4 (2018-11-16)
1. Send WhatsApp helpdesk replies to DHIS2
   ([#182](https://github.com/praekeltfoundation/ndoh-hub/pull/182))
   ([#184](https://github.com/praekeltfoundation/ndoh-hub/pull/184))
   ([#185](https://github.com/praekeltfoundation/ndoh-hub/pull/185))
   ([#186](https://github.com/praekeltfoundation/ndoh-hub/pull/186))
   ([#187](https://github.com/praekeltfoundation/ndoh-hub/pull/187))
1. Management command for TeenMomConnect post birth subscriptions
   ([#183](https://github.com/praekeltfoundation/ndoh-hub/pull/183))
1. Ensure that HMAC signature check is secure
   ([b1b6a2b](https://github.com/praekeltfoundation/ndoh-hub/commit/b1b6a2b4f8bc5bbd85a94f163c163f367e92c998))

## 0.4.3 (2018-11-09)
1. Cache junebug lookup for jembi software type.
   ([#179](https://github.com/praekeltfoundation/ndoh-hub/pull/179))
2. Handle race condition in Jembi registration endpoint.
   ([#180](https://github.com/praekeltfoundation/ndoh-hub/pull/180))
3. No sms messageset notification.
   ([#181](https://github.com/praekeltfoundation/ndoh-hub/pull/181))

## 0.4.2 (2018-11-01)
1. Fix channel switch between WhatsApp and SMS for public subscriptions.
   ([#178](https://github.com/praekeltfoundation/ndoh-hub/pull/178))

## 0.4.1 (2018-10-31)
1. Fix service info subscription request function
   ([#175](https://github.com/praekeltfoundation/ndoh-hub/pull/175))
2. Channel switch between WhatsApp and SMS fix for service info subscriptions.
   ([#176](https://github.com/praekeltfoundation/ndoh-hub/pull/176))
   ([#177](https://github.com/praekeltfoundation/ndoh-hub/pull/177))

## 0.4.0 (2018-10-30)
1. Change WhatsApp contact check from Wassup API to Engage API
   ([#174](https://github.com/praekeltfoundation/ndoh-hub/pull/174))

## 0.3.2 (2018-10-17)
### Enhancements
1. Add list of active subscriptions to engage context
   ([#173](https://github.com/praekeltfoundation/ndoh-hub/pull/173))

## 0.3.1 (2018-10-17)
### Enhancements
1. Add endpoint for engage context
   ([#172](https://github.com/praekeltfoundation/ndoh-hub/pull/171))

## 0.3.0 (2018-10-16)
### Enhancements
1. Switch to WhatsApp API for failure event types
   ([#165](https://github.com/praekeltfoundation/ndoh-hub/pull/165))
1. Handling for HSM errors from WhatsApp API
   ([#166](https://github.com/praekeltfoundation/ndoh-hub/pull/166))
1. Translations for SMSes sent from handling of errors
   ([#167](https://github.com/praekeltfoundation/ndoh-hub/pull/167))
1. Handling for Engage system events, undelivered type
   ([#168](https://github.com/praekeltfoundation/ndoh-hub/pull/168))
1. Webhook receiver for Seed Message Sender webhooks, WhatsApp contact check failure
   ([#169](https://github.com/praekeltfoundation/ndoh-hub/pull/168))
### Code Health
1. Upgrade to Django 2.1, and upgrade all other packages
   ([#170](https://github.com/praekeltfoundation/ndoh-hub/pull/170))
1. Add Black automatic formatting and isort import formatting
   ([#171](https://github.com/praekeltfoundation/ndoh-hub/pull/171))
