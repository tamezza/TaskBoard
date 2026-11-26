#!/usr/bin/env bash
# Write a compressed backup of the database to backups/.
set -euo pipefail

mkdir -p backups
FILE="backups/taskboard-$(date +%Y%m%d-%H%M%S).dump"

docker compose exec -T db pg_dump -U taskboard -d taskboard --format=custom > "$FILE.partial"
mv "$FILE.partial" "$FILE"

echo "Backup written to $FILE ($(du -h "$FILE" | cut -f1))"