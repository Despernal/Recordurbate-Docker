#!/bin/bash

cd /app

rm configs/rb.*

/usr/local/bin/python3 Recordurbate.py start

status=$?

if [ $status -ne 0 ]; then
  echo "Failed to start chat: $status"
  exit $status
fi

while sleep 60; do
  ps aux |grep Recordurbate.py |grep -q -v grep
  PROCESS_1_STATUS=$?
  if [ $PROCESS_1_STATUS -ne 0 ]; then
    echo "Chat exited"
    exit 1
  fi
done
