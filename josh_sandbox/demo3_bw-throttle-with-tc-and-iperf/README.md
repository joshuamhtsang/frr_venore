
## Throttle bitrate eth0 interface on `r1`

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


