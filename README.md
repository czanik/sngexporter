# syslog-ng Prometheus exporter

First of all: What is [Prometheus](https://prometheus.io/)? It is an open source monitoring system, that collects metrics from your hosts and applications, allowing you to visualize and alert on them. The syslog-ng Prometheus exporter allows you to export syslog-ng statistics in a way that Prometheus can collect it.

An implementation in Go has been available for years on GitHub, you can read more about it at https://www.syslog-ng.com/community/b/blog/posts/prometheus-syslog-ng-exporter However, it uses the old syslog-ng statistics interface. While it still works, version 4.1 introduced a new, Prometheus friendly statistics interface. It provides more information than the old stats interface, and in a Prometheus friendly format. Ever since the information available through the new interface is growing.

This project provides you with a new Prometheus exporter for syslog-ng, implemented in Python. It uses the new stats interface, making new fields automatically available when added.

## Requirements

- Python 3.X (tested with Python 3.6 and 3.11) with no external dependencies
- syslog-ng 4.1 or later (tested with 4.7), or syslog-ng PE 7.0.32 or later (tested with 7.0.34)

For Docker testing we used the the official syslog-ng Docker image from https://hub.docker.com/r/balabit/syslog-ng/ Other images might use different path names for the syslog-ng control socket.

From the script's point of view there is no difference between syslog-ng open source and syslog-ng PE, except for the ```syslog-ng.ctl``` (syslog-ng control socket) path.

## How it works?

The syslog-ng Prometheus exporter runs continuously in the the background. It opens the syslog-ng control socket (it's location depends on the operating system used) to collect statistics. It also starts a web server, where it shares the collected statistics. The collected statistics depends on the stats-level() setting of syslog-ng.

When Prometheus contacts the exporter, the exporter collects the latest stats from syslog-ng, by sending a ```STATS PROMETHEUS``` command ( or```STATS PROMETHEUS WITH_LEGACY``` with the TBD parameter)  to the socket. Then it shares the results using the web server. You can get the same results on the command line with ```syslog-ng-ctl```:
```
syslog-ng-ctl stats prometheus
```
or
```
syslog-ng-ctl stats prometheus --with-legacy-metrics
```

## Parameters

- ```--socket-path``` path to the ```syslog-ng.ctl``` socket (by default ```/var/lib/syslog-ng/syslog-ng.ctl```)
- ```--listen-address``` specifies where the exporter listens  (default: all interfaces on port ```9577```)
- ```--stats-with-legacy``` also include legacy statistics
- ```--log-level``` sets the logging level. "info" is the default, "debug" gives more, "error" less messages
- ```--log-target``` sets where logs go. By default to ```stderr```, but you can also set it to ```syslog```

## systemd service file

You can find an example service file for the syslog-ng Prometheus exporter. Note that directory names might be different on your operating system. This was tested on openSUSE, with the sngexporter git repo checked out by root (not a best practice...)

```
[Unit]
Description=Syslog-ng Prometheus Exporter Service
After=syslog-ng.service

[Service]
EnvironmentFile=-/etc/sysconfig/sngexporter
ExecStart=python3 /root/sngexporter/sng_exporter.py $SNGEXPORTER_PARAMS
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```
Save it as ```/usr/lib/systemd/system/sngexporter.service``` (or where your system stores service files).

Normally service files are not edited by hand. They can be configured using parameters, stored in a separate file. On openSUSE these parameter files can be found under the ```/etc/sysconfig``` directory. The above service file expects parameters in ```/etc/sysconfig/sngexporter```. If the default parameters are OK in your environment, you do not have to create it. Otherwise the format should be something similar:
```
SNGEXPORTER_PARAMS="--socket-path=/run/syslog-ng.ctl"
```

Note that the scripts exits if the syslog-ng control socket becomes unavailable (syslog-ng crashes or does not start after a reconfiguration). If you use the above service file, it will try to restart the script five times in 30 seconds intervals before giving up.

## Creating a container image

Use the following simple Dockerfile to build the container, which allows to pass the above parameters to the script if necessary:
```
FROM python:3.11

COPY sng_exporter.py /app/sng_exporter.py
WORKDIR /app
ENTRYPOINT ["python3", "/app/sng_exporter.py"]
```
The following command line builds the container image (I actually used ```podman``` with a docker alias...):
```
docker build -t sngexporter .
```
Which builds the image and names it ```localhost/sngexporter```.

## Use cases

In all cases you have to make sure that the syslog-ng Prometheus exporter has access to the syslog-ng control socket. If the location is different form the default, configure it accordingly using the ```--socket-path``` parameter.

In the Prometheus configuration you should add a similar section:
```
  - job_name: sngpe
    # syslog-ng on Alma Linux.
    static_configs:
      - targets: ['172.16.167.170:9577']
```
Change the various parameters according to your local environment.

### Exporter and syslog-ng installed on host

This is the easiest use case. Configure Prometheus as above, and start ```sng_exporter.py``` with parameters adopted to your environment.

### Exporter in container, syslog-ng on host

Configure Prometheus as above. Find the syslog-ng control socket for the syslog-ng installed on the host. Use the container image from above to run the syslog-ng Prometheus exporter in a container:
```
docker run -it -p 9577:9577 -v /run/syslog-ng.ctl:/run/syslog-ng.ctl localhost/sngexporter --socket-path=/run/syslog-ng.ctl --stats-with-legacy
```
The ```-p 9577:9577``` forwards the network connection to the container. The ```-v /run/syslog-ng.ctl:/run/syslog-ng.ctl``` maps the control socket from the host into the container's filesystem. After the container's name the remaining parameters are passed on the the script, so we configure the location of the control socket, and enable legacy stats in the Prometheus output.

### Exporter  on host, syslog-ng in container

If the exporter is running on the host and syslog-ng in a container, then you have to make the ```syslog-ng.ctl``` socket easily available outside of the container. You can use volume mounts on the ```docker``` or ```podman``` command line. Create a directory on the host, for example ```/mydata/libsng/```, and start the syslog-ng docker image with a similar command line:
```
docker run -it -p 514:514/udp -p 601:601 -v /mydata/libsng:/var/lib/syslog-ng/ --name syslog-ng balabit/syslog-ng:latest -edv
```
This puts the syslog-ng socket and a few more files in the previously created directory, once the image is started:
```
[root@localhost ~]# ls -l /mydata/libsng/
total 20
srwxr-xr-x 1 root root     0 Apr 22 16:05 syslog-ng.ctl
-rw------- 1 root root 16384 Apr 22 16:05 syslog-ng.persist
-rw-r--r-- 1 root root     2 Apr 22 16:05 syslog-ng.pid

```
You can use ```ncat``` to check the socket:
```
[root@localhost ~]# ncat -U /mydata/libsng/syslog-ng.ctl 
STATS PROMETHEUS
syslogng_socket_max_connections{id="s_network#0",driver="afsocket",transport="stream",address="AF_INET(0.0.0.0:514)",direction="input"} 10
syslogng_socket_connections{id="s_network#2",driver="afsocket",transport="stream",address="AF_INET(0.0.0.0:6514)",direction="input"} 0
syslogng_last_config_reload_timestamp_seconds 1713794747
syslogng_last_config_file_modification_timestamp_seconds 1713541883
syslogng_socket_max_connections{id="s_network#2",driver="afsocket",transport="stream",address="AF_INET(0.0.0.0:6514)",direction="input"} 10
syslogng_socket_connections{id="s_network#3",driver="afsocket",transport="stream",address="AF_INET(0.0.0.0:601)",direction="input"} 0
syslogng_scratch_buffers_count 14
syslogng_socket_max_connections{id="s_network#3",driver="afsocket",transport="stream",address="AF_INET(0.0.0.0:601)",direction="input"} 10
syslogng_socket_connections{id="s_network#0",driver="afsocket",transport="stream",address="AF_INET(0.0.0.0:514)",direction="input"} 0
syslogng_input_events_total{id="s_local#0"} 0
syslogng_last_successful_config_reload_timestamp_seconds 1713794747
syslogng_scratch_buffers_bytes 0
.
```
You can start sng_exporter.py with the following commandline:
```
python3 sng_exporter.py --listen-address=":9578" --socket-path=/mydata/libsng/syslog-ng.ctl --log-level=debug
```
Or using the systemd service file, once you edited the parameters.
### Exporter and syslog-ng in containers

You can also run syslog-ng and the syslog-ng Prometheus exporter in containers. For testing I used the official syslog-ng container and the exporter container, as created above. You can use volumes to share a directory between the two containers. The following command creates a volume called ```myvolume```.
```
docker volume create myvolume
```
Next start the syslog-ng container, by making sure that the directory with the syslog-ng control socket is mapped to this volume:
```
docker run -it -p 514:514/udp -p 601:601 -v myvolume:/var/lib/syslog-ng/ --name syslog-ng balabit/syslog-ng:latest -edv
```
Finally also start the exporter container, mapping the volume to a directory where the exporter expects to find the syslog-ng.ctl socket:
```
docker run -it -p 9577:9577 -v myvolume:/run/ localhost/sngexporter --socket-path=/run/syslog-ng.ctl --stats-with-legacy
```
