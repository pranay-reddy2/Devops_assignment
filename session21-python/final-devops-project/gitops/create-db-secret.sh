#!/usr/bin/env bash
# One-time, out-of-band creation of the database Secret (GitOps keeps secrets out of Git).
# In a real cluster use External Secrets / Sealed Secrets / AWS Secrets Manager instead.
#   DB_PASSWORD=... ./create-db-secret.sh
set -euo pipefail
: "${DB_PASSWORD:?set DB_PASSWORD}"
kubectl -n spendwise create secret generic spendwise-db \
  --from-literal=password="$DB_PASSWORD" \
  --from-literal=database-url="postgresql+psycopg://spendwise:${DB_PASSWORD}@spendwise-spendwise-postgres:5432/spendwise" \
  --dry-run=client -o yaml | kubectl apply -f -
