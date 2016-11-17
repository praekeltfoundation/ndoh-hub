import datetime
import json
import requests

from celery.task import Task
from celery.utils.log import get_task_logger
from django.conf import settings
from requests.exceptions import HTTPError
from seed_services_client.identity_store import IdentityStoreApiClient
from seed_services_client.stage_based_messaging import StageBasedMessagingApiClient  # noqa
from six import iteritems

from ndoh_hub import utils
from registrations.models import Registration
from .models import Change
from registrations.models import SubscriptionRequest


sbm_client = StageBasedMessagingApiClient(
    api_url=settings.STAGE_BASED_MESSAGING_URL,
    auth_token=settings.STAGE_BASED_MESSAGING_TOKEN
)

is_client = IdentityStoreApiClient(
    api_url=settings.IDENTITY_STORE_URL,
    auth_token=settings.IDENTITY_STORE_TOKEN
)


class ValidateImplement(Task):
    """ Task to apply a Change action.
    """
    name = "ndoh_hub.changes.tasks.validate_implement"
    l = get_task_logger(__name__)

    # Helpers
    def deactivate_all(self, change):
        """ Deactivates all subscriptions for an identity
        """
        self.l.info("Retrieving active subscriptions")
        active_subs = sbm_client.get_subscriptions(
            {'identity': change.registrant_id, 'active': True}
        )["results"]

        self.l.info("Deactivating all active subscriptions")
        for active_sub in active_subs:
            sbm_client.update_subscription(
                active_sub["id"], {"active": False})

        self.l.info("All subscriptions deactivated")
        return True

    def deactivate_all_except_nurseconnect(self, change):
        """ Deactivates all subscriptions for an identity that are not to
        nurseconnect
        """
        self.l.info("Retrieving active subscriptions")
        active_subs = sbm_client.get_subscriptions(
            {'identity': change.registrant_id, 'active': True}
        )["results"]

        self.l.info("Retrieving nurseconnect messageset")
        nc_messageset = sbm_client.get_messagesets(
            {"short_name": "nurseconnect.hw_full.1"})["results"][0]

        self.l.info("Deactivating active non-nurseconnect subscriptions")
        for active_sub in active_subs:
            if nc_messageset["id"] != active_sub["messageset"]:
                sbm_client.update_subscription(
                    active_sub["id"], {"active": False})

        self.l.info("Non-nurseconnect subscriptions deactivated")
        return True

    def deactivate_nurseconnect(self, change):
        """ Deactivates nurseconnect subscription only
        """
        self.l.info("Retrieving nurseconnect messageset")
        nc_messageset = sbm_client.get_messagesets(
            {"short_name": "nurseconnect.hw_full.1"})["results"][0]

        self.l.info("Retrieving active nurseconnect subscriptions")
        active_subs = sbm_client.get_subscriptions(
            {'identity': change.registrant_id, 'active': True,
             'messageset': nc_messageset["id"]}
        )["results"]

        self.l.info("Deactivating active nurseconnect subscriptions")
        for active_sub in active_subs:
            sbm_client.update_subscription(active_sub["id"], {"active": False})

    def deactivate_pmtct(self, change):
        """ Deactivates any pmtct subscriptions
        """
        self.l.info("Retrieving active subscriptions")
        active_subs = sbm_client.get_subscriptions(
            {'identity': change.registrant_id, 'active': True}
        )["results"]

        self.l.info("Deactivating active pmtct subscriptions")
        for active_sub in active_subs:
            messageset = sbm_client.get_messageset(active_sub["messageset"])
            if "pmtct" in messageset["short_name"]:
                self.l.info("Deactivating messageset %s" % messageset["id"])
                sbm_client.update_subscription(
                    active_sub["id"], {"active": False})

    def loss_switch(self, change):
        self.l.info("Retrieving active subscriptions")
        active_subs = sbm_client.get_subscriptions(
            {'identity': change.registrant_id, 'active': True}
        )["results"]

        if (len(active_subs) == 0):
            self.l.info("No active subscriptions - aborting")
            return False

        # TODO: Provide temporary bridging code while both systems are
        # being used. The purpose of this would be to accommodate making
        # changes to ndoh-hub that need to be deployed to production while
        # the old system is still in use in production while the new system
        # is in use in QA.
        # If the active subscriptions do not include a momconnect
        # subscription, it means the old system is still being used.

        else:
            self.deactivate_all_except_nurseconnect(change)

            self.l.info("Determining messageset shortname")
            short_name = utils.get_messageset_short_name(
                "loss_%s" % change.data["reason"], "patient", 0)

            self.l.info("Determining SBM details")
            msgset_id, msgset_schedule, next_sequence_number =\
                utils.get_messageset_schedule_sequence(
                    short_name, 0)

            self.l.info("Determining language")
            identity = is_client.get_identity(change.registrant_id)

            subscription = {
                "identity": change.registrant_id,
                "messageset": msgset_id,
                "next_sequence_number": next_sequence_number,
                "lang": identity["details"]["lang_code"],
                "schedule": msgset_schedule
            }

            self.l.info("Creating Loss SubscriptionRequest")
            SubscriptionRequest.objects.create(**subscription)
            self.l.info("Created Loss SubscriptionRequest")
            return True

    # Action implementation
    def baby_switch(self, change):
        """ This should be applied when a mother has her baby. Currently it
        only changes the pmtct subscription, but in the future it will also
        change her momconnect subscription.
        """
        self.l.info("Starting switch to baby")

        self.l.info("Retrieving active subscriptions")
        active_subs = sbm_client.get_subscriptions(
            {'identity': change.registrant_id, 'active': True}
        )["results"]

        # Determine if the mother has an active pmtct subscription and
        # deactivate active subscriptions
        self.l.info("Evaluating active subscriptions")
        has_active_pmtct_prebirth_sub = False
        has_active_momconnect_prebirth_sub = False

        for active_sub in active_subs:
            self.l.info("Retrieving messageset")
            messageset = sbm_client.get_messageset(active_sub["messageset"])
            if "pmtct_prebirth" in messageset["short_name"]:
                has_active_pmtct_prebirth_sub = True
                lang = active_sub["lang"]
            if "momconnect_prebirth" in messageset["short_name"]:
                has_active_momconnect_prebirth_sub = True
                lang = active_sub["lang"]
            if "prebirth" in messageset["short_name"]:
                self.l.info("Deactivating subscription")
                sbm_client.update_subscription(
                    active_sub["id"], {"active": False})

        if has_active_momconnect_prebirth_sub:
            self.l.info("Starting postbirth momconnect subscriptionrequest")

            self.l.info("Determining messageset shortname")
            # . determine messageset shortname
            short_name = utils.get_messageset_short_name(
                "momconnect_postbirth", "hw_full", 0)

            # . determine sbm details
            self.l.info("Determining SBM details")
            msgset_id, msgset_schedule, next_sequence_number =\
                utils.get_messageset_schedule_sequence(short_name, 0)

            subscription = {
                "identity": change.registrant_id,
                "messageset": msgset_id,
                "next_sequence_number": next_sequence_number,
                "lang": lang,
                "schedule": msgset_schedule
            }
            self.l.info("Creating MomConnect postbirth SubscriptionRequest")
            SubscriptionRequest.objects.create(**subscription)
            self.l.info("Created MomConnect postbirth SubscriptionRequest")

        if has_active_pmtct_prebirth_sub:
            self.l.info("Starting postbirth pmtct subscriptionrequest")

            self.l.info("Determining messageset shortname")
            # . determine messageset shortname
            short_name = utils.get_messageset_short_name(
                "pmtct_postbirth", "patient", 0)

            # . determine sbm details
            self.l.info("Determining SBM details")
            msgset_id, msgset_schedule, next_sequence_number =\
                utils.get_messageset_schedule_sequence(short_name, 0)

            subscription = {
                "identity": change.registrant_id,
                "messageset": msgset_id,
                "next_sequence_number": next_sequence_number,
                "lang": lang,
                "schedule": msgset_schedule
            }
            self.l.info("Creating PMTCT postbirth SubscriptionRequest")
            SubscriptionRequest.objects.create(**subscription)
            self.l.info("Created PMTCT postbirth SubscriptionRequest")

        self.l.info("Saving the date of birth to the identity")
        identity = is_client.get_identity(change.registrant_id)
        details = identity["details"]
        details["last_baby_dob"] = utils.get_today().strftime("%Y-%m-%d")
        is_client.update_identity(
            change.registrant_id, {"details": details})
        self.l.info("Saved the date of birth to the identity")

        return "Switch to baby completed"

    def pmtct_loss_switch(self, change):
        """ Deactivate any active momconnect & pmtct subscriptions, then
        subscribe them to loss messages.
        """
        self.l.info("Starting PMTCT switch to loss")
        switched = self.loss_switch(change)

        if switched is True:
            self.l.info("Completed PMTCT switch to loss")
            return "Completed PMTCT switch to loss"
        else:
            self.l.info("Aborted PMTCT switch to loss")
            return "Aborted PMTCT switch to loss"

    def pmtct_loss_optout(self, change):
        """ This only deactivates non-nurseconnect subscriptions
        """
        self.l.info("Starting PMTCT loss optout")
        self.deactivate_all_except_nurseconnect(change)
        self.l.info("Completed PMTCT loss optout")
        self.l.info("Sending optout to Jembi")
        push_momconnect_optout_to_jembi.delay(str(change.pk))
        return "Completed PMTCT loss optout"

    def pmtct_nonloss_optout(self, change):
        """ Identity optout only happens for SMS optout and is done
        in the JS app. SMS optout deactivates all subscriptions,
        whereas USSD optout deactivates only pmtct subscriptions
        """
        self.l.info("Starting PMTCT non-loss optout")

        if change.data["reason"] == 'unknown':  # SMS optout
            self.deactivate_all(change)
        else:
            self.deactivate_pmtct(change)

        self.l.info("Completed PMTCT non-loss optout")
        self.l.info("Sending optout to Jembi")
        push_momconnect_optout_to_jembi.delay(str(change.pk))
        return "Completed PMTCT non-loss optout"

    def nurse_update_detail(self, change):
        """ This currently does nothing, but in a seperate issue this will
        handle sending the information update to Jembi
        """
        self.l.info("Starting nurseconnect detail update")
        self.l.info("Completed nurseconnect detail update")
        return "Completed nurseconnect detail update"

    def nurse_change_msisdn(self, change):
        """ This currently does nothing, but in a seperate issue this will
        handle sending the information update to Jembi
        """
        self.l.info("Starting nurseconnect msisdn change")
        self.l.info("Completed nurseconnect msisdn change")
        return "NurseConnect msisdn changed"

    def nurse_optout(self, change):
        """ The rest of the action required (opting out the identity on the
        identity store) is currently done via the ndoh-jsbox ussd_nurse
        app, we're only deactivating any NurseConnect subscriptions here.
        """
        self.l.info("Starting NurseConnect optout")
        self.deactivate_nurseconnect(change)
        self.l.info("Pushing optout to Jembi")
        push_nurseconnect_optout_to_jembi.delay(str(change.pk))
        self.l.info("Completed NurseConnect optout")
        return "Completed NurseConnect optout"

    def momconnect_loss_switch(self, change):
        """ Deactivate any active momconnect & pmtct subscriptions, then
        subscribe them to loss messages.
        """
        self.l.info("Starting MomConnect switch to loss")
        switched = self.loss_switch(change)

        if switched is True:
            self.l.info("Completed MomConnect switch to loss")
            return "Completed MomConnect switch to loss"
        else:
            self.l.info("Aborted MomConnect switch to loss")
            return "Aborted MomConnect switch to loss"

    def momconnect_loss_optout(self, change):
        """ This only deactivates non-nurseconnect subscriptions
        """
        self.l.info("Starting MomConnect loss optout")
        self.deactivate_all_except_nurseconnect(change)
        self.l.info("Completed MomConnect loss optout")
        self.l.info("Sending optout to Jembi")
        push_momconnect_optout_to_jembi.delay(str(change.pk))
        return "Completed MomConnect loss optout"

    def momconnect_nonloss_optout(self, change):
        """ Identity optout only happens for SMS optout and is done
        in the JS app. SMS optout deactivates all subscriptions,
        whereas USSD optout deactivates all except nurseconnect
        """
        self.l.info("Starting MomConnect non-loss optout")

        if change.data["reason"] == 'unknown':  # SMS optout
            self.deactivate_all(change)
        else:
            self.deactivate_all_except_nurseconnect(change)

        self.l.info("Completed MomConnect non-loss optout")
        self.l.info("Sending optout to Jembi")
        push_momconnect_optout_to_jembi.delay(str(change.pk))
        return "Completed MomConnect non-loss optout"

    # Validation checks
    def check_pmtct_loss_optout_reason(self, data_fields, change):
        loss_reasons = ["miscarriage", "stillbirth", "babyloss"]
        if "reason" not in data_fields:
            return ["Optout reason is missing"]
        elif change.data["reason"] not in loss_reasons:
            return ["Not a valid loss reason"]
        else:
            return []

    def check_pmtct_nonloss_optout_reason(self, data_fields, change):
        nonloss_reasons = ["not_hiv_pos", "not_useful", "other", "unknown"]
        if "reason" not in data_fields:
            return ["Optout reason is missing"]
        elif change.data["reason"] not in nonloss_reasons:
            return ["Not a valid nonloss reason"]
        else:
            return []

    def check_nurse_update_detail(self, data_fields, change):
        if len(data_fields) == 0:
            return ["No details to update"]

        elif "faccode" in data_fields:
            if len(data_fields) != 1:
                return ["Only one detail update can be submitted per Change"]
            elif not utils.is_valid_faccode(change.data["faccode"]):
                return ["Faccode invalid"]
            else:
                return []

        elif "sanc_no" in data_fields:
            if len(data_fields) != 1:
                return ["Only one detail update can be submitted per Change"]
            elif not utils.is_valid_sanc_no(change.data["sanc_no"]):
                return ["sanc_no invalid"]
            else:
                return []

        elif "persal_no" in data_fields:
            if len(data_fields) != 1:
                return ["Only one detail update can be submitted per Change"]
            elif not utils.is_valid_persal_no(change.data["persal_no"]):
                return ["persal_no invalid"]
            else:
                return []

        elif "id_type" in data_fields and not (
          change.data["id_type"] in ["passport", "sa_id"]):
            return ["ID type should be passport or sa_id"]

        elif "id_type" in data_fields and change.data["id_type"] == "sa_id":
            if len(data_fields) != 3 or set(data_fields) != set(
              ["id_type", "sa_id_no", "dob"]):
                return ["SA ID update requires fields id_type, sa_id_no, dob"]
            elif not utils.is_valid_date(change.data["dob"]):
                return ["Date of birth is invalid"]
            elif not utils.is_valid_sa_id_no(change.data["sa_id_no"]):
                return ["SA ID number is invalid"]
            else:
                return []

        elif "id_type" in data_fields and change.data["id_type"] == "passport":
            if len(data_fields) != 4 or set(data_fields) != set(
              ["id_type", "passport_no", "passport_origin", "dob"]):
                return ["Passport update requires fields id_type, passport_no,"
                        " passport_origin, dob"]
            elif not utils.is_valid_date(change.data["dob"]):
                return ["Date of birth is invalid"]
            elif not utils.is_valid_passport_no(change.data["passport_no"]):
                return ["Passport number is invalid"]
            elif not utils.is_valid_passport_origin(
              change.data["passport_origin"]):
                return ["Passport origin is invalid"]
            else:
                return []

        else:
            return ["Could not parse detail update request"]

    def check_nurse_change_msisdn(self, data_fields, change):
        if len(data_fields) != 3 or set(data_fields) != set(
          ["msisdn_old", "msisdn_new", "msisdn_device"]):
            return ["SA ID update requires fields msisdn_old, msisdn_new, "
                    "msisdn_device"]
        elif not utils.is_valid_msisdn(change.data["msisdn_old"]):
            return ["Invalid old msisdn"]
        elif not utils.is_valid_msisdn(change.data["msisdn_new"]):
            return ["Invalid old msisdn"]
        elif not (change.data["msisdn_device"] == change.data["msisdn_new"] or
                  change.data["msisdn_device"] == change.data["msisdn_old"]):
            return ["Device msisdn should be the same as new or old msisdn"]
        else:
            return []

    def check_nurse_optout(self, data_fields, change):
        valid_reasons = ["job_change", "number_owner_change", "not_useful",
                         "other", "unknown"]
        if "reason" not in data_fields:
            return ["Optout reason is missing"]
        elif change.data["reason"] not in valid_reasons:
            return ["Not a valid optout reason"]
        else:
            return []

    def check_momconnect_loss_optout_reason(self, data_fields, change):
        loss_reasons = ["miscarriage", "stillbirth", "babyloss"]
        if "reason" not in data_fields:
            return ["Optout reason is missing"]
        elif change.data["reason"] not in loss_reasons:
            return ["Not a valid loss reason"]
        else:
            return []

    def check_momconnect_nonloss_optout_reason(self, data_fields, change):
        nonloss_reasons = ["not_useful", "other", "unknown"]
        if "reason" not in data_fields:
            return ["Optout reason is missing"]
        elif change.data["reason"] not in nonloss_reasons:
            return ["Not a valid nonloss reason"]
        else:
            return []

    # Validate
    def validate(self, change):
        """ Validates that all the required info is provided for a
        change.
        """
        self.l.info("Starting change validation")

        validation_errors = []

        # Check if registrant_id is a valid UUID
        if not utils.is_valid_uuid(change.registrant_id):
            validation_errors += ["Invalid UUID registrant_id"]

        # Check that required fields are provided and valid
        data_fields = change.data.keys()

        if 'pmtct_loss' in change.action:
            validation_errors += self.check_pmtct_loss_optout_reason(
                data_fields, change)

        elif change.action == 'pmtct_nonloss_optout':
            validation_errors += self.check_pmtct_nonloss_optout_reason(
                data_fields, change)

        elif change.action == 'nurse_update_detail':
            validation_errors += self.check_nurse_update_detail(
                data_fields, change)

        elif change.action == 'nurse_change_msisdn':
            validation_errors += self.check_nurse_change_msisdn(
                data_fields, change)

        elif change.action == 'nurse_optout':
            validation_errors += self.check_nurse_optout(
                data_fields, change)

        elif 'momconnect_loss' in change.action:
            validation_errors += self.check_momconnect_loss_optout_reason(
                data_fields, change)

        elif change.action == 'momconnect_nonloss_optout':
            validation_errors += self.check_momconnect_nonloss_optout_reason(
                data_fields, change)

        # Evaluate if there were any problems, save and return
        if len(validation_errors) == 0:
            self.l.info("Change validated successfully - updating change "
                        "object")
            change.validated = True
            change.save()
            return True
        else:
            self.l.info("Change validation failed - updating change object")
            change.data["invalid_fields"] = validation_errors
            change.save()
            return False

    # Run
    def run(self, change_id, **kwargs):
        """ Implements the appropriate action
        """
        self.l = self.get_logger(**kwargs)
        self.l.info("Looking up the change")
        change = Change.objects.get(id=change_id)
        change_validates = self.validate(change)

        if change_validates:
            {
                'baby_switch': self.baby_switch,
                'pmtct_loss_switch': self.pmtct_loss_switch,
                'pmtct_loss_optout': self.pmtct_loss_optout,
                'pmtct_nonloss_optout': self.pmtct_nonloss_optout,
                'nurse_update_detail': self.nurse_update_detail,
                'nurse_change_msisdn': self.nurse_change_msisdn,
                'nurse_optout': self.nurse_optout,
                'momconnect_loss_switch': self.momconnect_loss_switch,
                'momconnect_loss_optout': self.momconnect_loss_optout,
                'momconnect_nonloss_optout': self.momconnect_nonloss_optout,
            }.get(change.action, None)(change)
            self.l.info("Task executed successfully")
            return True
        else:
            self.l.info("Task terminated due to validation issues")
            return False

validate_implement = ValidateImplement()


class BasePushOptoutToJembi(object):
    def get_today(self):
        return datetime.datetime.today()

    def get_timestamp(self):
        return self.get_today().strftime("%Y%m%d%H%M%S")

    def get_optout_reason(self, reason):
        """
        Returns the numerical Jembi optout reason for the given optout reason.
        """
        return {
            'miscarriage': 1,
            'stillbirth': 2,
            'babyloss': 3,
            'not_useful': 4,
            'other': 5,
            'unknown': 6,
            'job_change': 7,
            'number_owner_change': 8,
            'not_hiv_pos': 9,
        }.get(reason)

    def run(self, change_id, **kwargs):
        from .models import Change
        change = Change.objects.get(pk=change_id)
        json_doc = self.build_jembi_json(change)
        try:
            result = requests.post(
                self.URL,
                headers={'Content-Type': 'application/json'},
                data=json.dumps(json_doc),
                auth=(settings.JEMBI_USERNAME, settings.JEMBI_PASSWORD),
                verify=False
            )
            result.raise_for_status()
            return result.text
        except (HTTPError,) as e:
            # retry message sending if in 500 range (3 default retries)
            if 500 < e.response.status_code < 599:
                raise self.retry(exc=e)
            else:
                self.l.error('Error when posting to Jembi. Payload: %r' % (
                    json_doc))
                raise e
        except (Exception,) as e:
            self.l.error(
                'Problem posting Optout %s JSON to Jembi' % (
                    change_id), exc_info=True)


class PushMomconnectOptoutToJembi(BasePushOptoutToJembi, Task):
    """
    Sends a momconnect optout change to Jembi.
    """
    name = "ndoh_hub.changes.tasks.push_momconnect_optout_to_jembi"
    l = get_task_logger(__name__)
    URL = "%s/optout" % settings.JEMBI_BASE_URL

    def get_identity_address(self, identity, address_type='msisdn'):
        """
        Returns a single address for the identity for the given address
        type.
        """
        addresses = identity.get(
            'details', {}).get('addresses', {}).get(address_type, {})
        address = None
        for address, details in iteritems(addresses):
            if details.get('default'):
                return address
        return address

    def build_jembi_json(self, change):
        identity = is_client.get_identity(change.registrant_id) or {}
        address = self.get_identity_address(identity)
        return {
            'encdate': self.get_timestamp(),
            'mha': 1,
            'swt': 1,
            'cmsisdn': address,
            'dmsisdn': address,
            'type': 4,
            'optoutreason': self.get_optout_reason(change.data['reason']),
        }

push_momconnect_optout_to_jembi = PushMomconnectOptoutToJembi()


class PushNurseconnectOptoutToJembi(BasePushOptoutToJembi, Task):
    """
    Sends a nurseconnect optout change to Jembi.
    """
    name = "ndoh_hub.changes.tasks.push_nurseconnect_optout_to_jembi"
    l = get_task_logger(__name__)
    URL = "%s/nc/optout" % settings.JEMBI_BASE_URL

    def get_nurse_id(
            self, id_type, id_no=None, passport_origin=None, mom_msisdn=None):
        if id_type == 'sa_id':
            return id_no + "^^^ZAF^NI"
        elif id_type == 'passport':
            return id_no + '^^^' + passport_origin.upper() + '^PPN'
        else:
            return mom_msisdn.replace('+', '') + '^^^ZAF^TEL'

    def get_dob(self, nurse_dob):
        return nurse_dob.strftime("%Y%m%d")

    def get_nurse_registration(self, change):
        """
        A lot of the data that we need to send for the optout is contained
        in the registration, so we need to get the latest registration.
        """
        return Registration.objects\
            .filter(registrant_id=change.registrant_id)\
            .order_by('-created_at')\
            .first()

    def build_jembi_json(self, change):
        registration = self.get_nurse_registration(change)
        if registration is None:
            self.l.error(
                'Cannot find registration for change {}'.format(change.pk))
            return
        return {
            'encdate': self.get_timestamp(),
            'mha': 1,
            'swt': 1,
            'type': 8,
            "cmsisdn": registration.data['msisdn_registrant'],
            "dmsisdn": registration.data['msisdn_device'],
            'rmsisdn': None,
            "faccode": registration.data['faccode'],
            "id": self.get_nurse_id(
                registration.data.get('id_type'),
                (registration.data.get('sa_id_no')
                 if registration.data.get('id_type') == 'sa_id'
                 else registration.data.get('passport_no')),
                # passport_origin may be None if sa_id is used
                registration.data.get('passport_origin'),
                registration.data['msisdn_registrant']),
            "dob": (self.get_dob(
                datetime.strptime(registration.data['mom_dob'], '%Y-%m-%d'))
                    if registration.data.get('mom_db')
                    else None),
            'optoutreason': self.get_optout_reason(change.data['reason']),
        }

push_nurseconnect_optout_to_jembi = PushNurseconnectOptoutToJembi()
