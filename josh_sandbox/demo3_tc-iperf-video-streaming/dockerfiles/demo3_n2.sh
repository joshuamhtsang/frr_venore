#!/bin/bash
set -e
set -o pipefail

while true
do
    if ! socat UDP-LISTEN:3434 UDP:10.0.1.1:3434
    then
        echo "SOCAT failed, retrying..."
        continue
    fi
    sleep 1
done
