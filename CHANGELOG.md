# Changelog

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
