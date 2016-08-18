from celery.task import Task

from ndoh_hub import utils
from .models import Change

from registrations.models import SubscriptionRequest


class ImplementAction(Task):
    """ Task to apply a Change action.
    """
    name = "ndoh_hub.changes.tasks.implement_action"

    def baby_switch(self, change):
        """ This should be applied when a mother has her baby. Currently it
        only changes the pmtct subscription, but in the future it will also
        change her momconnect subscription.
        """
        # Get current subscriptions
        active_subs = utils.get_subscriptions(
            {'id': change.registrant_id, 'active': True}
        )["results"]
        # Determine if the mother has an active pmtct subscription and
        # deactivate active subscriptions
        has_active_pmtct_sub = False

        for active_sub in active_subs:
            # get the messageset and check if it is pmtct
            messageset = utils.get_messageset(active_sub["messageset"])
            if "pmtct" in messageset["short_name"]:
                has_active_pmtct_sub = True
                lang = active_sub["lang"]

            utils.patch_subscription(active_sub["id"], {"active": False})

        if has_active_pmtct_sub:
            # create a postbirth pmtct subscriptionrequest

            # . determine messageset shortname
            short_name = utils.get_messageset_short_name(
                "pmtct_postbirth", "patient", 0)

            # . determine sbm details
            msgset_id, msgset_schedule, next_sequence_number =\
                utils.get_messageset_schedule_sequence(
                    short_name, 0)

            subscription = {
                "identity": change.registrant_id,
                "messageset": msgset_id,
                "next_sequence_number": next_sequence_number,
                "lang": lang,
                "schedule": msgset_schedule
            }
            SubscriptionRequest.objects.create(**subscription)

        # Future: create a postbirth momconnect subscriptionrequest

        return "Switch to baby completed"

    def pmtct_loss_switch(self, change):
        """ The rest of the action required (deactivating momconnect
        subscription, subscribing to loss messages) is currently done on the
        old system via the ndoh-jsbox ussd_pmtct app, we're only deactivating
        the subscriptions here.
        """
        # Get current subscriptions
        active_subs = utils.get_subscriptions(
            {'id': change.registrant_id, 'active': True}
        )["results"]
        # Deactivate subscriptions
        for active_sub in active_subs:
            utils.patch_subscription(active_sub["id"], {"active": False})

        return "PMTCT switch to loss completed"

    def pmtct_loss_optout(self, change):
        """ The rest of the action required (opting out the identity on the
        identity store, opting out the vumi contact, deactivating the old
        system subscriptions) is currently done via the ndoh-jsbox ussd_pmtct
        app, we're only deactivating the subscriptions here.
        """
        # Get current subscriptions
        active_subs = utils.get_subscriptions(
            {'id': change.registrant_id, 'active': True}
        )["results"]
        # Deactivate subscriptions
        for active_sub in active_subs:
            utils.patch_subscription(active_sub["id"], {"active": False})

        return "PMTCT optout due to loss completed"

    def pmtct_nonloss_optout(self, change):
        """ The rest of the action required (opting out the identity on the
        identity store, opting out the vumi contact, deactivating the old
        system subscriptions) is currently done via the ndoh-jsbox ussd_pmtct
        app, we're only deactivating the subscriptions here.
        """
        # Get current subscriptions
        active_subs = utils.get_subscriptions(
            {'id': change.registrant_id, 'active': True}
        )["results"]
        # Deactivate subscriptions
        for active_sub in active_subs:
            utils.patch_subscription(active_sub["id"], {"active": False})

        return "PMTCT optout not due to loss completed"

    def run(self, change_id, **kwargs):
        """ Implements the appropriate action
        """
        change = Change.objects.get(id=change_id)

        result = {
            'baby_switch': self.baby_switch,
            'pmtct_loss_switch': self.pmtct_loss_switch,
            'pmtct_loss_optout': self.pmtct_loss_optout,
            'pmtct_nonloss_optout': self.pmtct_nonloss_optout,
        }.get(change.action, None)(change)
        return result

implement_action = ImplementAction()
