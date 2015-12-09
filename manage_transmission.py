#! /usr/bin/python


import os
import signal
import sys
import re
import shutil
import subprocess
import StringIO
import pprint
from functools import wraps
from datetime import datetime

import click

from pid import PidFile, PidFileError

# User-defined constants - change to reflect your system

ARCHIVE_HOME = "~/archive"

MOUNT_COMMAND = None
UNMOUNT_COMMAND = None

DOWNLOADS_HOME = "/home/debian-transmission/downloads/"

TRANSMISSION_UNAME = "transmission"
TRANSMISSION_PWD = "transmission"

# Static constants - DO NOT CHANGE

PROGRAM_NAME = "manage_transmission"

TRANSMISSION_COMMAND = "transmission-remote -n '%s:%s'" % (TRANSMISSION_UNAME, TRANSMISSION_PWD)
TORRENT_INFO = "%s -l"
TORRENT_CTL = "%s -t %s -%s"

TORRENT_RE = re.compile("^\s*(?P<id>\d+)\s+(?P<done>\d+)%\s+(?P<have>\d+\.\d+)\s+MB\s+Done\s+(?P<up>\d+\.\d+)\s+(?P<down>\d+\.\d+)\s+(?P<ratio>\d+\.\d+)\s+(?P<status>\w+)\s+(?P<name>.*)$")


# Helpers

pretty_printer = pprint.PrettyPrinter(indent=4)

def pretty_print(object):
    pretty_printer.pprint(object)

def println(line, newline=True):
    if newline:
        print("%s: %s\n" % (datetime.now().isoformat(), line))
    else:
        print(line)

def print_delimiter():
    print("\n====================\n")

def mount_command():
    if MOUNT_COMMAND is None:
        return
    subprocess.check_call(MOUNT_COMMAND, shell=True)

def unmount_command():
    if UNMOUNT_COMMAND is None:
        return
    subprocess.check_call(UNMOUNT_COMMAND, shell=True)

def with_mountpoint(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        mount_command()
        retval = func(*args, **kwargs)
        unmount_command()
        return retval
    return wrapper

# Main class

class Manager(object):
    should_exit = False

    def exit_next_cycle(self):
        self.should_exit = True

    def get_torrent_data(self):
        torrent_info = subprocess.check_output(TORRENT_INFO % TRANSMISSION_COMMAND, shell=True)
        fo = StringIO.StringIO(torrent_info)
        for row in fo:
            match = TORRENT_RE.match(row)
            if match is None:
                continue
            yield match.groupdict()

    def prepare_torrents(self, getemall=False, archive_ratio=None, torrent_ids=None):
        torrent_list = []
        for torrent_data in self.get_torrent_data():
            if getemall:
                torrent_list.append(torrent_data)
            elif torrent_ids is not None:
                if int(torrent_data['id']) in torrent_ids:
                    torrent_list.append(torrent_data)
            elif archive_ratio is not None:
                if float(torrent_data['ratio']) < archive_ratio:
                    println("Archive %s?  (Seed ratio %s)" % (torrent_data['name'], torrent_data['ratio']))
                    confirm = raw_input('y/n: ')
                    if confirm != "y":
                        continue
                    torrent_list.append(torrent_data)
        return torrent_list

    def confirm_archive(self, torrents_to_archive):
        println("Will archive the following torrents:")
        pretty_print([torrent_info['name'] for torrent_info in torrents_to_archive])
        confirm = raw_input('Continue? y/n: ')
        if confirm != "y":
            return False
        return True

    def stop_and_remove(self, torrent_data):
        subprocess.check_output(TORRENT_CTL % (TRANSMISSION_COMMAND, torrent_data['id'], 'S'), shell=True)
        subprocess.check_output(TORRENT_CTL % (TRANSMISSION_COMMAND, torrent_data['id'], 'r'), shell=True)

    @with_mountpoint
    def archive_torrents(self, torrents_to_archive):
        for i, torrent_data in enumerate(torrents_to_archive):
            if self.should_exit:
                println("Exiting...")
                break

            print_delimiter()
            println("Archiving %s (%d of %d)..." % (torrent_data['name'], i + 1, len(torrents_to_archive)))

            source_dir = os.path.join(DOWNLOADS_HOME, torrent_data['name'])
            if not os.path.isdir(source_dir):
                println("Torrent source dir %s does not exist, skipping." % source_dir)
                continue

            archive_dir = os.path.join(ARCHIVE_HOME, torrent_data['name'])
            if os.path.isdir(archive_dir):
                self.stop_and_remove(torrent_data)
                println("Torrent archive dir %s already exists.  Deleting source files." % archive_dir)
                shutil.rmtree(source_dir)
                continue

            self.stop_and_remove(torrent_data)
            shutil.move(source_dir, archive_dir)

    @with_mountpoint
    def sync_torrents(self, torrents_to_sync):
        for i, torrent_data in enumerate(torrents_to_sync):
            if self.should_exit:
                println("Exiting...")
                break

            print_delimiter()
            println("Syncing %s (%d of %d)..." % (torrent_data['name'], i + 1, len(torrents_to_sync)))

            source_dir = os.path.join(DOWNLOADS_HOME, torrent_data['name'])
            if not os.path.isdir(source_dir):
                println("Torrent source dir %s does not exist, skipping." % source_dir)
                continue

            archive_dir = os.path.join(ARCHIVE_HOME, torrent_data['name'])
            if os.path.isdir(archive_dir):
                println("Torrent archive dir %s already exists. Skipping." % archive_dir)
                continue

            shutil.copytree(source_dir, archive_dir)

    def delete_archived_torrents(self, torrents_to_delete):
        for i, torrent_data in enumerate(torrents_to_delete):
            if self.should_exit:
                println("Exiting...")
                break

            archive_dir = os.path.join(ARCHIVE_HOME, torrent_data['name'])
            if not os.path.isdir(archive_dir):
                println("Torrent archive dir %s does not exist. Skipping." % archive_dir)
                continue

            os.rmdir(archive_dir)

    @with_mountpoint
    def list_torrents(self):
        for torrent_data in self.get_torrent_data():
            torrent_info = [torrent_data['id'], torrent_data['name'], torrent_data['ratio'], torrent_data['done']]
            archive_dir = os.path.join(ARCHIVE_HOME, torrent_data['name'])
            if os.path.isdir(archive_dir):
                torrent_info.append("SYNCED")
            else:
                torrent_info.append("UNSYNCED")
            println(torrent_info, newline=False)


manager = Manager()

# Signal handling

def signal_handler(signal, frame):
    println("\nShutting down after next cycle...")
    manager.exit_next_cycle()

signal.signal(signal.SIGINT, signal_handler)

# CLI

@click.group()
def main():
    pass

@main.command()
def info():
    manager.list_torrents()

@main.command()
def mount():
    mount_command()

@main.command()
def unmount():
    unmount_command()

@main.command()
@click.argument('torrent_ids', nargs=-1, type=click.INT)
def archive_by_id(torrent_ids):
    torrents_to_archive = manager.prepare_torrents(torrent_ids=torrent_ids)
    if not manager.confirm_archive(torrents_to_archive):
        return
    manager.archive_torrents(torrents_to_archive)

@main.command()
@click.argument('archive_ratio', type=click.FLOAT)
def archive_by_ratio(archive_ratio):
    torrents_to_archive = manager.prepare_torrents(archive_ratio=archive_ratio)
    if not manager.confirm_archive(torrents_to_archive):
        return
    manager.archive_torrents(torrents_to_archive)

@main.command()
def archive_all():
    println("Archive all. Are you sure?")
    confirm = raw_input('Y/n: ')
    if confirm != "Y":
        return
    torrents_to_archive = manager.prepare_torrents(getemall=True)
    manager.archive_torrents(torrents_to_archive)

@main.command()
@click.argument('torrent_ids', nargs=-1, type=click.INT)
def sync_by_id(torrent_ids):
    torrents_to_sync = manager.prepare_torrents(torrent_ids=torrent_ids)
    manager.sync_torrents(torrents_to_sync)

@main.command()
def sync_all():
    torrents_to_sync = manager.prepare_torrents(getemall=True)
    manager.sync_torrents(torrents_to_sync)

@main.command()
@click.argument('torrent_id', type=click.INT)
def delete_from_archive(torrent_id):
    torrents_to_delete = manager.prepare_torrents(torrent_ids=[torrent_id])
    manager.delete_archived_torrents(torrents_to_delete)

if __name__ == "__main__":
    try:
        with PidFile(pidname=PROGRAM_NAME):
            main()
    except PidFileError:
        print("%s already running" % PROGRAM_NAME)
