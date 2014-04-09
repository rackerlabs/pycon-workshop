#!/usr/bin/env python

import argparse
import os
import sys

import pyrax

pyrax.set_setting("identity_type", "rackspace")
pyrax.set_credential_file(os.path.expanduser("~/.pyraxtestcreds"))

cm = pyrax.cloud_monitoring
auto = pyrax.autoscale


def get_entity(ip):
    """Create or get an entity."""
    entities = cm.list_entities()
    matches = [entity for entity in entities if ip in entity.ip_addresses]
    if len(matches) == 1:
        return matches[0]
    else:
        ent = cm.create_entity(label="%s-entity" % ip,
                               ip_addresses={"ip": ip})
        return ent


def create_email_notification(args):
    """Create an email notification."""

    entity = get_entity(args.ip)

    # Create a check on our entity.
    # This will do an HTTP GET request on the API every 60 seconds with
    # a 10 second timeout.
    check = cm.create_check(entity, label="my-check",
                check_type="remote.http",
                details={"url": "http://bikeshed.io/api/v1.0/color",
                         "method": "GET"},
                period=60, timeout=10, # How often to check, and what timeout
                monitoring_zones_poll=["mzdfw"], # Which DCs to check from
                target_alias="ip" # The public IP for our entity
                )

    # Create an email notification.
    email = cm.create_notification("email", label="my-email",
            details={"address": "brian@python.org"})

    # Create a notification plan that will email for all states.
    plan = cm.create_notification_plan("my-plan", ok_state=email,
            warning_state=email, critical_state=email)

    # Create an alarm that will cause a critical state to be reached
    # if our HTTP GET check returns a 500 status code.
    alarm = cm.create_alarm(entity, check, plan,
     "if (metric[\"code\"] == \"500\") { return new AlarmStatus(CRITICAL); }")


def create_webhook_notification(args):
    """Create a webhook notification."""

    # Get the entity that we already created.
    entity = cm.list_entities()[0]

    # Create a check on our entity.
    # This will do an HTTP GET request on the API every 60 seconds with
    # a 10 second timeout.
    check = cm.create_check(entity, label="my-check",
                check_type="remote.http",
                details={"url": "http://bikeshed.io/api/v1.0/color",
                         "method": "GET"},
                period=60, timeout=10, # How often to check, and what timeout
                monitoring_zones_poll=["mzdfw"], # Which DCs to check from
                target_alias="ip" # The public IP for our entity
                )

    # Now we bring up our autoscale scaling group.
    group = auto.list()[0]

    # Get our policy, which has the webhook.
    policy = group.list_policies()[0]

    # Get the hook out of the policy.
    hook = policy.list_webhooks()[0]

    # Create an email notification.
    email = cm.create_notification("email", label="my-email",
            details={"address": "brian@python.org"})

    # Create a web hook notification with the HREF link in the hook.
    webhook = cm.create_notification("webhook", label="my-webhook",
            details={"url": hook.links[0]["href"]})

    # Create another notification plan which will call our hook
    plan = cm.create_notification_plan("my-webhook", ok_state=email,
            warning_state=email, critical_state=webhook)

    # Create an alarm
    alarm = cm.create_alarm(entity, check, plan,
     "if (metric[\"code\"] == \"500\") { return new AlarmStatus(CRITICAL); }")

def _main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip")

    subparsers = parser.add_subparsers()

    email_notify = subparsers.add_parser("email-notify")
    email_notify.set_defaults(func=create_email_notification)

    webhook_notify = subparsers.add_parser("webhook-notify")
    webhook_notify.set_defaults(func=create_webhook_notification)

    args = parser.parse_args()

    args.func(args)

    return 0

if __name__ == "__main__":
    sys.exit(_main())

