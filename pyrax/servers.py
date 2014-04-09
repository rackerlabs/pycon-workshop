#! /usr/bin/env python2.7

from __future__ import print_function

import argparse
import logging
import os
import sys
import time

import pyrax

pyrax.set_setting("identity_type", "rackspace")
pyrax.set_credential_file(os.path.expanduser("~/.pyraxtestcreds"))

# Alias some of the long names.
cs = pyrax.cloudservers
clb = pyrax.cloud_loadbalancers

def _option_chooser(options, attr=None, enumerated=False):
    """Given an iterable, enumerate its contents for a user to choose from.
    If the optional `attr` is not None, that attribute in each iterated
    object will be printed.

    This function will exit the program if the user chooses the escape option.
    """
    if not enumerated:
        options = enumerate(options)

    num = 0
    for num, option in options:
        if attr:
            print("%s: %s" % (num, getattr(option, attr)))
        else:
            print("%s: %s" % (num, option))

    # Add an escape option
    escape_opt = num + 1
    print("%s: I want to exit!" % escape_opt)

    choice = raw_input("Selection: ")
    try:
        ichoice = int(choice)
        if ichoice > escape_opt:
            raise ValueError
    except ValueError:
        print("Valid entries are numbers 0-%s. Received '%s'." % (escape_opt,
              choice))
        sys.exit()

    if ichoice == escape_opt:
        print("Bye!")
        sys.exit()

    return ichoice

def add_keypair(args):
    """Setup a keypair for `args.key`, named `args.name`."""
    with open(args.key, "r") as key:
        cs.keypairs.create(args.name, key.read())

def create_loadbalancer(args):
    """Create a Rackspace Cloud Load Balancer."""
    print(args)

    # Create a node for each server to add to our load balancer.
    nodes = [clb.Node(ip, port=80, condition="ENABLED") for ip in args.servers]

    # Create a VirtualIP for the load balancer.
    vip = clb.VirtualIP(type="PUBLIC")

    lb = clb.create(args.name, port=80, protocol="HTTP", nodes=nodes,
                    virtual_ips=[vip], algorithm="ROUND_ROBIN")
    print(vip)
    print(lb)

def create_server(args):
    """Create a Rackspace Cloud Server."""
    # We need to subscript this, so make it a list.
    all_images = list(enumerate(cs.images.list()))
    server_subset = filter(lambda (n, s): args.distro in s.name, all_images)

    print("* Choose a specific distro...")
    img_id = _option_chooser(server_subset, "name", True)
    image = all_images[img_id][1]

    all_flavors = cs.flavors.list()
    print("* Choose your flavor (RAM)...")
    flavor_id = _option_chooser(all_flavors, "ram")
    flavor = all_flavors[flavor_id]

    all_pairs = cs.keypairs.list()
    print("* Choose the key name to pair with the server...")
    key_id = _option_chooser(all_pairs, "name")
    key = all_pairs[key_id]

    server = cs.servers.create(args.name, image, flavor, key_name=key.name)
    pyrax.utils.wait_for_build(server)
    print("Server built: {}".format(server.name))
    print("Public IP: {}".format(server.networks["public"]))
    print("Private IP: {}".format(server.networks["private"]))

def _main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    add_key = subparsers.add_parser("add-key", help="Add an SSH key pair")
    add_key.add_argument("key")
    add_key.add_argument("name")
    add_key.set_defaults(func=add_keypair)

    create_srv = subparsers.add_parser("create-server",
                                       help="Create a server")
    create_srv.add_argument("--distro", type=str, default="Ubuntu")
    create_srv.add_argument("--name", type=str,
            default="server-{}".format(
                time.strftime("%Y%m%d-%H%M%S", time.localtime())))
    create_srv.set_defaults(func=create_server)

    create_lb = subparsers.add_parser("create-loadbalancer",
                                      help="Create a load balancer")
    create_lb.add_argument("servers", nargs="*")
    create_lb.add_argument("--name", type=str,
            default="lb-{}".format(
                time.strftime("%Y%m%d-%H%M%S", time.localtime())))
    create_lb.set_defaults(func=create_loadbalancer)

    args = parser.parse_args()

    args.func(args)

    return 0


if __name__ == "__main__":
    sys.exit(_main())

