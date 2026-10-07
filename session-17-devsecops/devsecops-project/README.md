# Session 17 – DevSecOps Project

Hardened version of the instructor's [demo/](../demo/) with a full CI/CD + DevSecOps pipeline.
Full write-up, results and screenshots: **[../README.md](../README.md)**.

```bash
# run locally
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
pytest -q
docker build -t session17-python:local .
./security/scan-local.sh session17-python:local     # bandit, pip-audit, gitleaks, trivy + gate
```

| Path | Purpose |
| :--- | :--- |
| `app/`, `tests/` | Flask app + pytest suite |
| `Dockerfile` | alpine, non-root, gunicorn |
| `security/gate.py` | the security gate policy used by CI and locally |
| `security/bandit.yaml`, `gitleaks.toml`, `.trivyignore` | scanner configuration |
| `k8s/` | restricted namespace, hardened Deployment, Service |
| `/.github/workflows/session17-devsecops.yml` | the pipeline (repo root) |
