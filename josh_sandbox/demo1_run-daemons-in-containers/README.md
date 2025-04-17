# Demo 1: Running OSPF daemon and other foundational daemons in a docker container



# Docker commands to build and run the demo

To build the docker images, run the following docker commands from the repository (frr_venore) root.

~~~
$ docker build -t frr-ubuntu22:latest -f josh_sandbox/demo1_run-daemons-in-containers/dockerfiles/Dockerfile_1_StartDaemons .

$ docker run -d --init --privileged --name frr-ubuntu22 --mount type=bind,source=/lib/modules,target=/lib/modules frr-ubuntu22:latest

$ docker exec -it frr-ubuntu22 bash

$ docker stop frr-ubuntu22 ; docker rm frr-ubuntu22
~~~

---------------------------------------------------

Same docker build command:
~~~
$ docker build -t frr-ubuntu22:latest -f josh_sandbox/demo1_run-daemons-in-containers/dockerfiles/Dockerfile_1_StartDaemons .
~~~

Run a container for router 1 (r1).  Note you MUST run this first before r2, due to the way frr.conf files assume r1 is at 172.17.0.2.
~~~
$ docker run -d --init --privileged --name frr-ubuntu22-demo1-r1 --mount type=bind,source=/lib/modules,target=/lib/modules -v ./josh_sandbox/demo1_run-daemons-in-containers/frrconf_files/r1:/etc/frr frr-ubuntu22:latest
~~~

Run a container for router 2 (r2).  r2 is assumed to have ip address 172.17.0.3.
~~~
$ docker run -d --init --privileged --name frr-ubuntu22-demo1-r2 --mount type=bind,source=/lib/modules,target=/lib/modules -v ./josh_sandbox/demo1_run-daemons-in-containers/frrconf_files/r2:/etc/frr frr-ubuntu22:latest
~~~


OSPF neighbor successfully found!  In r1:
~~~
~/frr$ sudo vtysh

710ee4cf1c89# show ip ospf neighbor

Neighbor ID     Pri State           Up Time         Dead Time Address         Interface                        RXmtL RqstL DBsmL
2.2.2.2           1 2-Way/DROther   15.894s           34.105s 172.17.0.3      eth0:172.17.0.2                      0     0     0


~~~