#!/usr/bin/env bash
# Prove that a backup restores: load it into a scratch database and count the rows.
set -euo pipefail

FILE="${1:?usage: scripts/restore-test.sh backups/<file>.dump}"
PSQL="docker compose exec -T db psql -U taskboard -v ON_ERROR_STOP=1"

$PSQL -d postgres -c "DROP DATABASE IF EXISTS restore_test"
$PSQL -d postgres -c "CREATE DATABASE restore_test"

docker compose exec -T db pg_restore -U taskboard -d restore_test --no-owner < "$FILE"

for table in users boards board_columns cards; do
  echo "$table: $($PSQL -d restore_test -tAc "SELECT count(*) FROM $table")"
done

$PSQL -d postgres -c "DROP DATABASE restore_test"
echo "Restore test passed for $FILE"