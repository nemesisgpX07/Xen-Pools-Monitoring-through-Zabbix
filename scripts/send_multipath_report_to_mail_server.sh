#!/bin/bash
# File: run_multipath_report.sh
# Runs the multipath report for given host IDs, then SCPs the
# latest generated LVMOHBA_Multipath_Report_*.xlsx to remote server.
# Cron example (runs daily at 9:16 AM):
#   33 9,16 * * * /root/scripts/run_multipath_report.sh >> /root/scripts/logs/multipath_cron.log 2>&1

SCRIPT_DIR="/root/scripts"
REMOTE_USER="root"
REMOTE_HOST="198.19.6.34"
REMOTE_PORT="2232"
REMOTE_PATH="/tmp/"
#HOST_IDS="38"
HOST_IDS="1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 55 56"          # space-separated if multiple: "38 39 40"

echo "===== $(date '+%Y-%m-%d %H:%M:%S') ====="

# Run the report (it creates the timestamped xlsx in SCRIPT_DIR)
cd "$SCRIPT_DIR" || { echo "ERROR: cannot cd to $SCRIPT_DIR"; exit 1; }

python3 "$SCRIPT_DIR/lvmohba_multipath_report.py" $HOST_IDS

# Find the most recently created report file
LATEST=$(ls -t "$SCRIPT_DIR"/LVMOHBA_Multipath_Report_*.xlsx 2>/dev/null | head -1)

if [[ -z "$LATEST" ]]; then
    echo "No report file found – nothing to transfer."
    exit 0
fi

echo "Latest report: $LATEST"

# SCP to remote server
scp -P "$REMOTE_PORT" "$LATEST" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}"

if [[ $? -eq 0 ]]; then
    echo "Transfer OK: $LATEST -> ${REMOTE_HOST}:${REMOTE_PATH}"
else
    echo "ERROR: SCP transfer failed for $LATEST"
    exit 1
fi
