#!/bin/sh
set -e

echo "Stopping local TeamUp stack..."
docker compose down
echo "Done."
