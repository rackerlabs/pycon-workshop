#!/usr/bin/env python

import argparse
import os
import sys

import pyrax

pyrax.set_setting("identity_type", "rackspace")
pyrax.set_credential_file(os.path.expanduser("~/.pyraxcreds"))

auto = pyrax.autoscale
clb = pyrax.cloud_loadbalancers
cs = pyrax.cloudservers

def create_scaling_group(args):
    """Create a scaling group."""
    # Get the load balancer we're working with.
    lb = clb.list()[0]

    flavor = cs.flavors.list()

    try:

        # Create a scaling group based on our bikeshed image.
        group = auto.create("bikeshed-asg",
                    cooldown=120, # Wait 120 seconds to process more events
                    min_entities=2, # Start with two servers
                    max_entities=4, # Can go up to four servers
                    launch_config_type="launch_server", # Only option
                    flavor=2, # 512mb server
                    image="907476cd-f838-4b20-98d9-194b215ea505", # bikeshed-img1
                    server_name="bikeshed", # name prefix
                    load_balancers=lb.id, # Start up the servers on my LB
                    scaling_policies=None
                    )
    except pyrax.exceptions.BadRequest as br:
        print br.details
        print br.message

    # Set a policy web hook that Cloud Monitoring can call
    group.add_policy("my-policy",
                     "webhook", # Type of policy
                     60, # Number of seconds to cooldown before processing more
                     1) # Positive change, so we'll scale *up*

def execute_policy(args):
    """Execute a scaling policy."""

    # Get our scaling group.
    group = auto.list()[0]

    # Get our policy.
    policy = group.list_policies()[0]

    # Execute the policy.
    policy.execute()

def _main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    create_group = subparsers.add_parser("create-scaling-group",
                                    help="Create our scaling group")
    create_group.set_defaults(func=create_scaling_group)

    execute = subparsers.add_parser("execute",
                                    help="Execute our scaling policy")
    execute.set_defaults(func=execute_policy)



    args = parser.parse_args()

    args.func(args)

    return 0


if __name__ == "__main__":
    sys.exit(_main())

