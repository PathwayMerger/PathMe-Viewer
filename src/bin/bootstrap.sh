#!/bin/bash

# I need a shut_down method, start method

set -x

pid=0

shut_down() {
    echo "shutting down"

    # Kills all python processes
    ps aux |grep python |grep -v grep | awk '{print $2}' | while read line; do kill -HUP "$line"; done
    sleep 10
	ps aux
    exit
}

trap 'shut_down' SIGKILL SIGTERM SIGHUP SIGINT EXIT

python -m pathme_viewer web --host 5000 --port 5000 --template="/opt/pathme_viewer/src/compath/templates" --static="/opt/pathme_viewer/src/compath/static" >> /data/logs/pathme.log 2>&1

# this script must end with a persistent foreground process
# exec a command
# wait forever
while true
do
	tail -f /data/logs/pathme.log & wait ${!}
done