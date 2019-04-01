#!/bin/sh

while read -r line; do
    identity=${line%,*}
    channel=${line#*,}
    if [ $channel == $1 ]; then
        echo "$identity"
    fi
done
