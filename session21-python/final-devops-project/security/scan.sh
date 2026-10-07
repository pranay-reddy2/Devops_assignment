#!/usr/bin/env bash
# Run every security check the pipeline runs, locally, and apply the gate.
#   security/scan.sh [backend-image] [frontend-image]
set -uo pipefail
cd "$(dirname "$0")/.."
BACKEND_IMAGE="${1:-spendwise-backend:local}"
FRONTEND_IMAGE="${2:-spendwise-frontend:local}"
R=security/reports; mkdir -p $R

echo "== SAST (bandit) on application/backend/app"
bandit -c security/bandit.yaml -r application/backend/app -f json -o $R/bandit.json -q
echo "== SCA python (pip-audit)"
pip-audit -r application/backend/requirements.txt -f json -o $R/pip-audit.json --progress-spinner off
echo "== SCA npm (npm audit, production + dev deps)"
(cd application/frontend && npm audit --json > ../../$R/npm-audit.json 2>/dev/null; true)
echo "== Secret scan (gitleaks)"
gitleaks dir . -c security/gitleaks.toml -f json -r $R/gitleaks.json --no-banner --exit-code 0 2>/dev/null
echo "== Image scan (trivy) $BACKEND_IMAGE / $FRONTEND_IMAGE"
trivy image -q --scanners vuln --ignorefile security/.trivyignore -f json -o $R/trivy-backend.json "$BACKEND_IMAGE"
trivy image -q --scanners vuln --ignorefile security/.trivyignore -f json -o $R/trivy-frontend.json "$FRONTEND_IMAGE"
echo "== Security gate"
python3 security/gate.py $R
