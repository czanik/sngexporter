# syslog-ng Prometheus exporter

[Prometheus](https://prometheus.io/) is an open-source monitoring system that collects metrics from your hosts and applications, allowing you to visualize and alert on them. The syslog-ng Prometheus exporter allows you to export syslog-ng statistics, so that Prometheus can collect it.

While an implementation in Go has been available for years on GitHub (for more information, see [this blog entry](https://www.syslog-ng.com/community/b/blog/posts/prometheus-syslog-ng-exporter), that solution uses the old syslog-ng statistics interface. And while that Go-based implementation still works, syslog-ng 4.1 introduced a new interface that provides not just more information than the previous statistics interface, but does so in a Prometheus-friendly format. The information available through the new interface has been growing ever since.

The syslog-ng Prometheus exporter is implemented in Python. It also uses the new statistics interface, making new fields automatically available when added.

## Requirements

Before you configure and start using the syslog-ng Prometheus exporter, make sure that the following prerequisites are met:

- Python 3.x (tested with Python 3.6 and 3.11) with no external dependencies.
- syslog-ng OSE 4.1 or later (tested with 4.7), or syslog-ng PE 7.0.34 or later (tested with 7.0.34).

**Note:** while Prometheus formatted statistics works in syslog-ng PE, it is not (yet) an officially supported feature.

For Docker testing, we used the [official syslog-ng Docker image](https://hub.docker.com/r/balabit/syslog-ng/). Other images might use different path names for the syslog-ng control socket.

From the script's point of view, there is no difference between syslog-ng OSE and syslog-ng PE, except for the path of the ```syslog-ng.ctl``` (syslog-ng control socket) file.

## How the syslog-ng Prometheus exporter works

The syslog-ng Prometheus exporter runs continuously in the background. It opens the syslog-ng control socket (its location depending on the operating system used) to collect statistics. It also starts a web server, where it shares the collected statistics. The collected statistics depends on the stats-level() setting of syslog-ng.

When Prometheus contacts the exporter, the exporter collects the latest stats from syslog-ng, by sending a ```STATS PROMETHEUS``` command ( or```STATS PROMETHEUS WITH_LEGACY``` with the --stats-with-legacy parameter) to the socket. Then, it shares the results using the web server. You can get the same results on the command line with ```syslog-ng-ctl```:
```
syslog-ng-ctl stats prometheus
```
Alternatively, if using legacy metrics, run:
```
syslog-ng-ctl stats prometheus --with-legacy-metrics
```

## Parameters

The syslog-ng Prometheus exporter uses the following parameters:

- ```--socket-path```: Specifies the path to the ```syslog-ng.ctl``` socket. The default value is ```/var/lib/syslog-ng/syslog-ng.ctl```.
- ```--listen-address```: Specifies where the exporter listens. By default, it uses all interfaces on port ```9577```.
- ```--stats-with-legacy```: When specified, the exporter also includes legacy statistics.
- ```--log-level```: Sets the logging level. The 3 available values are “info" (the default value providing the default amount of messages), “error” (collecting only errors, resulting in less messages) and "debug" (also collecting debug messages, resulting in the most detailed level of logging).
- ```--log-target```: Sets the location of the collected logs. The default value is ```stderr```, but you can also set it to ```syslog```.

## Example: systemd service file

Use this example as the basis of your service file for the syslog-ng Prometheus exporter.

**Note**: The directory names may be different on your operating system. This service file was tested on openSUSE, with the sngexporter git repo checked out by root (which is not a best practice).

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
Save the contents to ```/usr/lib/systemd/system/sngexporter.service``` (or where your system stores service files).

Normally, service files are not edited by hand. Instead, you can configure them using parameters, stored in a separate file. On openSUSE, you can find these parameter files in the ```/etc/sysconfig``` directory. The above service file example expects parameters in ```/etc/sysconfig/sngexporter```. If the default parameters are correct for your environment, you do not have to create this file. Otherwise, the format must be something similar:
```
SNGEXPORTER_PARAMS="--socket-path=/run/syslog-ng.ctl"
```

**Note**: The scripts exits if the syslog-ng control socket becomes unavailable (for example, because syslog-ng crashes or does not start after a reconfiguration). If you use the above service file, it will try to restart the script five times in 30 second-intervals before stopping.

## Creating a container image

Use the following simple Dockerfile to build the container that will allow to pass the above parameters to the script, if necessary:
```
FROM python:3.11

COPY sng_exporter.py /app/sng_exporter.py
WORKDIR /app
ENTRYPOINT ["python3", "/app/sng_exporter.py"]
```
The following command line builds the container image. Here, ```podman``` is actually used with a docker alias, building the image and naming it ```localhost/sngexporter```:
```
docker build -t sngexporter .
```

## Use cases

This section lists the various use cases of the syslog-ng Prometheus exporter.

**Note**: Regardless of the use case, always make sure that the syslog-ng Prometheus exporter has access to the syslog-ng control socket. If the location is different from the default location, configure it accordingly with the ```--socket-path``` parameter.

In the Prometheus configuration, add a similar section:
```
  - job_name: sngpe
    # syslog-ng on Alma Linux.
    static_configs:
      - targets: ['172.16.167.170:9577']
```
Change the various parameters according to your local environment.

### Exporter and syslog-ng installed on host

This is the simplest use case. If both the exporter and syslog-ng run on the host, configure Prometheus as above, and start ```sng_exporter.py``` with the parameters adopted to your environment.

### Exporter in container, syslog-ng on host

If the exporter runs in a container and syslog-ng runs on the host, then configure Prometheus as above. Find the syslog-ng control socket for the syslog-ng instance installed on the host. Use the container image linked above to run the syslog-ng Prometheus exporter in a container:
```
docker run -it -p 9577:9577 -v /run/syslog-ng.ctl:/run/syslog-ng.ctl localhost/sngexporter --socket-path=/run/syslog-ng.ctl --stats-with-legacy
```
The ```-p 9577:9577``` parameter forwards the network connection to the container. The ```-v /run/syslog-ng.ctl:/run/syslog-ng.ctl``` parameter maps the control socket from the host into the container's filesystem. After the container's name, the remaining parameters are passed on the script, so we configure the location of the control socket, and enable legacy stats in the Prometheus output.

### Exporter on host, syslog-ng in container

If the exporter runs on the host and syslog-ng in a container, then you must make the ```syslog-ng.ctl``` socket easily available outside of the container. You can use volume mounts on the ```docker``` or ```podman``` command line. Create a directory on the host, for example ```/mydata/libsng/```, and start the syslog-ng docker image with a similar command line:
```
docker run -it -p 514:514/udp -p 601:601 -v /mydata/libsng:/var/lib/syslog-ng/ --name syslog-ng balabit/syslog-ng:latest -edv
```
This puts the syslog-ng socket and a few more files in the previously-created directory, once the image is started:
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
Then, you can start sng_exporter.py with the following commandline:
```
python3 sng_exporter.py --listen-address=":9578" --socket-path=/mydata/libsng/syslog-ng.ctl --log-level=debug
```
Alternatively, to start the exporter, use the systemd service file after you edited its parameters.

### Exporter and syslog-ng in separate containers

You can also run the exporter and syslog-ng in separate containers. For testing, use the official syslog-ng container and the exporter container as created above. You can use volumes to share a directory between the two containers. The following command creates a volume called ```myvolume```:
```
docker volume create myvolume
```
Next, start the syslog-ng container, by making sure that the directory with the syslog-ng control socket is mapped to this volume:
```
docker run -it -p 514:514/udp -p 601:601 -v myvolume:/var/lib/syslog-ng/ --name syslog-ng balabit/syslog-ng:latest -edv
```
Finally, also start the exporter container, mapping the volume to a directory where the exporter expects to find the syslog-ng.ctl socket:
```
docker run -it -p 9577:9577 -v myvolume:/run/ localhost/sngexporter --socket-path=/run/syslog-ng.ctl --stats-with-legacy
```
