# manage_transmission

A program to sync torrent folders downloaded via transmission to another directory,
possibly a filesystem on NFS or another FUSE mountpoint

This script can be called frequently via a crontab as well as from the command-line,
as concurrent invocation is denied by a pidfile lock

### Requirements

1) Set up transmission.

`(sudo) apt-get install transmission`

Configure the following parameters in settings.json

```
"rpc-authentication-required": true,
"rpc-bind-address": "0.0.0.0",
"rpc-enabled": true
```

2) Install python dependencies

`(sudo) pip install -r requirements.txt`

### Notes

Tested on python 2.7.6

Example to use in combination with google-drive-ocamlfuse filesystem:

```
MOUNT_COMMAND = "google-drive-ocamlfuse -verbose /mnt"
UNMOUNT_COMMAND = "fusermount -u /mnt"
```
