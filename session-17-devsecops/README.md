# Session 17: Complete CI/CD & DevSecOps

**Author:** Pranay Reddy
**Course:** SST DevOps & Cloud [SWE]
**Session:** 17, Task: DevSecOps Demo Project
**Environment:** macOS (arm64), Docker Desktop 29.7, minikube v1.39.0 / Kubernetes v1.37.0, Bandit 1.9.4, pip-audit 2.9.0, gitleaks 8.30.1, Trivy 0.75 (local) / 0.70 (pipeline), act 0.2.89

Every output block is real output; screenshots in [screenshots/](screenshots/) are rendered from the same captured output.

| Deliverable | Where |
| :--- | :--- |
| Application | [devsecops-project/app/](devsecops-project/app/) (the instructor's Flask "DevSecOps Dashboard", hardened) + [tests/](devsecops-project/tests/) |
| Dockerfile | [devsecops-project/Dockerfile](devsecops-project/Dockerfile) |
| GitHub Actions workflow | [/.github/workflows/session17-devsecops.yml](../.github/workflows/session17-devsecops.yml) |
| Security tools configuration | [security/bandit.yaml](devsecops-project/security/bandit.yaml), [security/gitleaks.toml](devsecops-project/security/gitleaks.toml), [security/.trivyignore](devsecops-project/security/.trivyignore), gate policy [security/gate.py](devsecops-project/security/gate.py), local runner [security/scan-local.sh](devsecops-project/security/scan-local.sh) |
| Kubernetes manifests | [devsecops-project/k8s/](devsecops-project/k8s/) (namespace with Pod Security `restricted`, hardened Deployment, Service) |
| Successful pipeline output + screenshots | [Pipeline execution](#pipeline-execution) |

---

## Pipeline

```text
Code ─► 1 Build ─► 2 Unit Test ─┬─► 3 SAST (Bandit)  [+ 3b CodeQL on GitHub] ─┐
                                ├─► 4 SCA (pip-audit) ─────────────────────────┤
                                └─► 5 Secret Scan (gitleaks) ──────────────────┤
                                                                               ▼
                                   6 Docker Build ─► 7 Container Image Scan (Trivy)
                                                                               │
              reports: bandit.json, pip-audit.json, gitleaks.json, trivy-image.json
                                                                               ▼
                                                                    8 SECURITY GATE (gate.py)
                                                                      PASS │        │ FAIL → stop
                                                                           ▼
                                      9 Push Image (GHCR) ─► 10 Deploy to Kubernetes (kind)
                                      (push to main only)
```

The three scans run in parallel after the tests (same order as the required flow, just faster). Docker Build only starts after all three, so nothing is built from code that has not been scanned.

| Stage | Tool | What it looks at | Blocks when |
| :--- | :--- | :--- | :--- |
| Build | python | the app compiles and imports | error |
| Unit Test | pytest + coverage | behaviour | any failed test |
| SAST | Bandit (+ CodeQL on GitHub) | **our source code**: insecure calls, debug mode, injection | HIGH severity or the scanner crashed |
| SCA | pip-audit (PyPI/OSV advisories) | **our dependencies** (`requirements.txt`) | known CVE that has a fixed version |
| Secret scanning | gitleaks | hard-coded keys/tokens/passwords | any finding |
| Container image scanning | Trivy | **the built image**: OS packages + installed Python packages | CRITICAL/HIGH with a fixed version |
| Security gate | `security/gate.py` | all four reports | any of the above; also a missing report |
| Container registry | GHCR (`docker/login-action` with `GITHUB_TOKEN`) | push `:<sha>` and `:latest` | only after the gate |
| Kubernetes deployment | kind on the runner | `restricted` Pod Security namespace, rollout, smoke test | rollout/curl failure |

**Why a separate gate job?** Each scanner has its own exit-code rules. Here the scan jobs only write JSON reports (`|| true`, `--exit-code 0`) and one script owns the policy (what blocks, what only warns), the same locally and in CI. The gate also writes its table to the GitHub job summary.

---

## What I changed from the instructor's demo (and why)

| Instructor `demo/` | My `devsecops-project/` | Reason |
| :--- | :--- | :--- |
| `app.run(host="0.0.0.0", debug=True)` | gunicorn in the container; dev server only on 127.0.0.1 with `FLASK_DEBUG=1` | Bandit **B201 HIGH**: Werkzeug debugger = remote code execution |
| `python:3.12-slim`, runs as **root** | `python:3.12-alpine`, `apk upgrade`, user 10001 | slim had **44 unfixed HIGH** OS CVEs, alpine **0**; image 46 MB → 24 MB |
| empty `.dockerignore` | excludes `.venv`, `.git`, tests, reports, … | smaller context, no local secrets/venv in the image |
| Trivy without `--exit-code` (never fails) | gate blocks fixable CRITICAL/HIGH | a scan that cannot fail is not a gate |
| no secret scanning | gitleaks (checksum-verified download) | required by the task |
| push to Docker Hub with a personal token | GHCR with the built-in `GITHUB_TOKEN`, `packages: write` only on that job | no long-lived secret to manage |
| rebuilds the image in 3 jobs | built once, passed as an artifact, scanned image = pushed image = deployed image | you deploy exactly what you scanned |
| plain Deployment, `imagePullPolicy: Always` | `runAsNonRoot`, `readOnlyRootFilesystem`, drop ALL caps, seccomp, no SA token, probes, limits | passes Pod Security `restricted` |
| `random` calls flagged B311 | `# nosec B311` with a justification comment | not security-relevant (greetings, simulation) |

---

## Hands-on results

### 1. SAST on the instructor's demo

```text
# SAST on the instructor's demo/ app as given
$ bandit --version | head -1
bandit 1.9.4
$ bandit -r demo/app
[main]	INFO	profile include tests: None
[main]	INFO	profile exclude tests: None
[main]	INFO	cli include tests: None
[main]	INFO	cli exclude tests: None
[main]	INFO	running on Python 3.14.7
Run started:2026-10-07 16:19:34.034899+00:00

Test results:
>> Issue: [B311:blacklist] Standard pseudo-random generators are not suitable for security/cryptographic purposes.
   Severity: Low   Confidence: High
   CWE: CWE-330 (https://cwe.mitre.org/data/definitions/330.html)
   More Info: https://bandit.readthedocs.io/en/1.9.4/blacklists/blacklist_calls.html#b311-random
   Location: demo/app/app.py:79:19
78	    return jsonify({
79	        "message": random.choice(greetings),
80	        "name": name,

--------------------------------------------------
>> Issue: [B311:blacklist] Standard pseudo-random generators are not suitable for security/cryptographic purposes.
   Severity: Low   Confidence: High
   CWE: CWE-330 (https://cwe.mitre.org/data/definitions/330.html)
   More Info: https://bandit.readthedocs.io/en/1.9.4/blacklists/blacklist_calls.html#b311-random
   Location: demo/app/app.py:190:13
189	            duration = 0
190	        elif random.random() < float(fail_chance):
191	            status = "failed"

--------------------------------------------------
>> Issue: [B311:blacklist] Standard pseudo-random generators are not suitable for security/cryptographic purposes.
   Severity: Low   Confidence: High
   CWE: CWE-330 (https://cwe.mitre.org/data/definitions/330.html)
   More Info: https://bandit.readthedocs.io/en/1.9.4/blacklists/blacklist_calls.html#b311-random
   Location: demo/app/app.py:192:29
191	            status = "failed"
192	            duration = round(random.uniform(0.5, 5.0), 2)
193	            failed = True

--------------------------------------------------
>> Issue: [B311:blacklist] Standard pseudo-random generators are not suitable for security/cryptographic purposes.
   Severity: Low   Confidence: High
   CWE: CWE-330 (https://cwe.mitre.org/data/definitions/330.html)
   More Info: https://bandit.readthedocs.io/en/1.9.4/blacklists/blacklist_calls.html#b311-random
   Location: demo/app/app.py:196:29
195	            status = "passed"
196	            duration = round(random.uniform(0.5, 15.0), 2)
197	

--------------------------------------------------
>> Issue: [B311:blacklist] Standard pseudo-random generators are not suitable for security/cryptographic purposes.
   Severity: Low   Confidence: High
   CWE: CWE-330 (https://cwe.mitre.org/data/definitions/330.html)
   More Info: https://bandit.readthedocs.io/en/1.9.4/blacklists/blacklist_calls.html#b311-random
   Location: demo/app/app.py:207:20
206	    total_time = round(sum(s["duration_s"] for s in stages), 2)
207	    run_id = f"run-{random.randint(1000, 9999)}"
208	

--------------------------------------------------
>> Issue: [B201:flask_debug_true] A Flask app appears to be run with debug=True, which exposes the Werkzeug debugger and allows the execution of arbitrary code.
   Severity: High   Confidence: Medium
   CWE: CWE-94 (https://cwe.mitre.org/data/definitions/94.html)
   More Info: https://bandit.readthedocs.io/en/1.9.4/plugins/b201_flask_debug_true.html
   Location: demo/app/app.py:234:4
233	if __name__ == "__main__":
234	    app.run(host="0.0.0.0", port=5001, debug=True)

--------------------------------------------------
>> Issue: [B104:hardcoded_bind_all_interfaces] Possible binding to all interfaces.
   Severity: Medium   Confidence: Medium
   CWE: CWE-605 (https://cwe.mitre.org/data/definitions/605.html)
   More Info: https://bandit.readthedocs.io/en/1.9.4/plugins/b104_hardcoded_bind_all_interfaces.html
   Location: demo/app/app.py:234:17
233	if __name__ == "__main__":
234	    app.run(host="0.0.0.0", port=5001, debug=True)

--------------------------------------------------

Code scanned:
	Total lines of code: 168
	Total lines skipped (#nosec): 0
	Total potential issues skipped due to specifically being disabled (e.g., #nosec BXXX): 0

Run metrics:
	Total issues (by severity):
		Undefined: 0
		Low: 5
		Medium: 1
		High: 1
	Total issues (by confidence):
		Undefined: 0
		Low: 0
		Medium: 2
		High: 5
Files skipped (0):
```

![SAST finding in instructor demo](screenshots/01-sast-instructor-demo-finding.png)

### 2. All scans + gate on the hardened project: PASSED

```text
$ docker build -q -t session17-python:local .
sha256:8283e72a8b12127fa042a1c9ca283e98b1fc848ee074c1aaec512c850cdb4e65
$ pytest -q 2>&1 | tail -1
8 passed, 6 warnings in 0.06s
$ ./security/scan-local.sh session17-python:local
== SAST: bandit
== SCA: pip-audit
No known vulnerabilities found
No known vulnerabilities found
== Secret scan: gitleaks
9:49PM INF scanned ~72763 bytes (72.76 KB) in 7.96ms
9:49PM INF no leaks found
== Image scan: trivy session17-python:local

Report Summary

┌──────────────────────────────────────────────────────────────────────────────┬────────────┬─────────────────┐
│                                    Target                                    │    Type    │ Vulnerabilities │
├──────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
│ session17-python:local (alpine 3.24.2)                                       │   alpine   │        0        │
├──────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
│ usr/local/lib/python3.12/site-packages/blinker-1.9.0.dist-info/METADATA      │ python-pkg │        0        │
├──────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
│ usr/local/lib/python3.12/site-packages/click-8.5.0.dist-info/METADATA        │ python-pkg │        0        │
├──────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
│ usr/local/lib/python3.12/site-packages/flask-3.1.3.dist-info/METADATA        │ python-pkg │        0        │
├──────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
│ usr/local/lib/python3.12/site-packages/gunicorn-23.0.0.dist-info/METADATA    │ python-pkg │        0        │
├──────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
│ usr/local/lib/python3.12/site-packages/itsdangerous-2.2.0.dist-info/METADATA │ python-pkg │        0        │
├──────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
│ usr/local/lib/python3.12/site-packages/jinja2-3.1.6.dist-info/METADATA       │ python-pkg │        0        │
├──────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
│ usr/local/lib/python3.12/site-packages/markupsafe-3.0.4.dist-info/METADATA   │ python-pkg │        0        │
├──────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
│ usr/local/lib/python3.12/site-packages/packaging-26.3.dist-info/METADATA     │ python-pkg │        0        │
├──────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
│ usr/local/lib/python3.12/site-packages/pip-25.0.1.dist-info/METADATA         │ python-pkg │        0        │
├──────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
│ usr/local/lib/python3.12/site-packages/werkzeug-3.1.9.dist-info/METADATA     │ python-pkg │        0        │
└──────────────────────────────────────────────────────────────────────────────┴────────────┴─────────────────┘
Legend:
- '-': Not scanned
- '0': Clean (no security findings detected)

== Security gate
SECURITY GATE
Stage    Report            Blocking  Warnings  Result
SAST     bandit.json       0         0         PASS  
SCA      pip-audit.json    0         0         PASS  
Secrets  gitleaks.json     0         0         PASS  
Image    trivy-image.json  0         0         PASS  
DECISION: PASSED - safe to push and deploy
```

![all scans pass](screenshots/02-all-scans-and-gate-pass.png)

### 3. Proof the gate works: a bad commit is BLOCKED

A throwaway copy (not committed) with one problem per stage: `requests==2.25.0`, a hard-coded (fake) AWS key, `subprocess(..., shell=True)` with user input, and an old `python:3.9-slim-bullseye` base.

```text
# Throwaway copy of the project with one problem per stage (NOT committed):
#   requirements.txt += requests==2.25.0 | app.py += hard-coded AWS key + subprocess shell=True | FROM python:3.9-slim-bullseye
$ bandit -c security/bandit.yaml -r app -q -f custom --msg-template '{test_id} {severity} {relpath}:{line} {msg}'
B404 LOW app/app.py:246 Consider possible security implications associated with the subprocess module.
B602 HIGH app/app.py:254 subprocess call with shell=True identified, security issue.
$ pip-audit -r requirements.txt 2>&1 | head -6
Found 13 known vulnerabilities in 3 packages
Name     Version ID              Fix Versions
-------- ------- --------------- ------------
requests 2.25.0  PYSEC-2023-74   2.31.0
requests 2.25.0  PYSEC-2026-1873 2.32.0
requests 2.25.0  PYSEC-2026-1872 2.32.4
$ gitleaks dir . -c security/gitleaks.toml --no-banner -v 2>&1 | grep -E 'RuleID|Secret|File|Line|leaks found'
Secret:      AKIAZ7Q3VXN4PL2M6KRT
RuleID:      aws-access-token
File:        app/app.py
Line:        248
9:51PM WRN leaks found: 1
$ ./security/scan-local.sh session17-python:bad >/dev/null 2>&1; python security/gate.py reports; echo "gate exit code: $?"
SECURITY GATE
Stage    Report            Blocking  Warnings  Result
SAST     bandit.json       1         0         FAIL  
SCA      pip-audit.json    13        0         FAIL  
Secrets  gitleaks.json     1         0         FAIL  
Image    trivy-image.json  42        67        FAIL  
  BLOCK SAST: B602 HIGH app/app.py:254 subprocess call with shell=True identified, security issue.
  BLOCK SCA: requests==2.25.0 PYSEC-2023-74 fix: 2.31.0
  BLOCK SCA: requests==2.25.0 PYSEC-2026-1873 fix: 2.32.0
  BLOCK SCA: requests==2.25.0 PYSEC-2026-1872 fix: 2.32.4
  BLOCK SCA: requests==2.25.0 PYSEC-2026-2275 fix: 2.33.0
  BLOCK SCA: idna==2.10 PYSEC-2024-60 fix: 3.7
  BLOCK SCA: idna==2.10 PYSEC-2026-215 fix: 3.15
  BLOCK SCA: urllib3==1.26.20 PYSEC-2026-141 fix: 2.7.0
  BLOCK SCA: urllib3==1.26.20 PYSEC-2026-1999 fix: 2.5.0
  BLOCK SCA: ... and 5 more (see pip-audit.json)
  BLOCK Secrets: aws-access-token app/app.py:248
  BLOCK Image: HIGH CVE-2025-68973 gpgv 2.2.27-2+deb11u2 -> 2.2.27-2+deb11u3
  BLOCK Image: CRITICAL CVE-2026-33845 libgnutls30 3.7.1-5+deb11u7 -> 3.7.1-5+deb11u10
  BLOCK Image: CRITICAL CVE-2026-42010 libgnutls30 3.7.1-5+deb11u7 -> 3.7.1-5+deb11u10
  BLOCK Image: HIGH CVE-2025-32988 libgnutls30 3.7.1-5+deb11u7 -> 3.7.1-5+deb11u8
  BLOCK Image: HIGH CVE-2025-32990 libgnutls30 3.7.1-5+deb11u7 -> 3.7.1-5+deb11u8
  BLOCK Image: HIGH CVE-2026-33846 libgnutls30 3.7.1-5+deb11u7 -> 3.7.1-5+deb11u10
  BLOCK Image: HIGH CVE-2026-3833 libgnutls30 3.7.1-5+deb11u7 -> 3.7.1-5+deb11u10
  BLOCK Image: HIGH CVE-2026-42009 libgnutls30 3.7.1-5+deb11u7 -> 3.7.1-5+deb11u10
  BLOCK Image: ... and 34 more (see trivy-image.json)
  warn  Image: HIGH CVE-2022-3715 bash 5.1-2+deb11u1 -> no fix
  warn  Image: HIGH CVE-2026-53613 bsdutils 1:2.36.1-8+deb11u2 -> no fix
  warn  Image: HIGH CVE-2026-76642 bsdutils 1:2.36.1-8+deb11u2 -> no fix
  warn  Image: HIGH CVE-2026-78408 bsdutils 1:2.36.1-8+deb11u2 -> no fix
  warn  Image: HIGH CVE-2026-78409 bsdutils 1:2.36.1-8+deb11u2 -> no fix
  warn  Image: ... and 62 more (see trivy-image.json)
DECISION: BLOCKED - image will not be pushed or deployed
gate exit code: 1
```

![gate blocks](screenshots/03-security-gate-blocks-bad-commit.png)

Every stage failed independently, so the gate exits 1 and the image is never pushed or deployed. Notice SCA caught `idna` and `urllib3` too: vulnerabilities in **transitive** dependencies pulled in by `requests`.

### 4. Container registry

The pipeline pushes to GHCR. Locally I ran the same push/pull flow against a private `registry:2`:

```text
# Container registry: the CI pushes to GHCR; locally the same flow against a private registry:2
$ docker run -d --name local-registry -p 5005:5000 registry:2
91036239119f08aea7b4b6b29bf7e0bd8a2c68c26880727ce7863b2a995b01ef
$ docker tag session17-python:local localhost:5005/session17-python:b45e5fb
$ docker push localhost:5005/session17-python:b45e5fb 2>&1 | tail -3
72cb777ae735: Pushed
d955dcb31563: Pushed
b45e5fb: digest: sha256:8283e72a8b12127fa042a1c9ca283e98b1fc848ee074c1aaec512c850cdb4e65 size: 856
$ curl -s http://localhost:5005/v2/_catalog; curl -s http://localhost:5005/v2/session17-python/tags/list
{"repositories":["session17-python"]}
{"name":"session17-python","tags":["b45e5fb"]}
$ docker rmi localhost:5005/session17-python:b45e5fb >/dev/null && docker pull -q localhost:5005/session17-python:b45e5fb
localhost:5005/session17-python:b45e5fb
$ docker image inspect localhost:5005/session17-python:b45e5fb --format 'user={{.Config.User}} cmd={{.Config.Cmd}} size={{.Size}}'
user=10001 cmd=[gunicorn --bind 0.0.0.0:5001 --workers 2 --access-logfile - app.app:app] size=23828092
```

![registry](screenshots/04-container-registry.png)

### 5. Kubernetes deployment with a restricted Pod Security namespace

```text
$ kubectl apply -f k8s/namespace.yaml
namespace/devsecops created
$ sed "s|__IMAGE__|session17-python:b45e5fb|" k8s/deployment.yaml | kubectl apply -f - && kubectl apply -f k8s/service.yaml
deployment.apps/session17-python created
service/session17-python created
$ kubectl -n devsecops rollout status deployment/session17-python --timeout=120s
Waiting for deployment "session17-python" rollout to finish: 0 of 2 updated replicas are available...
Waiting for deployment "session17-python" rollout to finish: 1 of 2 updated replicas are available...
deployment "session17-python" successfully rolled out
$ kubectl -n devsecops get deploy,pods,svc -o wide
NAME                               READY   UP-TO-DATE   AVAILABLE   AGE   CONTAINERS   IMAGES                     SELECTOR
deployment.apps/session17-python   2/2     2            2           7s    app          session17-python:b45e5fb   app=session17-python

NAME                                    READY   STATUS    RESTARTS   AGE   IP             NODE       NOMINATED NODE   READINESS GATES
pod/session17-python-59f748fd95-bc2gq   1/1     Running   0          7s    10.244.0.131   minikube   <none>           <none>
pod/session17-python-59f748fd95-jklf6   1/1     Running   0          7s    10.244.0.130   minikube   <none>           <none>

NAME                       TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)   AGE   SELECTOR
service/session17-python   ClusterIP   10.102.192.198   <none>        80/TCP    7s    app=session17-python
$ kubectl -n devsecops exec session17-python-59f748fd95-bc2gq -- sh -c 'id; touch /app/x 2>&1; touch /tmp/ok && echo /tmp writable'
uid=10001(appuser) gid=10001(appuser) groups=10001(appuser)
touch: /app/x: Read-only file system
/tmp writable
$ kubectl -n devsecops port-forward svc/session17-python 5001:80 &
$ curl -s http://127.0.0.1:5001/health; echo; curl -s http://127.0.0.1:5001/api/status; echo
{"status":"healthy","timestamp":"2026-10-07T16:29:32.317584Z","uptime_seconds":7.42}

{"app":"DevSecOps Dashboard","platform":"Linux","python_version":"3.12.15","status":"running","timestamp":"2026-10-07T16:29:32.331198Z","total_requests":2,"uptime":"00h 00m 07s","version":"2.0.0"}

# Deploy-time guard: the instructor's demo/k8s/deployment.yaml (root, no securityContext) in the restricted namespace:
$ sed 's|nensiravaliya28/hey-cicd:__IMAGE_TAG__|session17-python:b45e5fb|' ../demo/k8s/deployment.yaml | kubectl -n devsecops apply --dry-run=server -f - 2>&1 | fold -w 160
Warning: would violate PodSecurity "restricted:latest": allowPrivilegeEscalation != false (container "session17-python" must set securityContext.allowPrivilegeE
scalation=false), unrestricted capabilities (container "session17-python" must set securityContext.capabilities.drop=["ALL"]), runAsNonRoot != true (pod or cont
ainer "session17-python" must set securityContext.runAsNonRoot=true), seccompProfile (pod or container "session17-python" must set securityContext.seccompProfil
e.type to "RuntimeDefault" or "Localhost")
deployment.apps/session17-python configured (server dry run)
# For a Deployment PSA only warns; the ReplicaSet's pods are what get rejected. A bare pod shows the hard block:
$ kubectl -n devsecops run root-pod --image=nginx:1.27 --dry-run=server 2>&1 | fold -w 160
Error from server (Forbidden): pods "root-pod" is forbidden: violates PodSecurity "restricted:latest": allowPrivilegeEscalation != false (container "root-pod" m
ust set securityContext.allowPrivilegeEscalation=false), unrestricted capabilities (container "root-pod" must set securityContext.capabilities.drop=["ALL"]), ru
nAsNonRoot != true (pod or container "root-pod" must set securityContext.runAsNonRoot=true), seccompProfile (pod or container "root-pod" must set securityContex
t.seccompProfile.type to "RuntimeDefault" or "Localhost")
```

![deploy restricted](screenshots/05-deploy-kubernetes-restricted.png)

The app runs as uid 10001, cannot write to its own filesystem (only to the `/tmp` emptyDir), and the namespace itself refuses root/privileged pods. That is a second, deploy-time security gate.

---

## Pipeline execution

The repository is not pushed yet, so I executed the workflow with **act** (local GitHub Actions runner) on a `pull_request` event. A PR runs stages 1–8; 9 Push and 10 Deploy only run on push to `main`. 3b CodeQL and the SARIF upload only exist on GitHub (they need the code-scanning API) and are skipped locally via `github.event.act`.

### All stages green

```text
$ act pull_request -W .github/workflows/session17-devsecops.yml -e pr-event.json -P ubuntu-latest=ghcr.io/catthehacker/ubuntu:act-latest --artifact-server-path ./artifacts
[1. Build] ⭐ Run Main Install runtime dependencies
[1. Build]   ✅  Success - Main Install runtime dependencies [2.803668792s]
[1. Build] ⭐ Run Main Compile and import the app
[1. Build]   ✅  Success - Main Compile and import the app [140.523791ms]
[1. Build] 🏁  Job succeeded
[2. Unit Test] ⭐ Run Main pip install -r requirements-dev.txt
[2. Unit Test]   ✅  Success - Main pip install -r requirements-dev.txt [2.062795416s]
[2. Unit Test] ⭐ Run Main pytest
[2. Unit Test]   ✅  Success - Main pytest [384.874083ms]
[2. Unit Test] 🏁  Job succeeded
[5. Secret Scan (gitleaks)] ⭐ Run Main Install gitleaks (checksum verified)
[4. SCA (pip-audit)] ⭐ Run Main pip install pip-audit==2.9.0
[3. SAST (Bandit)] ⭐ Run Main pip install "bandit[sarif]==1.9.4"
[3. SAST (Bandit)]   ✅  Success - Main pip install "bandit[sarif]==1.9.4" [1.963007625s]
[4. SCA (pip-audit)]   ✅  Success - Main pip install pip-audit==2.9.0 [2.080371125s]
[3. SAST (Bandit)] ⭐ Run Main Bandit
[4. SCA (pip-audit)] ⭐ Run Main pip-audit
[3. SAST (Bandit)]   ✅  Success - Main Bandit [429.771ms]
[3. SAST (Bandit)] 🏁  Job succeeded
[5. Secret Scan (gitleaks)]   ✅  Success - Main Install gitleaks (checksum verified) [7.823896959s]
[5. Secret Scan (gitleaks)] ⭐ Run Main gitleaks
[5. Secret Scan (gitleaks)]   ✅  Success - Main gitleaks [279.849833ms]
[5. Secret Scan (gitleaks)] 🏁  Job succeeded
[4. SCA (pip-audit)]   ✅  Success - Main pip-audit [43.981631334s]
[4. SCA (pip-audit)] 🏁  Job succeeded
[6. Docker Build] ⭐ Run Main Build image
[6. Docker Build]   ✅  Success - Main Build image [2.425387958s]
[6. Docker Build] ⭐ Run Main Save image
[6. Docker Build]   ✅  Success - Main Save image [484.767416ms]
[6. Docker Build] 🏁  Job succeeded
[7. Container Image Scan (Trivy)] ⭐ Run Main Load image
[7. Container Image Scan (Trivy)]   ✅  Success - Main Load image [302.306209ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Create report directory
[7. Container Image Scan (Trivy)]   ✅  Success - Main Create report directory [36.118833ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Trivy (JSON report for the gate)
[7. Container Image Scan (Trivy)] ⭐ Run Main Install Trivy
[7. Container Image Scan (Trivy)] ⭐ Run Main Binary dir
[7. Container Image Scan (Trivy)]   ✅  Success - Main Binary dir [34.191125ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Restore Trivy binary from cache
[7. Container Image Scan (Trivy)]   ✅  Success - Main Restore Trivy binary from cache [1.277667708s]
[7. Container Image Scan (Trivy)] ⭐ Run Main Add Trivy binary to $GITHUB_PATH
[7. Container Image Scan (Trivy)]   ✅  Success - Main Add Trivy binary to $GITHUB_PATH [34.687875ms]
[7. Container Image Scan (Trivy)]   ✅  Success - Main Install Trivy [1.560647125s]
[7. Container Image Scan (Trivy)] ⭐ Run Main Get current date
[7. Container Image Scan (Trivy)]   ✅  Success - Main Get current date [56.603333ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Restore DB from cache
[7. Container Image Scan (Trivy)]   ✅  Success - Main Restore DB from cache [1.034758583s]
[7. Container Image Scan (Trivy)] ⭐ Run Main Set GitHub Path
[7. Container Image Scan (Trivy)]   ✅  Success - Main Set GitHub Path [40.274584ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Clear Trivy Envs file
[7. Container Image Scan (Trivy)]   ✅  Success - Main Clear Trivy Envs file [40.499792ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Set Trivy environment variables
[7. Container Image Scan (Trivy)]   ✅  Success - Main Set Trivy environment variables [41.998291ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Run Trivy
[7. Container Image Scan (Trivy)]   ✅  Success - Main Run Trivy [1m12.091269416s]
[7. Container Image Scan (Trivy)] ⭐ Run Main Remove Trivy Envs file
[7. Container Image Scan (Trivy)]   ✅  Success - Main Remove Trivy Envs file [51.178875ms]
[7. Container Image Scan (Trivy)]   ✅  Success - Main Trivy (JSON report for the gate) [1m15.423724667s]
[7. Container Image Scan (Trivy)] ⭐ Run Main Trivy (readable table, HIGH/CRITICAL)
[7. Container Image Scan (Trivy)] ⭐ Run Main Get current date
[7. Container Image Scan (Trivy)]   ✅  Success - Main Get current date [43.549375ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Restore DB from cache
[7. Container Image Scan (Trivy)]   ✅  Success - Main Restore DB from cache [971.924667ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Set GitHub Path
[7. Container Image Scan (Trivy)]   ✅  Success - Main Set GitHub Path [47.2745ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Clear Trivy Envs file
[7. Container Image Scan (Trivy)]   ✅  Success - Main Clear Trivy Envs file [49.011083ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Set Trivy environment variables
[7. Container Image Scan (Trivy)]   ✅  Success - Main Set Trivy environment variables [49.1435ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Run Trivy
[7. Container Image Scan (Trivy)]   ✅  Success - Main Run Trivy [185.340667ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Remove Trivy Envs file
[7. Container Image Scan (Trivy)]   ✅  Success - Main Remove Trivy Envs file [67.277625ms]
[7. Container Image Scan (Trivy)]   ✅  Success - Main Trivy (readable table, HIGH/CRITICAL) [1.895017417s]
[7. Container Image Scan (Trivy)] 🏁  Job succeeded
[8. Security Gate] ⭐ Run Main Apply security policy
[8. Security Gate]   ✅  Success - Main Apply security policy [77.882625ms]
[8. Security Gate] 🏁  Job succeeded
# 3b CodeQL is GitHub-only (skipped locally); 9 Push and 10 Deploy only run on push to main
```

![pipeline overview](screenshots/06-pipeline-overview.png)

### Scanner output inside the pipeline

```text
# jobs 3 SAST, 4 SCA, 5 Secret Scan - scanner output
[5. Secret Scan (gitleaks)] ⭐ Run Main Install gitleaks (checksum verified)
[3. SAST (Bandit)] ⭐ Run Main Bandit
[4. SCA (pip-audit)] ⭐ Run Main pip-audit
[3. SAST (Bandit)]   | 	No issues identified.
[3. SAST (Bandit)]   | 	Total lines of code: 172
[3. SAST (Bandit)]   | 	Total lines skipped (#nosec): 0
[3. SAST (Bandit)]   | 		Medium: 0
[3. SAST (Bandit)]   | 		High: 0
[3. SAST (Bandit)]   | 		Medium: 0
[3. SAST (Bandit)]   | 		High: 0
[3. SAST (Bandit)]   ✅  Success - Main Bandit [429.771ms]
[3. SAST (Bandit)] 🏁  Job succeeded
[5. Secret Scan (gitleaks)]   | gitleaks_8.30.1_linux_arm64.tar.gz: OK
[5. Secret Scan (gitleaks)]   ✅  Success - Main Install gitleaks (checksum verified) [7.823896959s]
[5. Secret Scan (gitleaks)] ⭐ Run Main gitleaks
[5. Secret Scan (gitleaks)]   | 4:39PM INF scanned ~50708 bytes (50.71 KB) in 8.76ms
[5. Secret Scan (gitleaks)]   | 4:39PM INF no leaks found
[5. Secret Scan (gitleaks)]   ✅  Success - Main gitleaks [279.849833ms]
[5. Secret Scan (gitleaks)] 🏁  Job succeeded
[4. SCA (pip-audit)]   | No known vulnerabilities found
[4. SCA (pip-audit)]   | No known vulnerabilities found
[4. SCA (pip-audit)]   ✅  Success - Main pip-audit [43.981631334s]
[4. SCA (pip-audit)] 🏁  Job succeeded
```

![pipeline scans](screenshots/09-pipeline-scans.png)

### Container image scan stage

```text
# job 7. Container Image Scan (Trivy)
[7. Container Image Scan (Trivy)] ⭐ Run Main actions/checkout@v6
[7. Container Image Scan (Trivy)]   ✅  Success - Main actions/checkout@v6 [415.214875ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main actions/download-artifact@v5
[7. Container Image Scan (Trivy)]   ✅  Success - Main actions/download-artifact@v5 [644.388625ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Load image
[7. Container Image Scan (Trivy)]   | Loaded image: session17-python:b45e5fb9ca80b386176d4478d4a7a435faefc478
[7. Container Image Scan (Trivy)]   ✅  Success - Main Load image [302.306209ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Create report directory
[7. Container Image Scan (Trivy)]   ✅  Success - Main Create report directory [36.118833ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Trivy (JSON report for the gate)
[7. Container Image Scan (Trivy)] ⭐ Run Main Install Trivy
[7. Container Image Scan (Trivy)] ⭐ Run Main Binary dir
[7. Container Image Scan (Trivy)]   ✅  Success - Main Binary dir [34.191125ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Restore Trivy binary from cache
[7. Container Image Scan (Trivy)]   ✅  Success - Main Restore Trivy binary from cache [1.277667708s]
[7. Container Image Scan (Trivy)] ⭐ Run Main Add Trivy binary to $GITHUB_PATH
[7. Container Image Scan (Trivy)]   ✅  Success - Main Add Trivy binary to $GITHUB_PATH [34.687875ms]
[7. Container Image Scan (Trivy)]   ✅  Success - Main Install Trivy [1.560647125s]
[7. Container Image Scan (Trivy)] ⭐ Run Main Get current date
[7. Container Image Scan (Trivy)]   ✅  Success - Main Get current date [56.603333ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Restore DB from cache
[7. Container Image Scan (Trivy)]   ✅  Success - Main Restore DB from cache [1.034758583s]
[7. Container Image Scan (Trivy)] ⭐ Run Main Set GitHub Path
[7. Container Image Scan (Trivy)]   ✅  Success - Main Set GitHub Path [40.274584ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Clear Trivy Envs file
[7. Container Image Scan (Trivy)]   ✅  Success - Main Clear Trivy Envs file [40.499792ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Set Trivy environment variables
[7. Container Image Scan (Trivy)]   ✅  Success - Main Set Trivy environment variables [41.998291ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Run Trivy
[7. Container Image Scan (Trivy)]   ✅  Success - Main Run Trivy [1m12.091269416s]
[7. Container Image Scan (Trivy)] ⭐ Run Main Remove Trivy Envs file
[7. Container Image Scan (Trivy)]   ✅  Success - Main Remove Trivy Envs file [51.178875ms]
[7. Container Image Scan (Trivy)]   ✅  Success - Main Trivy (JSON report for the gate) [1m15.423724667s]
[7. Container Image Scan (Trivy)] ⭐ Run Main Trivy (readable table, HIGH/CRITICAL)
[7. Container Image Scan (Trivy)] ⭐ Run Main Get current date
[7. Container Image Scan (Trivy)]   ✅  Success - Main Get current date [43.549375ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Restore DB from cache
[7. Container Image Scan (Trivy)]   ✅  Success - Main Restore DB from cache [971.924667ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Set GitHub Path
[7. Container Image Scan (Trivy)]   ✅  Success - Main Set GitHub Path [47.2745ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Clear Trivy Envs file
[7. Container Image Scan (Trivy)]   ✅  Success - Main Clear Trivy Envs file [49.011083ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Set Trivy environment variables
[7. Container Image Scan (Trivy)]   ✅  Success - Main Set Trivy environment variables [49.1435ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Run Trivy
[7. Container Image Scan (Trivy)]   ✅  Success - Main Run Trivy [185.340667ms]
[7. Container Image Scan (Trivy)] ⭐ Run Main Remove Trivy Envs file
[7. Container Image Scan (Trivy)]   ✅  Success - Main Remove Trivy Envs file [67.277625ms]
[7. Container Image Scan (Trivy)]   ✅  Success - Main Trivy (readable table, HIGH/CRITICAL) [1.895017417s]
[7. Container Image Scan (Trivy)] ⭐ Run Main actions/upload-artifact@v4
[7. Container Image Scan (Trivy)]   ✅  Success - Main actions/upload-artifact@v4 [829.780083ms]
[7. Container Image Scan (Trivy)] 🏁  Job succeeded
[7. Container Image Scan (Trivy)]   | Report Summary
[7. Container Image Scan (Trivy)]   | 
[7. Container Image Scan (Trivy)]   | ┌──────────────────────────────────────────────────────────────────────────────┬────────────┬─────────────────┐
[7. Container Image Scan (Trivy)]   | │                                    Target                                    │    Type    │ Vulnerabilities │
[7. Container Image Scan (Trivy)]   | ├──────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
[7. Container Image Scan (Trivy)]   | │ session17-python:b45e5fb9ca80b386176d4478d4a7a435faefc478 (alpine 3.24.2)    │   alpine   │        0        │
[7. Container Image Scan (Trivy)]   | ├──────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
[7. Container Image Scan (Trivy)]   | │ usr/local/lib/python3.12/site-packages/blinker-1.9.0.dist-info/METADATA      │ python-pkg │        0        │
[7. Container Image Scan (Trivy)]   | ├──────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
[7. Container Image Scan (Trivy)]   | │ usr/local/lib/python3.12/site-packages/click-8.5.0.dist-info/METADATA        │ python-pkg │        0        │
[7. Container Image Scan (Trivy)]   | ├──────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
[7. Container Image Scan (Trivy)]   | │ usr/local/lib/python3.12/site-packages/flask-3.1.3.dist-info/METADATA        │ python-pkg │        0        │
[7. Container Image Scan (Trivy)]   | ├──────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
[7. Container Image Scan (Trivy)]   | │ usr/local/lib/python3.12/site-packages/gunicorn-23.0.0.dist-info/METADATA    │ python-pkg │        0        │
[7. Container Image Scan (Trivy)]   | ├──────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
[7. Container Image Scan (Trivy)]   | │ usr/local/lib/python3.12/site-packages/itsdangerous-2.2.0.dist-info/METADATA │ python-pkg │        0        │
[7. Container Image Scan (Trivy)]   | ├──────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
[7. Container Image Scan (Trivy)]   | │ usr/local/lib/python3.12/site-packages/jinja2-3.1.6.dist-info/METADATA       │ python-pkg │        0        │
[7. Container Image Scan (Trivy)]   | ├──────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
[7. Container Image Scan (Trivy)]   | │ usr/local/lib/python3.12/site-packages/markupsafe-3.0.4.dist-info/METADATA   │ python-pkg │        0        │
[7. Container Image Scan (Trivy)]   | ├──────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
[7. Container Image Scan (Trivy)]   | │ usr/local/lib/python3.12/site-packages/packaging-26.3.dist-info/METADATA     │ python-pkg │        0        │
[7. Container Image Scan (Trivy)]   | ├──────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
[7. Container Image Scan (Trivy)]   | │ usr/local/lib/python3.12/site-packages/pip-25.0.1.dist-info/METADATA         │ python-pkg │        0        │
[7. Container Image Scan (Trivy)]   | ├──────────────────────────────────────────────────────────────────────────────┼────────────┼─────────────────┤
[7. Container Image Scan (Trivy)]   | │ usr/local/lib/python3.12/site-packages/werkzeug-3.1.9.dist-info/METADATA     │ python-pkg │        0        │
[7. Container Image Scan (Trivy)]   | └──────────────────────────────────────────────────────────────────────────────┴────────────┴─────────────────┘
[7. Container Image Scan (Trivy)]   | Legend:
[7. Container Image Scan (Trivy)]   | - '-': Not scanned
[7. Container Image Scan (Trivy)]   | - '0': Clean (no security findings detected)
```

![pipeline trivy](screenshots/08-pipeline-trivy.png)

### Security gate stage

```text
# job 8. Security Gate (needs: sast, sca, secret-scan, image-scan)
[8. Security Gate] ⭐ Run Main actions/checkout@v6
[8. Security Gate]   ✅  Success - Main actions/checkout@v6 [526.908791ms]
[8. Security Gate] ⭐ Run Main actions/download-artifact@v5
[8. Security Gate]   | Filtering artifacts by pattern 'reports-*'
[8. Security Gate]   | - reports-sca (ID: 3352424300, Size: 96, Expected Digest: undefined)
[8. Security Gate]   | - reports-sast (ID: 3158610192, Size: 96, Expected Digest: undefined)
[8. Security Gate]   | - reports-image (ID: 2871320164, Size: 96, Expected Digest: undefined)
[8. Security Gate]   | - reports-secrets (ID: 344493484, Size: 96, Expected Digest: undefined)
[8. Security Gate]   | Total of 4 artifact(s) downloaded
[8. Security Gate]   ✅  Success - Main actions/download-artifact@v5 [489.392333ms]
[8. Security Gate] ⭐ Run Main Apply security policy
[8. Security Gate]   | SECURITY GATE
[8. Security Gate]   | Stage    Report            Blocking  Warnings  Result
[8. Security Gate]   | SAST     bandit.json       0         0         PASS  
[8. Security Gate]   | SCA      pip-audit.json    0         0         PASS  
[8. Security Gate]   | Secrets  gitleaks.json     0         0         PASS  
[8. Security Gate]   | Image    trivy-image.json  0         0         PASS  
[8. Security Gate]   | DECISION: PASSED - safe to push and deploy
[8. Security Gate]   ✅  Success - Main Apply security policy [77.882625ms]
[8. Security Gate] 🏁  Job succeeded
```

![pipeline gate](screenshots/07-pipeline-gate.png)

### After pushing

The first push to `main` that touches `session-17-devsecops/devsecops-project/` runs all 10 stages on GitHub. Take screenshots of the run graph, the **Security gate** job summary, the GHCR package and the deploy job log, and add them to `screenshots/`. CodeQL / Bandit results appear under **Security → Code scanning** if the repository is public (or has GitHub Advanced Security).

---

## Problems I hit (and what they taught me)

| Problem | Lesson |
| :--- | :--- |
| Bandit 1.8.6 crashed on Python 3.14 (`ast.Num` removed) but still wrote a report with **zero results**, so the first gate said SAST PASS | a crashed scanner looks like a clean scan. The gate now blocks when the report has `errors`; upgraded to Bandit 1.9.4 |
| gitleaks did not flag my first fake AWS key | the rule matches the real key alphabet (`AKIA` + 16 chars of A–Z/2–7); my fake had an `8`. Pattern-based scanners only find what looks real; also rotate any key that ever reaches Git |
| `aquasecurity/trivy-action@0.33.1` → `reference not found` | that action's tags are `v`-prefixed (`v0.36.0`); pin real tags |
| Trivy `failed to create output file` | the `reports/` dir does not exist in a fresh checkout |
| act hung cloning `github/codeql-action` | act clones every action a job references, even skipped steps → moved CodeQL/SARIF into its own job that is skipped as a whole |
| Deployment applied fine in a `restricted` namespace even though it was insecure | Pod Security only **warns** for Deployments; the ReplicaSet's pods are what get rejected (shown with the bare-pod dry run) |

## Key takeaways

- **Shift left:** SAST/SCA/secrets run before anything is built; image scanning runs before anything is pushed.
- **Scan what you ship:** build once, scan that artifact, push that artifact, deploy that artifact.
- **A gate needs teeth:** one explicit policy, fails closed (missing or broken report = block), warnings for things you cannot fix yet.
- **Defense in depth:** CI gate + hardened image + Kubernetes Pod Security admission.
