# Running Warnet

Warnet runs a server which can be used to manage multiple networks.
In Kubernetes this runs as a `statefulSet` in the cluster.

If the `$XDG_STATE_HOME` environment variable is set, the server will log to
a file `$XDG_STATE_HOME/warnet/warnet.log`, otherwise it will use `$HOME/.warnet/warnet.log`.

## Kubernetes

// TODO

## Running large networks

When running a large number of containers on a single host machine, the system may run out of various resources.
We recommend setting the following values in /etc/sysctl.conf:

```sh
# Increase ARP cache thresholds to improve network performance under high load
# gc_thresh1 - Adjust to higher threshold to retain more ARP entries and avoid cache overflow
net.ipv4.neigh.default.gc_thresh1 = 80000

# gc_thresh2 - Set the soft threshold for garbage collection to initiate ARP entry clean up
net.ipv4.neigh.default.gc_thresh2 = 90000

# gc_thresh3 - Set the hard threshold beyond which the system will start to drop ARP entries
net.ipv4.neigh.default.gc_thresh3 = 100000

# Increase inotify watchers limit to allow more files to be monitored for changes
# This is beneficial for applications like file sync services, IDEs or web development servers
fs.inotify.max_user_watches = 100000

# Increase the max number of inotify instances to prevent "Too many open files" error
# This is useful for users or processes that need to monitor a large number of file systems or directories simultaneously.
fs.inotify.max_user_instances = 100000

```

Apply the settings by either restarting the host, or without restarting using:

```sh
sudo sysctl -p
```

In addition to these settings, you may need to increase the maximum number of permitted open files in /etc/security/limits.conf.
This change is often not necessary though so we recommend trying your network without it first.

The following command will apply it to a single shell session, and not persist it.
Use as root before launching docker.

```sh
# Increase the number of open files allowed per process to 4096
ulimit -n 4096
```
