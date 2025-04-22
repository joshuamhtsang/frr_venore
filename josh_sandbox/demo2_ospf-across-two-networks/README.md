# Demo 2: OSPF route discovery across two networks


TO DO: PUT DIAGRAM HERE.


## Create new network `net2` (10.0.2.0/24)

Create the new network `10.0.2.0/24` and call it `net2`:
~~~
$ docker network create --driver=bridge --subnet=10.0.2.0/24 net2
~~~

## Connect `r2` to the `net2` network

Connect the container `r2` to this new `net2` network.  This will create another network interface (`eth1`) on `r2` and assign it the IP address `10.0.2.2`:
~~~
$ docker network connect net2 frr-ubuntu22-demo1-r2
~~~

Get a bash terminal into `r2`:
~~~
$ docker exec -it frr-ubuntu22-demo1-r2 bash
~~~

Check that this container has the `eth1` interface connected to the `net2` (`10.0.2.0/24`) network:
~~~
~/frr$ ifconfig
eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet 10.0.1.3  netmask 255.255.255.0  broadcast 10.0.1.255
        ether 32:db:74:76:ba:41  txqueuelen 0  (Ethernet)
        RX packets 576  bytes 65212 (65.2 KB)
        RX errors 0  dropped 0  overruns 0  frame 0
        TX packets 382  bytes 31020 (31.0 KB)
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

eth1: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet 10.0.2.2  netmask 255.255.255.0  broadcast 10.0.2.255
        ether de:5d:fb:87:8e:d6  txqueuelen 0  (Ethernet)
        RX packets 57  bytes 8052 (8.0 KB)
        RX errors 0  dropped 0  overruns 0  frame 0
        TX packets 3  bytes 126 (126.0 B)
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

~~~

## Set up OSPF daemon on r2

Set up the zebra and OSPF daemons on `r2` router `2.2.2.2` by:
1. Enabling ospf on the new `eth1` interface which connects to the new `net2` network (`10.0.2.0/24`)
2. Setting the network address, subnet and OSPF area.

~~~
~/frr$ sudo vtysh

# configure terminal
(config)# interface eth1
(config-if)# ip address 10.0.2.0/24
(config-if)# router ospf vrf default
(config-router)# network 10.0.2.0/24 area 0
(config-router)# exit
(config)# exit

5ca07541895a# show ip ospf route
============ OSPF network routing table ============
N    10.0.1.0/24           [10] area: 0.0.0.0
                           directly attached to eth0
N    10.0.2.0/24           [10] area: 0.0.0.0
                           directly attached to eth1

============ OSPF router routing table =============

============ OSPF external routing table ===========
~~~

## Start container for r3

Note the `r2` OSPF daemon still only sees one neighboring router.  This is because we haven't spun up container `r3` with its own OSPF daemon.
~~~
5ca07541895a# show ip ospf neighbor

Neighbor ID     Pri State           Up Time         Dead Time Address         Interface                        RXmtL RqstL DBsmL
1.1.1.1           1 Full/Backup     1h08m33s          37.165s 10.0.1.2        eth0:10.0.1.3                        0     0     0
~~~

Spin up `r3` on network `net2` and give it the appropriate `frr.conf` which actually gives this router an id of `3.3.3.3`:
~~~
frr_venore$ docker run -d --init --privileged --name frr-ubuntu22-demo1-r3 --network net2 --mount type=bind,source=/lib/modules,target=/lib/modules -v ./josh_sandbox/demo2_ospf-across-two-networks/frrconf_files/r3:/etc/frr frr-ubuntu22:latest
~~~

## Checking OSPF daemon status

Now `r2`'s OSPF daemon can see the OSPF router `3.3.3.3` running on `r3` in the neighbor table:
~~~
5ca07541895a# show ip ospf neighbor

Neighbor ID     Pri State           Up Time         Dead Time Address         Interface                        RXmtL RqstL DBsmL
1.1.1.1           1 Full/Backup     1h13m19s          31.831s 10.0.1.2        eth0:10.0.1.3                        0     0     0
3.3.3.3           1 Full/Backup     3.613s            32.587s 10.0.2.3        eth1:10.0.2.2                        1     0     0

~~~

And critically, on `r1` the router `1.1.1.1` discovers the route to `10.0.2.0/24`, and that it is via `10.0.1.3` i.e. via `r2`.
~~~
eea8ed44d4b7# show ip ospf route
============ OSPF network routing table ============
N    10.0.1.0/24           [10] area: 0.0.0.0
                           directly attached to eth0
N    10.0.2.0/24           [20] area: 0.0.0.0
                           via 10.0.1.3, eth0

============ OSPF router routing table =============

============ OSPF external routing table ===========
~~~
