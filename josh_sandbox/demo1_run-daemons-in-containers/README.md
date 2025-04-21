# Demo 1: Running OSPF daemon and other foundational daemons in a docker container

The key to this demo is the script `docker-start-1-StartDaemons` [here](./dockerfiles/docker-start-1-StartDaemons) which runs the frr daemons in the background.  Note there is an (rather unsafe) way to run the daemons using systemd by using the `cap_add=net_raw` etc. options when running a container, but this approach is not used.

## Network topology of demo 1

A new network `net1` will be created with 2 docker containers (`r1` and `r2`) attached to this network each running the frr OSPF daemon.  The daemons will each target the eth0 interface and the `10.0.1.0/24` network.

~~~
┌─────────────┐     ┌─────────────┐              ┌────────────────────┐
│     Host    │     │             │              │──────────┐         │
│             │     │             │    veth1     │   eth0   │   r1    │
│┌────────────│     │             ┼──────────────┼(10.0.1.2)│         │
││  [Gateway] │     │    net1     │              │──────────┘         │
││   br-if1  ─│─────┼(10.0.1.0/24)│              └────────────────────┘
││ (10.0.1.1) │     │             │              ┌────────────────────┐
│└────────────│     │             │              │──────────┐         │
└─────────────┘     │             │    veth2     │   eth0   │   r2    │
                    │             ┼──────────────┼(10.0.1.3)│         │
                    └─────────────┘              │──────────┘         │
                                                 └────────────────────┘
~~~

The expectation is that the OSPF daemons to see neighbouring OSPF routers, and these will be evident in the OSPF neighbor, link state database and routing tables.

## Docker build image command
To build the docker images, run the following docker commands from the repository (frr_venore) root. Both routers r1 and r2 will be based off the same image.
~~~
$ docker build -t frr-ubuntu22:latest -f josh_sandbox/demo1_run-daemons-in-containers/dockerfiles/Dockerfile_1_StartDaemons .
~~~

## Create a new network using docker

To make the demo more reproducible, it's good practice to create another network, in this case a `10.0.1.0/24` one.  In effect, this creates a Linux bridge with the assigned network specification.

Create the network (called `net1`) with this docker command:
~~~
docker network create --driver=bridge --subnet=10.0.1.0/24 net1
~~~

Containers created on this network (with the `--network net1` flag during `docker run`) will be assigned ascending IP addressed from `10.0.1.2` and upwards on the `eth0` interface. For this demo, the OSPF daemons on r1 and r2 will be assigned to work these `eth0` interfaces.  The `10.0.1.1` address will actually be the gateway (which you can verify with `docker network inspect net1`).  You can even see this network with `ifconfig`:

~~~
$ ifconfig
br-c4c5fe0bfed2: flags=4099<UP,BROADCAST,MULTICAST>  mtu 1500
        inet 10.0.1.1  netmask 255.255.255.0  broadcast 10.0.1.255
        ether ae:4c:8f:27:c8:c5  txqueuelen 0  (Ethernet)
        RX packets 0  bytes 0 (0.0 B)
        RX errors 0  dropped 0  overruns 0  frame 0
        TX packets 0  bytes 0 (0.0 B)
        TX errors 0  dropped 13 overruns 0  carrier 0  collisions 0
~~~


## Run a container for router 1 (r1)
Things to note:
- This container for r1 MUST be run before r2, so it gets the `10.0.1.2` IP address.
- Note the `--network net1` flag to ensure this joins the `10.0.1.0/24` network created above.
- Note the volume binding argument (`-v`) I used to put the necessary `frr.conf` file into the location expected by the frr daemons.
~~~
$ docker run -d --init --privileged --name frr-ubuntu22-demo1-r1 --network net1 --mount type=bind,source=/lib/modules,target=/lib/modules -v ./josh_sandbox/demo1_run-daemons-in-containers/frrconf_files/r1:/etc/frr frr-ubuntu22:latest
~~~

## Run a container for router 2 (r2)
Run a container for router 2 (r2).
~~~
$ docker run -d --init --privileged --name frr-ubuntu22-demo1-r2 --network net1 --mount type=bind,source=/lib/modules,target=/lib/modules -v ./josh_sandbox/demo1_run-daemons-in-containers/frrconf_files/r2:/etc/frr frr-ubuntu22:latest
~~~

## Checking OSPF is working

1. SHow various OSPF-related tables. In r1:
~~~
$ docker exec -it frr-ubuntu22-demo1-r1 bash
~~~
Use `vtysh` to see the `Neighbor Table`:
~~~
~/frr$ sudo vtysh

eea8ed44d4b7# show ip ospf neighbor

Neighbor ID     Pri State           Up Time         Dead Time Address         Interface                        RXmtL RqstL DBsmL
2.2.2.2           1 Full/DR         49.703s           30.307s 10.0.1.3        eth0:10.0.1.2                        0     0     0
~~~
The `Link State Table` 
~~~
eea8ed44d4b7# show ip ospf database

       OSPF Router with ID (1.1.1.1)

                Router Link States (Area 0.0.0.0)

Link ID         ADV Router      Age  Seq#       CkSum  Link count
1.1.1.1        1.1.1.1          415 0x80000004 0x2301 1
2.2.2.2        2.2.2.2          416 0x80000003 0xe635 1

                Net Link States (Area 0.0.0.0)

Link ID         ADV Router      Age  Seq#       CkSum
10.0.1.3       2.2.2.2          416 0x80000001 0x2018
~~~
And the `Routing Table` (RIB):
~~~
eea8ed44d4b7# show ip ospf route 
============ OSPF network routing table ============
N    10.0.1.0/24           [10] area: 0.0.0.0
                           directly attached to eth0

============ OSPF router routing table =============

============ OSPF external routing table ===========


~~~