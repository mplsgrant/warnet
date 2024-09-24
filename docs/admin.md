# Admin

## Connect to your cluster

Ensure you are connected to your cluster because Warnet will use your current configuration to generate configurations for your users.

```shell
$ warnet status
```

Observe that the output of the command matches your cluster.

**TODO** Add the *current-config* to the *status* report.

## Create an *admin* directory

```shell
$ mkdir admin
$ cd admin
$ warnet admin init
```

Observe that there are now two folders within the *admin* directory: *namespaces* and *networks*

## The *namespaces* directory
This directory contains a Helm chart named *two_namespaces_two_users*.

Modify this chart based on the number of teams and users you have.

Deploy the *two_namespaces_two_users* chart.

```shell
$ cd namespaces
$ warnet deploy two_namespaces_two_users
```

**TODO**: `warnet deploy namespaces/two_namespaces_two_users` fails with an error about directory handling

Observe that this creates service accounts and namespaces in the cluster:

```shell
$ kubectl get ns
$ kubectl get sa -A
```

**TODO**: `warnet admin namespaces list` does not show the teams as yet.

**TODO**: Lift `kubectl get sa -A` into Warnet.

### Creating Warnet invites
A Warnet invite is a Kubernetes config file.

Create invites for each of your users.

```shell
$ warnet admin create-kubeconfigs wargames
```

Take note of the "wargames" prefix we used. That aligns with the "wargames" prefix of the namespaces we created for our users.

Observe the *kubeconfigs* directory. It holds invites for each user.

### Using Warnet invites
Users can connect to your wargame using their invite.

```shell
$ warnet auth alice-wargames-red-team-kubeconfig
```

### Set up a network for your users
Before letting the users into your cluster, make sure to create a network of tanks for them to view.


```shell
$ warnet admin deploy networks/mynet --namepace wargames-red-team
```

**TODO**: What's the logging approach here?

Observe that the *wargames-red-team* namespace now has tanks in it.
