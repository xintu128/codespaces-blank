#!/bin/sh
set -eu
[ "$(uname -r)" = 6.18.63-tyc4a-edp01 ] || exit 0
sleep 20
directory=/var/log/tyc4a-boots/$(cat /proc/sys/kernel/random/boot_id)
mkdir -p "$directory"
umask 077
{
    uname -a
    cat /proc/uptime
    cat /proc/cmdline
    lsmod
    printf '\nInput device descriptors:\n'
    cat /proc/bus/input/devices || true
    for usb in /sys/bus/usb/devices/*; do
        [ -f "$usb/idVendor" ] || continue
        printf '\nUSB device: %s\n' "$usb"
        for property in idVendor idProduct product; do
            [ ! -f "$usb/$property" ] || cat "$usb/$property" || true
        done
    done
    for connector in /sys/class/drm/card*-*; do
        [ -d "$connector" ] || continue
        printf '\nConnector: %s\n' "$connector"
        for property in status enabled modes; do
            if [ -f "$connector/$property" ]; then
                printf '%s: ' "$property"
                cat "$connector/$property" || true
            fi
        done
    done
    for backlight in /sys/class/backlight/*; do
        [ -d "$backlight" ] || continue
        printf '\nBacklight: %s\n' "$backlight"
        for property in brightness actual_brightness max_brightness bl_power; do
            if [ -f "$backlight/$property" ]; then
                printf '%s: ' "$property"
                cat "$backlight/$property" || true
            fi
        done
    done
    for state in /sys/kernel/debug/dri/*/state; do
        [ -f "$state" ] || continue
        printf '\nDRM state: %s\n' "$state"
        cat "$state" || true
    done
} > "$directory/display-after-20s.txt" 2>&1
dmesg > "$directory/dmesg-after-20s.txt" 2>&1 || true
sync
