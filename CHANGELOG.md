# Changelog

## 0.8.2 (2020-03-04)
1. Fix for rapidpro contacts with None as language
   ([#303](https://github.com/praekeltfoundation/ndoh-hub/pull/303))
1. Fix for rapidpro contacts not found
   ([#304](https://github.com/praekeltfoundation/ndoh-hub/pull/304))


## 0.8.1 (2020-03-04)
1. Retry TembaHttpError
   ([#301](https://github.com/praekeltfoundation/ndoh-hub/pull/301))
1. Optout user after n delivery failures
   ([#298](https://github.com/praekeltfoundation/ndoh-hub/pull/298))
   ([#302](https://github.com/praekeltfoundation/ndoh-hub/pull/302))

## 0.8.0 (2020-02-26)
1. Migration to RapidPro
   ([#300](https://github.com/praekeltfoundation/ndoh-hub/pull/300))
   ([#299](https://github.com/praekeltfoundation/ndoh-hub/pull/299))
   ([#297](https://github.com/praekeltfoundation/ndoh-hub/pull/297))
   ([#296](https://github.com/praekeltfoundation/ndoh-hub/pull/296))
   ([#295](https://github.com/praekeltfoundation/ndoh-hub/pull/295))
   ([#293](https://github.com/praekeltfoundation/ndoh-hub/pull/293))
   ([#292](https://github.com/praekeltfoundation/ndoh-hub/pull/292))
   ([#290](https://github.com/praekeltfoundation/ndoh-hub/pull/290))
   ([#289](https://github.com/praekeltfoundation/ndoh-hub/pull/289))
   ([#287](https://github.com/praekeltfoundation/ndoh-hub/pull/287))
   ([#286](https://github.com/praekeltfoundation/ndoh-hub/pull/286))
   ([#285](https://github.com/praekeltfoundation/ndoh-hub/pull/285))
   ([#284](https://github.com/praekeltfoundation/ndoh-hub/pull/284))
   ([#283](https://github.com/praekeltfoundation/ndoh-hub/pull/283))
   ([#282](https://github.com/praekeltfoundation/ndoh-hub/pull/282))
   ([#281](https://github.com/praekeltfoundation/ndoh-hub/pull/281))
   ([#280](https://github.com/praekeltfoundation/ndoh-hub/pull/280))
   ([#279](https://github.com/praekeltfoundation/ndoh-hub/pull/279))
   ([#278](https://github.com/praekeltfoundation/ndoh-hub/pull/278))
   ([#277](https://github.com/praekeltfoundation/ndoh-hub/pull/277))
   ([#276](https://github.com/praekeltfoundation/ndoh-hub/pull/276))
   ([#275](https://github.com/praekeltfoundation/ndoh-hub/pull/275))
   ([#274](https://github.com/praekeltfoundation/ndoh-hub/pull/274))
   ([#273](https://github.com/praekeltfoundation/ndoh-hub/pull/273))
   ([#272](https://github.com/praekeltfoundation/ndoh-hub/pull/272))

## 0.7.9 (2019-12-05)
1. Upgrade Django to 2.2.8 (Security vulnerability patch)
   ([#271](https://github.com/praekeltfoundation/ndoh-hub/pull/271))
1. Trigger RapidPro flow on receiving operator replies in eventstore
   ([#270](https://github.com/praekeltfoundation/ndoh-hub/pull/270))
1. Add flag for disabling all actions to whatsapp events
   ([#269](https://github.com/praekeltfoundation/ndoh-hub/pull/269))
1. Send Jembi registration to RapidPro if flag is set
   ([#268](https://github.com/praekeltfoundation/ndoh-hub/pull/268))
   ([#266](https://github.com/praekeltfoundation/ndoh-hub/pull/266))
1. Fix docs and warnings
   ([#267](https://github.com/praekeltfoundation/ndoh-hub/pull/267))

## 0.7.8 (2019-11-26)
1. Storing Messages in the Event store
   ([#265](https://github.com/praekeltfoundation/ndoh-hub/pull/265))

## 0.7.7 (2019-11-05)
1. Make sending events to Jembi optional
   ([#264](https://github.com/praekeltfoundation/ndoh-hub/pull/264))

## 0.7.6 (2019-10-31)
1. Store jembi requests before forwarding
   ([#261](https://github.com/praekeltfoundation/ndoh-hub/pull/261))
1. Restrict event store passport country field to list of choices
   ([#262](https://github.com/praekeltfoundation/ndoh-hub/pull/262))
1. Add API for storing + relaying nurseconnect subscriptions to Jembi
   ([#263](https://github.com/praekeltfoundation/ndoh-hub/pull/263))

## 0.7.5 (2019-10-30)
1. Fix sending of third party registrations to RapidPro
   ([#257](https://github.com/praekeltfoundation/ndoh-hub/pull/257))
1. Add CHW registrations to the event store
   ([#258](https://github.com/praekeltfoundation/ndoh-hub/pull/258))
1. Add API that mirrors Jembi's clinic code API
   ([#259](https://github.com/praekeltfoundation/ndoh-hub/pull/259))
   ([#260](https://github.com/praekeltfoundation/ndoh-hub/pull/260))

## 0.7.4 (2019-10-24)
1. Cache querystring token auth

## 0.7.3 (2019-10-24)
1. Allow third party registrations to be sent to RapidPro
   ([#255](https://github.com/praekeltfoundation/ndoh-hub/pull/255))
1. Bug fix for Turn context API
   ([#256](https://github.com/praekeltfoundation/ndoh-hub/pull/256))

## 0.7.2 (2019-10-18)
1. Create event store with support for opt outs, baby switches, channel switches,
   public, pre- and postbirth clinic registrations.
   ([#247](https://github.com/praekeltfoundation/ndoh-hub/pull/247))
   ([#248](https://github.com/praekeltfoundation/ndoh-hub/pull/248))
   ([#249](https://github.com/praekeltfoundation/ndoh-hub/pull/249))
   ([#250](https://github.com/praekeltfoundation/ndoh-hub/pull/250))
   ([#251](https://github.com/praekeltfoundation/ndoh-hub/pull/251))
   ([#252](https://github.com/praekeltfoundation/ndoh-hub/pull/252))
   ([#253](https://github.com/praekeltfoundation/ndoh-hub/pull/253))
1. Changes to handle changes in Turn Context API
   ([#254](https://github.com/praekeltfoundation/ndoh-hub/pull/254))

## 0.7.1 (2019-09-03)
1. Upgrade django to 2.2.4
   ([#241](https://github.com/praekeltfoundation/ndoh-hub/pull/241))
1. Cache auth token lookup
   ([#243](https://github.com/praekeltfoundation/ndoh-hub/pull/243))
1. Handle null message type when processing whatsapp messages
   ([#245](https://github.com/praekeltfoundation/ndoh-hub/pull/245))
1. Add script for getting archived messages
   ([#246](https://github.com/praekeltfoundation/ndoh-hub/pull/246))

## 0.7.0 (2019-08-19)
1. Send registrations via WhatsApp to Jembi
   ([#232](https://github.com/praekeltfoundation/ndoh-hub/pull/232))
   ([#234](https://github.com/praekeltfoundation/ndoh-hub/pull/234))
1. Send event and system IDs to Jembi
   ([#235](https://github.com/praekeltfoundation/ndoh-hub/pull/235))
   ([#236](https://github.com/praekeltfoundation/ndoh-hub/pull/236))
   ([#237](https://github.com/praekeltfoundation/ndoh-hub/pull/237))
   ([#240](https://github.com/praekeltfoundation/ndoh-hub/pull/240))
   ([#242](https://github.com/praekeltfoundation/ndoh-hub/pull/242))
1. Bug fix: opt in after registration
   ([#238](https://github.com/praekeltfoundation/ndoh-hub/pull/238))
1. Send welcome message after successful prebirth registration
   ([#239](https://github.com/praekeltfoundation/ndoh-hub/pull/239))


## 0.6.7 (2019-06-20)
1. Add missing translations
   ([#216](https://github.com/praekeltfoundation/ndoh-hub/pull/216))
   ([#217](https://github.com/praekeltfoundation/ndoh-hub/pull/217))
1. Active subscriptions API
   ([#218](https://github.com/praekeltfoundation/ndoh-hub/pull/218))
   ([#219](https://github.com/praekeltfoundation/ndoh-hub/pull/219))
   ([#227](https://github.com/praekeltfoundation/ndoh-hub/pull/227))
   ([#231](https://github.com/praekeltfoundation/ndoh-hub/pull/231))
1. Update security dependancies
   ([#220](https://github.com/praekeltfoundation/ndoh-hub/pull/220))
1. API for facility code check
   ([#221](https://github.com/praekeltfoundation/ndoh-hub/pull/221))
   ([#222](https://github.com/praekeltfoundation/ndoh-hub/pull/222))
1. APIs for creating registrations from RapidPro
   ([#223](https://github.com/praekeltfoundation/ndoh-hub/pull/223))
   ([#224](https://github.com/praekeltfoundation/ndoh-hub/pull/224))
   ([#226](https://github.com/praekeltfoundation/ndoh-hub/pull/226))
   ([#228](https://github.com/praekeltfoundation/ndoh-hub/pull/228))
   ([#229](https://github.com/praekeltfoundation/ndoh-hub/pull/229))
1. Postbirth registrations for MomConnect
   ([#225](https://github.com/praekeltfoundation/ndoh-hub/pull/225))

## 0.6.6 (2019-05-14)
1. Add missing translations
   ([#213](https://github.com/praekeltfoundation/ndoh-hub/pull/213))
1. Add new view for proxying the health check to the OpenHIM API
   ([#214](https://github.com/praekeltfoundation/ndoh-hub/pull/214))
1. Add new view for proxying WhatsApp contact checks
   ([#215](https://github.com/praekeltfoundation/ndoh-hub/pull/215))

## 0.6.5 (2019-04-23)
1. Add scripts for extract for GrowGreat send
   ([#209](https://github.com/praekeltfoundation/ndoh-hub/pull/209))
1. Update WhatsApp language mapping to use english for all languages
   ([#210](https://github.com/praekeltfoundation/ndoh-hub/pull/210))
1. Add script for annotating export with registration data
   ([#211](https://github.com/praekeltfoundation/ndoh-hub/pull/211))
1. Use async refreshing of Turn helpdesk context on action completion
   ([#212](https://github.com/praekeltfoundation/ndoh-hub/pull/212))

## 0.6.4 (2019-03-27)
1. Add actions to Turn context
   ([#204](https://github.com/praekeltfoundation/ndoh-hub/pull/204))
   ([#208](https://github.com/praekeltfoundation/ndoh-hub/pull/208))
1. Change to using new WhatsApp templates for outbounds WhatsApp messages
   ([#205](https://github.com/praekeltfoundation/ndoh-hub/pull/205))
1. Add helper scripts for migrating existing messagesets to use WhatsApp templates
   ([#206](https://github.com/praekeltfoundation/ndoh-hub/pull/206))
   ([#207](https://github.com/praekeltfoundation/ndoh-hub/pull/207))

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
