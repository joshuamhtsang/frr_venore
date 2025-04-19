# Demo 1: Running OSPF daemon and other foundational daemons in a docker container

The key to this demo is the script `docker-start-1-StartDaemons` [here](./dockerfiles/docker-start-1-StartDaemons) which runs the frr daemons in the background.  Note there is an (rather unsafe) way to run the daemons using systemd by using the `cap_add=net_raw` etc. options when running a container, but this approach is not used.


## Docker build image command
To build the docker images, run the following docker commands from the repository (frr_venore) root. Both routers r1 and r2 will be based off the same image.
~~~
$ docker build -t frr-ubuntu22:latest -f josh_sandbox/demo1_run-daemons-in-containers/dockerfiles/Dockerfile_1_StartDaemons .
~~~

## Create a another network using docker

To make the demo more reproducible, it's good pratise to create another network, in this case a `10.0.1.0/24` one.  In effect, this creates a Linux bridge with the assigned network specification.

Create the network with this docker command:
~~~
docker network create --driver=bridge --subnet=10.0.1.0/24 net1
~~~

Containers created on this network (with the `--network net1` flag during `docker run`) will be assigned ascending IP addressed from `10.0.1.2` and upwards on the `eth0` interface. For this demo, the OSPF daemons on r1 and r2 will be assigned to work these `eth0` interfaces.


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

## Some manual testing
OSPF neighbor successfully found! In r1:
~~~
~/frr$ sudo vtysh

710ee4cf1c89# show ip ospf neighbor

Neighbor ID     Pri State           Up Time         Dead Time Address         Interface                        RXmtL RqstL DBsmL
2.2.2.2           1 2-Way/DROther   15.894s           34.105s 10.0.1.3      eth0:10.0.1.2                      0     0     0
~~~