#!/usr/bin/env bash
# Generates realistic API traffic through the Ingress (reads + a few writes).
#   URL=http://spendwise.local ./load-test.sh 300
set -euo pipefail
URL="${URL:-http://spendwise.local}"; N="${1:-200}"; HOST_HEADER="${HOST_HEADER:-}"
cats=(FOOD TRANSPORT BILLS SHOPPING HEALTH ENTERTAINMENT EDUCATION OTHER)
h=(); [ -n "$HOST_HEADER" ] && h=(-H "Host: $HOST_HEADER")
for i in $(seq 1 "$N"); do
  curl -s -o /dev/null "${h[@]}" "$URL/api/expenses"
  curl -s -o /dev/null "${h[@]}" "$URL/api/expenses/summary"
  if (( i % 10 == 0 )); then
    c=${cats[$((RANDOM % ${#cats[@]}))]}
    curl -s -o /dev/null "${h[@]}" -X POST "$URL/api/expenses" -H 'Content-Type: application/json' \
      -d "{\"title\":\"load-test $i\",\"amount\":\"$((RANDOM % 2000 + 50))\",\"category\":\"$c\"}"
  fi
  curl -s -o /dev/null "${h[@]}" "$URL/api/expenses/999999"   # a 404 now and then
done
echo "sent $((N * 3 + N / 10)) requests to $URL"
