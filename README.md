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

3) Puth manage_transmission somewhere on your PATH

4) Configure via ENV vars:

`ARCHIVE_HOME` ==> Archive directory to move / copy torrent data

`MOUNT_COMMAND` ==> Optional command to mount a filesystem before performing any iops

`UNMOUNT_COMMAND` ==> Optional command to unmount a filesystem after performing any iops

`DOWNLOADS_HOME` ==> Where transmission downloads torrents

`TRANSMISSION_UNAME` ==> Username for transmission's RPC interface

`TRANSMISSION_PWD` ==> Password for transmission's RPC interface


### Invocation

`manage_transmission --help`

Terminology:

"Archive" will stop an existing torrent, move its files to the archive directory, then delete the source files

"Sync" will copy a torrent's files to the archive directory, leaving the torrent running

### Notes

Tested on python 2.7.6

Example to use in combination with google-drive-ocamlfuse filesystem:

```
MOUNT_COMMAND = "google-drive-ocamlfuse -verbose /mnt"
UNMOUNT_COMMAND = "fusermount -u /mnt"
```

Example crontab to continuously sync torrents (remember to append your path else manage_torrent wont find the right shell commands'):

`* * * * * PATH=/usr/bin /usr/bin/manage_transmission sync_all`
