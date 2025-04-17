# Demo 1: Running OSPF daemon and other foundational daemons in a docker container


## Docker build image command
To build the docker images, run the following docker commands from the repository (frr_venore) root. Both routers r1 and r2 will be based off the same image.
~~~
$ docker build -t frr-ubuntu22:latest -f josh_sandbox/demo1_run-daemons-in-containers/dockerfiles/Dockerfile_1_StartDaemons .
~~~

## Run a container for router 1 (r1)
Things to note:
- Note you MUST run the r1 container before r2, due to the static way I defined the frr.conf file to assume r1 is at 172.17.0.2 (the first address given to a new docker container).
- Note the volume binding argument I used (`-v`)
~~~
$ docker run -d --init --privileged --name frr-ubuntu22-demo1-r1 --mount type=bind,source=/lib/modules,target=/lib/modules -v ./josh_sandbox/demo1_run-daemons-in-containers/frrconf_files/r1:/etc/frr frr-ubuntu22:latest
~~~

## Run a container for router 2 (r2)
Run a container for router 2 (r2). r2 is assumed to have ip address 172.17.0.3.
~~~
$ docker run -d --init --privileged --name frr-ubuntu22-demo1-r2 --mount type=bind,source=/lib/modules,target=/lib/modules -v ./josh_sandbox/demo1_run-daemons-in-containers/frrconf_files/r2:/etc/frr frr-ubuntu22:latest
~~~

## Some manual testing
OSPF neighbor successfully found! In r1:
~~~
~/frr$ sudo vtysh

710ee4cf1c89# show ip ospf neighbor

Neighbor ID     Pri State           Up Time         Dead Time Address         Interface                        RXmtL RqstL DBsmL
2.2.2.2           1 2-Way/DROther   15.894s           34.105s 172.17.0.3      eth0:172.17.0.2                      0     0     0
~~~