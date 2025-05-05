# Demo 3: Traffic Control, iPerf and Video Streaming


## Network Schematic of Demo 3

<Put schematic here>


## Create network (`net1`) using docker command

If `net1` does not already exist (it was create in demo1), then create it with command:

~~~
$ docker network create --driver=bridge --subnet=10.0.1.0/24 net1
~~~

And check that it exists with:
~~~
$ ifconfig

br-abaa46ceff04: flags=4099<UP,BROADCAST,MULTICAST>  mtu 1500
        inet 10.0.1.1  netmask 255.255.255.0  broadcast 10.0.1.255
        ether 32:a4:44:59:76:ce  txqueuelen 0  (Ethernet)
<...TRUNCATED...>
~~~

## Build docker image for video streaming nodes
Build the docker images by running the following docker command from the root directory of the repository (`frr_venore/`).  Both `n1` and `n2` will be based off the same image.
~~~
$ docker build -t frr_venore:demo3_node -f josh_sandbox/demo3_tc-iperf-video-streaming/dockerfiles/Dockerfile_demo3_VideoStreaming .
~~~


## Run container for node n1

Ensure port binding `3434:3434` is done.
~~~
$ docker run -d --init --privileged --name frr_venore-demo3-n1 --network net1 -p 3434:3434 frr_venore:demo3_node
~~~


## Testing throughput with iperf

Run iperf server on `r2`
~~~
$ iperf -s
~~~

Run iperf client on `r1`
~~~
$ iperf -c 10.0.1.3
~~~


## Streaming video with ffmpeg and vlc

~~~
$ ffmpeg -re -stream_loop -1 -i motorway_lowres.mp4 -vcodec copy -acodec copy -f mpegts "udp://10.0.1.2:3434/live/stream"
~~~


## Forwarding video to host to play streamed video with VLC

~~~
$ socat socat UDP-LISTEN:3434 UDP:10.0.1.1:3434
~~~


On the host machine, open the stream with VLC at network address:
~~~
udp://@10.0.1.1:3434/live/stream
~~~


Restore normal queue discpline:
~~~
$ sudo tc qdisc replace dev eth0 root pfifo
~~~

## Throttle bitrate throughput of eth0 interface on `r1`

Token Bucket Filter exmaple:
~~~
$ sudo tc qdisc add dev eth0 root tbf rate 1mbit burst 32kbit latency 5ms
~~~

NetEm example:
~~~
sudo tc qdisc change dev eth0 root netem delay 10ms 5ms 1%
~~~

## Using tc NetEm and tbf

https://www.cs.unm.edu/~crandall/netsfall13/TCtutorial.pdf


