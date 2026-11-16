#!/bin/sh
# Capture evidence on the SD rootfs even when HDMI and networking are unavailable.
set -eu
boot_id=$(cat /proc/sys/kernel/random/boot_id)
directory=/var/log/tyc4a-boots/$boot_id
mkdir -p "$directory"
umask 077
{
    printf 'TYC4A Debian userspace reached\n'
    printf 'boot_id=%s\n' "$boot_id"
    uname -a
    cat /proc/uptime
    cat /proc/cmdline
    cat /proc/mounts
} > "$directory/userspace-reached.txt"
dmesg > "$directory/dmesg.txt" 2>&1 || true
if [ -d /sys/class/leds/work ]; then
    cat /sys/class/leds/work/trigger > "$directory/led-trigger.txt" 2>&1 || true
fi
ln -sfn "$boot_id" /var/log/tyc4a-boots/latest
sync
