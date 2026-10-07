#!/usr/bin/env bash
# Run the same scanners as the pipeline on this machine and apply the gate.
# Needs: python venv with requirements-dev.txt, gitleaks, trivy, docker.
#   ./security/scan-local.sh [image]      (default image: session17-python:local)
set -uo pipefail
cd "$(dirname "$0")/.."
IMAGE="${1:-session17-python:local}"
mkdir -p reports

echo "== SAST: bandit"
bandit -c security/bandit.yaml -r app -f json -o reports/bandit.json -q; bandit -c security/bandit.yaml -r app -q

echo "== SCA: pip-audit"
pip-audit -r requirements.txt -f json -o reports/pip-audit.json; pip-audit -r requirements.txt

echo "== Secret scan: gitleaks"
gitleaks dir . -c security/gitleaks.toml -f json -r reports/gitleaks.json --no-banner --exit-code 0

echo "== Image scan: trivy $IMAGE"
trivy image -q --scanners vuln --ignorefile security/.trivyignore -f json -o reports/trivy-image.json "$IMAGE"
trivy image -q --scanners vuln --ignorefile security/.trivyignore --severity HIGH,CRITICAL "$IMAGE"

echo "== Security gate"
python security/gate.py reports
