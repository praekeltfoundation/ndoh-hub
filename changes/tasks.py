from celery.task import Task

from ndoh_hub import utils
from registrations.models import Registration, SubscriptionRequest
from .models import Change


class ImplementAction(Task):
    """ Task to apply a Change action.
    """
    name = "ndoh_hub.changes.tasks.implement_action"

    def pmtct_loss_switch(self, change):
        """ The rest of the action required (deactivating momconnect
        subscription, subscribing to loss messages) is currently done on the
        old system via the ndoh-jsbox ussd_pmtct app, we're only deactivating
        her subscriptions here.
        """
        # Get current subscriptions
        subscriptions = utils.get_subscriptions(change.registrant_id)
        # Deactivate subscriptions
        for subscription in subscriptions:
            utils.deactivate_subscription(subscription)

        return "PMTCT switch to loss completed"

    def pmtct_loss_optout(self, change):
        """ The rest of the action required (opting out the identity on the
        identity store, opting out the vumi contact, deactivating the old
        system subscriptions) is currently done on via the ndoh-jsbox
        ussd_pmtct app, we're only deactivating her subscriptions here.
        """
        # Get current subscriptions
        subscriptions = utils.get_subscriptions(change.registrant_id)
        # Deactivate subscriptions
        for subscription in subscriptions:
            utils.deactivate_subscription(subscription)

        return "PMTCT optout due to loss completed"

    def change_language(self, change):
        # Get current subscriptions
        subscriptions = utils.get_subscriptions(change.registrant_id)
        # Patch subscriptions languages
        for subscription in subscriptions:
            utils.patch_subscription(
                subscription, {"lang": change.data["new_language"]})

        return "Change language completed"

    def unsubscribe(self, change):
        # Get current subscriptions
        subscriptions = utils.get_subscriptions(
            change.registrant_id)
        # Deactivate subscriptions
        for subscription in subscriptions:
            utils.deactivate_subscription(subscription)

        return "Unsubscribe completed"

    def run(self, change_id, **kwargs):
        """ Implements the appropriate action
        """
        change = Change.objects.get(id=change_id)

        result = {
            'pmtct_loss_switch': self.pmtct_loss_switch,
            'pmtct_loss_optout': self.pmtct_loss_optout,
            # 'change_language': self.change_language,
            # 'unsubscribe': self.unsubscribe,
        }.get(change.action, None)(change)
        return result

implement_action = ImplementAction()
