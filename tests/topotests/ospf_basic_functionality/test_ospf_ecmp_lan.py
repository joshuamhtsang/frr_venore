#!/usr/bin/python

#
# Copyright (c) 2020 by VMware, Inc. ("VMware")
# Used Copyright (c) 2018 by Network Device Education Foundation, Inc.
# ("NetDEF") in this file.
#
# Permission to use, copy, modify, and/or distribute this software
# for any purpose with or without fee is hereby granted, provided
# that the above copyright notice and this permission notice appear
# in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND VMWARE DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL VMWARE BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
#


"""OSPF Basic Functionality Automation."""
import os
import sys
import time
import pytest
import json

# Save the Current Working Directory to find configuration files.
CWD = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(CWD, "../"))
sys.path.append(os.path.join(CWD, "../lib/"))

# pylint: disable=C0413
# Import topogen and topotest helpers
from mininet.topo import Topo
from lib.topogen import Topogen, get_topogen

# Import topoJson from lib, to create topology and initial configuration
from lib.common_config import (
    start_topology,
    write_test_header,
    create_interfaces_cfg,
    write_test_footer,
    reset_config_on_routers,
    verify_rib,
    create_static_routes,
    check_address_types,
    step,
    create_route_maps,
    shutdown_bringup_interface,
    stop_router,
    start_router,
    topo_daemons,
)
from lib.bgp import verify_bgp_convergence, create_router_bgp
from lib.topolog import logger
from lib.topojson import build_topo_from_json, build_config_from_json

from lib.ospf import (
    verify_ospf_neighbor,
    config_ospf_interface,
    clear_ospf,
    verify_ospf_rib,
    create_router_ospf,
    verify_ospf_interface,
)
from ipaddress import IPv4Address

# Global variables
topo = None
# Reading the data from JSON File for topology creation

jsonFile = "{}/ospf_ecmp_lan.json".format(CWD)
try:
    with open(jsonFile, "r") as topoJson:
        topo = json.load(topoJson)
except IOError:
    assert False, "Could not read file {}".format(jsonFile)

NETWORK = {
    "ipv4": [
        "11.0.20.1/32",
        "11.0.20.2/32",
        "11.0.20.3/32",
        "11.0.20.4/32",
        "11.0.20.5/32",
    ],
    "ipv6": ["1::1/128", "1::2/128", "1::3/128", "1::4/128", "1::5/128"],
}
MASK = {"ipv4": "32", "ipv6": "128"}
NEXT_HOP = {
    "ipv4": ["10.0.0.1", "10.0.1.1", "10.0.2.1", "10.0.3.1", "10.0.4.1"],
    "ipv6": ["Null0", "Null0", "Null0", "Null0", "Null0"],
}
"""
TOPOOLOGY =
      Please view in a fixed-width font such as Courier.
      Topo : Broadcast Networks
        +---+       +---+          +---+           +---+
        |R0 +       +R1 +          +R2 +           +R3 |
        +-+-+       +-+-+          +-+-+           +-+-+
          |           |              |               |
          |           |              |               |
        --+-----------+--------------+---------------+-----
                         Ethernet Segment

TESTCASES =
1.  Verify OSPF ECMP with max path configured as 8
    (Edge having 1 uplink port as broadcast network,
    connect to 8 TORs - LAN case)

 """


class CreateTopo(Topo):
    """
    Test topology builder.

    * `Topo`: Topology object
    """

    def build(self, *_args, **_opts):
        """Build function."""
        tgen = get_topogen(self)

        # Building topology from json file
        build_topo_from_json(tgen, topo)


def setup_module(mod):
    """
    Sets up the pytest environment

    * `mod`: module name
    """
    global topo
    testsuite_run_time = time.asctime(time.localtime(time.time()))
    logger.info("Testsuite start time: {}".format(testsuite_run_time))
    logger.info("=" * 40)

    logger.info("Running setup_module to create topology")

    # This function initiates the topology build with Topogen...
    tgen = Topogen(CreateTopo, mod.__name__)
    # ... and here it calls Mininet initialization functions.

    # get list of daemons needs to be started for this suite.
    daemons = topo_daemons(tgen, topo)

    # Starting topology, create tmp files which are loaded to routers
    #  to start deamons and then start routers
    start_topology(tgen, daemons)

    # Creating configuration from JSON
    build_config_from_json(tgen, topo)

    # Don't run this test if we have any failure.
    if tgen.routers_have_failure():
        pytest.skip(tgen.errors)
    # Api call verify whether OSPF is converged
    ospf_covergence = verify_ospf_neighbor(tgen, topo, lan=True)
    assert ospf_covergence is True, "setup_module :Failed \n Error:" " {}".format(
        ospf_covergence
    )

    logger.info("Running setup_module() done")


def teardown_module():
    """Teardown the pytest environment"""

    logger.info("Running teardown_module to delete topology")

    tgen = get_topogen()

    try:
        # Stop toplogy and Remove tmp files
        tgen.stop_topology()

    except OSError:
        # OSError exception is raised when mininet tries to stop switch
        # though switch is stopped once but mininet tries to stop same
        # switch again, where it ended up with exception
        pass


def red_static(dut, config=True):
    """Local def for Redstribute static routes inside ospf."""
    global topo
    tgen = get_topogen()
    if config:
        ospf_red = {dut: {"ospf": {"redistribute": [{"redist_type": "static"}]}}}
    else:
        ospf_red = {
            dut: {
                "ospf": {
                    "redistribute": [{"redist_type": "static", "del_action": True}]
                }
            }
        }
    result = create_router_ospf(tgen, topo, ospf_red)
    assert result is True, "Testcase : Failed \n Error: {}".format(result)


def red_connected(dut, config=True):
    """Local def for Redstribute connected routes inside ospf."""
    global topo
    tgen = get_topogen()
    if config:
        ospf_red = {dut: {"ospf": {"redistribute": [{"redist_type": "connected"}]}}}
    else:
        ospf_red = {
            dut: {
                "ospf": {
                    "redistribute": [{"redist_type": "connected", "del_action": True}]
                }
            }
        }
    result = create_router_ospf(tgen, topo, ospf_red)
    assert result is True, "Testcase: Failed \n Error: {}".format(result)


def redistribute(dut, route_type, **kwargs):
    """Local def for redstribution of routes inside ospf."""
    global topo
    tgen = get_topogen()

    ospf_red = {dut: {"ospf": {"redistribute": [{"redist_type": route_type}]}}}
    for k, v in kwargs.items():
        ospf_red[dut]["ospf"]["redistribute"][0][k] = v

    result = create_router_ospf(tgen, topo, ospf_red)
    assert result is True, "Testcase : Failed \n Error: {}".format(result)


# ##################################
# Test cases start here.
# ##################################


def test_ospf_lan_ecmp_tc18_p0(request):
    """
    OSPF ECMP.

    Verify OSPF ECMP with max path configured as 8
    (Edge having 1 uplink port as broadcast network,
    connect to 8 TORs - LAN case)

    """
    tc_name = request.node.name
    write_test_header(tc_name)
    tgen = get_topogen()

    # Don't run this test if we have any failure.
    if tgen.routers_have_failure():
        pytest.skip(tgen.errors)

    global topo
    step("Bring up the base config as per the topology")
    step(". Configure ospf in all the routers on LAN interface.")
    reset_config_on_routers(tgen)
    step("Verify that OSPF is up with 8 neighborship sessions.")

    ospf_covergence = verify_ospf_neighbor(tgen, topo, lan=True)
    assert ospf_covergence is True, "setup_module :Failed \n Error:" " {}".format(
        ospf_covergence
    )

    step(
        "Configure a static route in all the routes and "
        "redistribute static/connected in OSPF."
    )

    for rtr in topo["routers"]:
        input_dict = {
            rtr: {
                "static_routes": [
                    {"network": NETWORK["ipv4"][0], "no_of_ip": 5, "next_hop": "Null0"}
                ]
            }
        }
        result = create_static_routes(tgen, input_dict)
        assert result is True, "Testcase {} : Failed \n Error: {}".format(
            tc_name, result
        )

        dut = rtr
        red_static(dut)

    step(
        "Verify that route in R0 in stalled with 8 hops. "
        "Verify ospf route table and ip route table."
    )

    nh = []
    for rtr in topo["routers"]:
        nh.append(topo["routers"][rtr]["links"]["s1"]["ipv4"].split("/")[0])
    nh.remove(topo["routers"]["r1"]["links"]["s1"]["ipv4"].split("/")[0])
    dut = "r1"
    result = verify_ospf_rib(tgen, dut, input_dict, next_hop=nh)
    assert result is True, "Testcase {} : Failed \n Error: {}".format(tc_name, result)

    protocol = "ospf"
    result = verify_rib(tgen, "ipv4", dut, input_dict, protocol=protocol, next_hop=nh)
    assert result is True, "Testcase {} : Failed \n Error: {}".format(tc_name, result)

    step(" clear ip ospf interface on DUT(r0)")
    clear_ospf(tgen, "r0")

    step(
        "Verify that after clearing the ospf interface all the "
        "neighbours are up and routes are installed with 8 next hop "
        "in ospf and ip route tables on R0"
    )

    dut = "r0"
    ospf_covergence = verify_ospf_neighbor(tgen, topo, dut=dut, lan=True)
    assert ospf_covergence is True, "setup_module :Failed \n Error:" " {}".format(
        ospf_covergence
    )

    step(" clear ip ospf interface on R2")
    clear_ospf(tgen, "r2")

    dut = "r2"
    ospf_covergence = verify_ospf_neighbor(tgen, topo, dut=dut, lan=True)
    assert ospf_covergence is True, "setup_module :Failed \n Error:" " {}".format(
        ospf_covergence
    )

    step("Delete static/connected cmd in ospf in all the routes one by one.")
    for rtr in topo["routers"]:
        input_dict = {
            rtr: {
                "static_routes": [
                    {
                        "network": NETWORK["ipv4"][0],
                        "no_of_ip": 5,
                        "next_hop": "Null0",
                        "delete": True,
                    }
                ]
            }
        }
        result = create_static_routes(tgen, input_dict)
        assert result is True, "Testcase {} : Failed \n Error: {}".format(
            tc_name, result
        )

    step("Verify that all the routes are withdrawn from R0")
    dut = "r1"
    result = verify_ospf_rib(
        tgen, dut, input_dict, next_hop=nh, attempts=5, expected=False
    )
    assert result is not True, "Testcase {} : Failed \n Error: {}".format(
        tc_name, result
    )

    protocol = "ospf"
    result = verify_rib(
        tgen,
        "ipv4",
        dut,
        input_dict,
        protocol=protocol,
        next_hop=nh,
        attempts=5,
        expected=False,
    )
    assert result is not True, "Testcase {} : Failed \n Error: {}".format(
        tc_name, result
    )

    write_test_footer(tc_name)


if __name__ == "__main__":
    args = ["-s"] + sys.argv[1:]
    sys.exit(pytest.main(args))
