# Changelog

# 0.10.18
1. Add openhim queue model and signal
   ([#590](https://github.com/praekeltfoundation/ndoh-hub/pull/590))
   ([#591](https://github.com/praekeltfoundation/ndoh-hub/pull/591))
   ([#592](https://github.com/praekeltfoundation/ndoh-hub/pull/592))

# 0.10.17
1. Add optout reason to model
   ([#587](https://github.com/praekeltfoundation/ndoh-hub/pull/587))
# 0.10.16
1. Push MQR Fix Send Date
   ([#583](https://github.com/praekeltfoundation/ndoh-hub/pull/583))

# 0.10.15
1. Push docker image to ghcr
   ([#582](https://github.com/praekeltfoundation/ndoh-hub/pull/582))

# 0.10.14
1. Events Export API
   ([#578](https://github.com/praekeltfoundation/ndoh-hub/pull/578))
1. Delete historical records management command
   ([#579](https://github.com/praekeltfoundation/ndoh-hub/pull/579))
   ([#580](https://github.com/praekeltfoundation/ndoh-hub/pull/580))
   ([#581](https://github.com/praekeltfoundation/ndoh-hub/pull/581))

# 0.10.13
1. Bump django from 4.1.9 to 4.1.10
   ([#575](https://github.com/praekeltfoundation/ndoh-hub/pull/576))

# 0.10.12
1. Added handling of non-text (media) input
   ([#576](https://github.com/praekeltfoundation/ndoh-hub/pull/576))

## 0.10.11
1. Add privacy policy PDF
   ([#568](https://github.com/praekeltfoundation/ndoh-hub/pull/568))
1. Fix WA error payload
   ([#569](https://github.com/praekeltfoundation/ndoh-hub/pull/569))
1. Manage fallback channel
   ([#570](https://github.com/praekeltfoundation/ndoh-hub/pull/570))
1. Add delivery failure api to add and view
   ([#571](https://github.com/praekeltfoundation/ndoh-hub/pull/571))
1. Refactor starting flow on 5 failures
   ([#573](https://github.com/praekeltfoundation/ndoh-hub/pull/573))
1. Fix deliveryfailure get not found
   ([#574](https://github.com/praekeltfoundation/ndoh-hub/pull/574))

## 0.10.10
1. Use registration date instead of today
   ([#566](https://github.com/praekeltfoundation/ndoh-hub/pull/566))
1. Rename argument
   ([#567](https://github.com/praekeltfoundation/ndoh-hub/pull/567))

## 0.10.9
1. Added gibberish input detection to AAQ
   ([#562](https://github.com/praekeltfoundation/ndoh-hub/pull/562))
1. Split out midweek arm message
   ([#564](https://github.com/praekeltfoundation/ndoh-hub/pull/564))

## 0.10.8
1. Send WhatsApp Template endpoint
   ([#552](https://github.com/praekeltfoundation/ndoh-hub/pull/552))
   ([#554](https://github.com/praekeltfoundation/ndoh-hub/pull/554))
   ([#555](https://github.com/praekeltfoundation/ndoh-hub/pull/555))
   ([#556](https://github.com/praekeltfoundation/ndoh-hub/pull/556))
   ([#560](https://github.com/praekeltfoundation/ndoh-hub/pull/560))
1. Bump django from 4.1.7 to 4.1.9
   ([#553](https://github.com/praekeltfoundation/ndoh-hub/pull/553))
1. Handle replies with only special characters for Input Type
   ([#557](https://github.com/praekeltfoundation/ndoh-hub/pull/557))
1. MQR split out ARM next message view
   ([#558](https://github.com/praekeltfoundation/ndoh-hub/pull/558))
1. Bump requests from 2.28.2 to 2.31.0
   ([#559](https://github.com/praekeltfoundation/ndoh-hub/pull/559))
1. Minor tweaks to random contact slack post
   ([#561](https://github.com/praekeltfoundation/ndoh-hub/pull/561))

## 0.10.7
1. Rename assessment report
  ([#549](https://github.com/praekeltfoundation/ndoh-hub/pull/549))

## 0.10.6
1. Delay forget_contact task
  ([#545](https://github.com/praekeltfoundation/ndoh-hub/pull/545))

## 0.10.5
1. Add index to message.contact_id
  ([#544](https://github.com/praekeltfoundation/ndoh-hub/pull/544))
1. Bump redis from 4.5.3 to 4.5.4
  ([#537](https://github.com/praekeltfoundation/ndoh-hub/pull/537))

## 0.10.4
1. Move message insert/update to celery task
  ([#543](https://github.com/praekeltfoundation/ndoh-hub/pull/543))

## 0.10.3
1. Add index to event.recipient_id concurrently
  ([#542](https://github.com/praekeltfoundation/ndoh-hub/pull/542))

## 0.10.2
1. Add setting to disable bulk inserts
  ([#541](https://github.com/praekeltfoundation/ndoh-hub/pull/541))

## 0.10.1
1. Batch insert WA events
  ([#536](https://github.com/praekeltfoundation/ndoh-hub/pull/536))
  ([#539](https://github.com/praekeltfoundation/ndoh-hub/pull/539))
  ([#540](https://github.com/praekeltfoundation/ndoh-hub/pull/540))

## 0.10.0
1. Upgrade to Django 4
  ([#532](https://github.com/praekeltfoundation/ndoh-hub/pull/532))

## 0.9.64
1. Handle timeouts
  ([#530](https://github.com/praekeltfoundation/ndoh-hub/pull/530))

## 0.9.4
1. Flag to disable expire helpdesk task
  ([#434](https://github.com/praekeltfoundation/ndoh-hub/pull/434))

## 0.9.3
1. Changed turn url format
  ([#430](https://github.com/praekeltfoundation/ndoh-hub/pull/430))

## 0.9.2
1. Add age field to registration models
  ([#429](https://github.com/praekeltfoundation/ndoh-hub/pull/429))

## 0.9.1
1. Add token auth to facilitycheck endpoint

## 0.9.0
1. Add ask feedback model and view
  ([#416](https://github.com/praekeltfoundation/ndoh-hub/pull/416))
1. Add AskFeedback to admin
  ([#417](https://github.com/praekeltfoundation/ndoh-hub/pull/417))
1. Change ask feedback into more generic model
  ([#418](https://github.com/praekeltfoundation/ndoh-hub/pull/418))
1. Random contacts information
  ([#419](https://github.com/praekeltfoundation/ndoh-hub/pull/419))
1. Random contact debug info
  ([#421](https://github.com/praekeltfoundation/ndoh-hub/pull/421))
1. Slack text message link tags
  ([#422](https://github.com/praekeltfoundation/ndoh-hub/pull/422))
1. Library upgrade and python version upgrade + major cleanup
  ([#423](https://github.com/praekeltfoundation/ndoh-hub/pull/423)
1. Bump django-filter from 2.0.0 to 2.4.0
  ([#424](https://github.com/praekeltfoundation/ndoh-hub/pull/424))
1. Bump django from 2.2.24 to 2.2.26
  ([#425](https://github.com/praekeltfoundation/ndoh-hub/pull/425))
1. Remove hooks and refs to registr & changes tasks
  ([#426](https://github.com/praekeltfoundation/ndoh-hub/pull/426))
1. Fix facility code check
  ([#427](https://github.com/praekeltfoundation/ndoh-hub/pull/427))
1. Add contacts endpoint again
  ([#428](https://github.com/praekeltfoundation/ndoh-hub/pull/428))

## 0.8.51
1. Handle whatsapp failure events too
  ([#414](https://github.com/praekeltfoundation/ndoh-hub/pull/414))
2. Increase optout reason field size
  ([#415](https://github.com/praekeltfoundation/ndoh-hub/pull/415))

## 0.8.50
1. Remove healthcheck Turn update task
  ([#412](https://github.com/praekeltfoundation/ndoh-hub/pull/412))

## 0.8.49
1. HCS Study A fixes
  ([#410](https://github.com/praekeltfoundation/ndoh-hub/pull/410))
  ([#411](https://github.com/praekeltfoundation/ndoh-hub/pull/411))

## 0.8.48
1. Fail gcc import validation for existing postbirth registration
  ([#408](https://github.com/praekeltfoundation/ndoh-hub/pull/408))
1. Change error message
  ([#409](https://github.com/praekeltfoundation/ndoh-hub/pull/409))

## 0.8.47
1. Update hcs study randomization + remove pilot c study
  ([#406](https://github.com/praekeltfoundation/ndoh-hub/pull/406))
1. Add disabled EDD flow setting
  ([#407](https://github.com/praekeltfoundation/ndoh-hub/pull/407))

## 0.8.46
1. Update docker cmd - cpu usage
  ([#405](https://github.com/praekeltfoundation/ndoh-hub/pull/405))

## 0.8.45
1. Add source field to mcimport
  ([#402](https://github.com/praekeltfoundation/ndoh-hub/pull/402))
1. Add baby dob fields to import
  ([#403](https://github.com/praekeltfoundation/ndoh-hub/pull/403))
1. Allow empty language to be specified
  ([#404](https://github.com/praekeltfoundation/ndoh-hub/pull/404))

## 0.8.36
1. Stop sending SMSes on whatsapp send errors
  ([#376](https://github.com/praekeltfoundation/ndoh-hub/pull/376))

## 0.8.35
1. Unused code cleanup
  ([#369](https://github.com/praekeltfoundation/ndoh-hub/pull/369))
1. Complete implementation of ada assessment notification webhook endpoint
  ([#370](https://github.com/praekeltfoundation/ndoh-hub/pull/370))
  ([#371](https://github.com/praekeltfoundation/ndoh-hub/pull/371))
1. Add additional field options for momconnect import
  ([#372](https://github.com/praekeltfoundation/ndoh-hub/pull/372))
1. Show proper error on invalid date format during momconnect import
  ([#373](https://github.com/praekeltfoundation/ndoh-hub/pull/373))
1. Add tracking for start of healthcheck
  ([#374](https://github.com/praekeltfoundation/ndoh-hub/pull/374))
  ([#375](https://github.com/praekeltfoundation/ndoh-hub/pull/375))

## 0.8.34
1. Add async bulk archive scripts
  ([#363](https://github.com/praekeltfoundation/ndoh-hub/pull/363))
1. Add momconnect CSV import
  ([#364](https://github.com/praekeltfoundation/ndoh-hub/pull/364))
  ([#365](https://github.com/praekeltfoundation/ndoh-hub/pull/365))
  ([#366](https://github.com/praekeltfoundation/ndoh-hub/pull/366))
1. Add ada assessment notification webhook endpoint
  ([#367](https://github.com/praekeltfoundation/ndoh-hub/pull/367))
1. Add forget contact endpoint
  ([#368](https://github.com/praekeltfoundation/ndoh-hub/pull/368))

## 0.8.33
1. Fix Celery Beat Schedule settings
  ([#361](https://github.com/praekeltfoundation/ndoh-hub/pull/361))
2. Update bulk archive and sync script
  ([#362](https://github.com/praekeltfoundation/ndoh-hub/pull/362))

## 0.8.32
1. Fix LockNotOwnedError on get_whatsapp_contact
  ([#360](https://github.com/praekeltfoundation/ndoh-hub/pull/360))

## 0.8.31
1. Handle sticker message type from turn
2. Remove travis.yml
  ([#359](https://github.com/praekeltfoundation/ndoh-hub/pull/359))

## 0.8.30
1. Retry task on HTTPError from turn
  ([#358](https://github.com/praekeltfoundation/ndoh-hub/pull/358))

## 0.8.29
1. DBE expanded comorbidities
  ([#356](https://github.com/praekeltfoundation/ndoh-hub/pull/356))

## 0.8.28
1. DBE multiple child profiles
  ([#355](https://github.com/praekeltfoundation/ndoh-hub/pull/355))

## 0.8.27
1. Change clinic code lookup index to be on the correct field

## 0.8.26
1. Add index for clinic code lookups
  ([#354](https://github.com/praekeltfoundation/ndoh-hub/pull/337))

## 0.8.25
1. Add bulk archive script
  ([#337](https://github.com/praekeltfoundation/ndoh-hub/pull/337))
1. Modify WhatsApp contact lookup to more closely mirror actual API
  ([#353](https://github.com/praekeltfoundation/ndoh-hub/pull/353))

## 0.8.24
1. Fix preexisting_conditions/preexisting_condition for user profile
  ([#350](https://github.com/praekeltfoundation/ndoh-hub/pull/350))
1. Add place_of_work and new v4 API for it for covid19triage
  ([#351](https://github.com/praekeltfoundation/ndoh-hub/pull/351))

## 0.8.23
1. Add user profiles for healthchecks
  ([#349](https://github.com/praekeltfoundation/ndoh-hub/pull/349))

## 0.8.22
1. Use cache lock to avoid sending duplicate SMSs on WhatsApp failures
  ([#346](https://github.com/praekeltfoundation/ndoh-hub/pull/346))
  ([#347](https://github.com/praekeltfoundation/ndoh-hub/pull/347))

## 0.8.21
1. Limit delivery failures to 1 per day
  ([#345](https://github.com/praekeltfoundation/ndoh-hub/pull/345))

## 0.8.20
1. Reset delivery failure count on new registrations
  ([#343](https://github.com/praekeltfoundation/ndoh-hub/pull/343))
  ([#344](https://github.com/praekeltfoundation/ndoh-hub/pull/344))

## 0.8.19
1. Add disable sms failure optouts flag
  ([#342](https://github.com/praekeltfoundation/ndoh-hub/pull/342))

## 0.8.18
1. Changed rapidpro variable for channel preference
  ([#339](https://github.com/praekeltfoundation/ndoh-hub/pull/339))

## 0.8.17
1. Added CHWRegistration to django admin
  ([#336](https://github.com/praekeltfoundation/ndoh-hub/pull/336))
1. ran registration migration
  ([#321](https://github.com/praekeltfoundation/ndoh-hub/pull/321))

## 0.8.16
1. Add functionality to the API for healthcheck returning users
   ([#326](https://github.com/praekeltfoundation/ndoh-hub/pull/326))
1. Add task to update Turn Contact on completed healthchecks
   ([#327](https://github.com/praekeltfoundation/ndoh-hub/pull/327))
1. Fix duplicate optouts happening
   ([#332](https://github.com/praekeltfoundation/ndoh-hub/pull/332))

## 0.8.15
1. Fix docker image translations

## 0.8.14
1. Additional fields for covid19 triage confirmed contact
   ([#324](https://github.com/praekeltfoundation/ndoh-hub/pull/324))
1. Add management command for filling in channel for historical registrations
   ([#321](https://github.com/praekeltfoundation/ndoh-hub/pull/321))
1. Add script for manipulating rapidpro contact fields
   ([#322](https://github.com/praekeltfoundation/ndoh-hub/pull/322))
   ([#323](https://github.com/praekeltfoundation/ndoh-hub/pull/323))


## 0.8.13 (2020-04-14)
1. Rate limits for covid19triage endpoint
   ([#320](https://github.com/praekeltfoundation/ndoh-hub/pull/320))

## 0.8.12 (2020-04-14)
1. Return 200 for duplicate covid19 triage entries
   ([#319](https://github.com/praekeltfoundation/ndoh-hub/pull/319))
1. Add API for fetching covid19 triage data
   ([#317](https://github.com/praekeltfoundation/ndoh-hub/pull/317))
1. Add difficulty_breathing field to covid19 triage
   ([#316](https://github.com/praekeltfoundation/ndoh-hub/pull/316))
1. Add district field to CDU address update
   ([#315](https://github.com/praekeltfoundation/ndoh-hub/pull/315))

## 0.8.10 (2020-04-07)

1. Add msisdn column to CDU address updates
   ([#314](https://github.com/praekeltfoundation/ndoh-hub/pull/314))

## 0.8.9 (2020-04-06)

1. Add CDU address updates to admin
   ([#313](https://github.com/praekeltfoundation/ndoh-hub/pull/313))

## 0.8.8 (2020-04-06)

1. Add table for storing CDU address updates
   ([#312](https://github.com/praekeltfoundation/ndoh-hub/pull/312))

## 0.8.7 (2020-04-03)

1. Add table for storing covid19 triage results
   ([#311](https://github.com/praekeltfoundation/ndoh-hub/pull/311))

## 0.8.6 (2020-03-19)

1. Trigger flows for 'EDD SWITCH' keyword instead of 'EDD'
   ([#309](https://github.com/praekeltfoundation/ndoh-hub/pull/309))

## 0.8.4 (2020-03-09)

1. Optout user after n delivery failures
   ([#307](https://github.com/praekeltfoundation/ndoh-hub/pull/307))

## 0.8.3 (2020-03-05)

1. Optout user after n delivery failures
   ([#305](https://github.com/praekeltfoundation/ndoh-hub/pull/305))

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
