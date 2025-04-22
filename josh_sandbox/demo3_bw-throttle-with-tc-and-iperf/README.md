
## Throttle bitrate throughput of eth0 interface on `r1`

~~~
$ sudo tc qdisc add dev eth0 root tbf rate 1mbit burst 32kbit latency 5ms
~~~

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
$ ffmpeg -re -i gabbie.mp4 -vcodec copy -acodec copy -f mpegts "udp://127.0.0.1:5000/live/stream"
~~~

In VLC, open the stream at network address:
~~~
udp://@127.0.0.1:5000/live/stream
~~~

