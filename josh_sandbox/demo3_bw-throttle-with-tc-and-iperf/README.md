

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


