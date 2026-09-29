#!/bin/bash

LOCKFILE="/tmp/host_all.lock"
BATCHLOG="/var/log/host_batch.log"
MAX_PARALLEL=5

exec 200>$LOCKFILE
flock -n 200 || exit 0

echo "=====================================" >> $BATCHLOG
echo "Host batch started at $(date)" >> $BATCHLOG

IDS=(
50
)

run_job() {
    local id=$1

    echo "Running host.py for ID $id at $(date)" >> $BATCHLOG

    timeout 120 /usr/bin/python3 /root/scripts/host.py "$id" \
        >> "/var/log/per${id}.log" 2>&1

    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 124 ]; then
        echo "ID $id TIMED OUT at $(date)" >> $BATCHLOG
    elif [ $EXIT_CODE -ne 0 ]; then
        echo "ID $id FAILED (exit $EXIT_CODE) at $(date)" >> $BATCHLOG
    else
        echo "ID $id completed successfully at $(date)" >> $BATCHLOG
    fi
}

for id in "${IDS[@]}"
do
    run_job "$id" &

    # Limit number of parallel jobs
    while [ $(jobs -r | wc -l) -ge $MAX_PARALLEL ]; do
        sleep 1
    done
done

wait  # Wait for all background jobs to finish

echo "Host batch finished at $(date)" >> $BATCHLOG
echo "=====================================" >> $BATCHLOG

