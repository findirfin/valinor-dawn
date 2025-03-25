#!/bin/bash

# Watchdog script to ensure main.py is running

PROCESS_NAME="main.py"

if pgrep -f $PROCESS_NAME > /dev/null
then
    echo "$PROCESS_NAME is running."
else
    echo "$PROCESS_NAME is not running. Starting it now..."
    python3 /path/to/valinor_dawn/scripts/main.py &
fi