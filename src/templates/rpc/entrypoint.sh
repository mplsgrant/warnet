#!/bin/bash
set -e

SOURCE_DIR="/root/warnet"
MAX_ATTEMPTS=30
SLEEP_DURATION=1

echo "$(ls $SOURCE_DIR)"

# Execute the CMD from the Dockerfile
echo "$@ $($@)"
exec "$@"
