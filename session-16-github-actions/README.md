# Session 16: CI/CD & GitHub Actions

**Author:** Pranay Reddy
**Course:** SST DevOps & Cloud [SWE]
**Session:** 16
**Repository:** devops-heros / session-16-github-actions

## Task: Demo Project

**→ [cicd-demo-project/README.md](cicd-demo-project/README.md)**

A Flask calculator API (based on [10-final-cicd-pipeline](10-final-cicd-pipeline/)) with a complete GitHub Actions pipeline at [/.github/workflows/session16-cicd.yml](../.github/workflows/session16-cicd.yml):

```text
CI:  lint ──► test (py3.11, py3.12) ──► build artifact ─┐
                                    └─► docker build + smoke test ─┤
CD:                                       (push to main only) ─────┴─► publish to GHCR ──► deploy to Kubernetes (kind)
```

| Required topic | Covered in |
| :--- | :--- |
| CI vs CD | [CI vs CD](cicd-demo-project/README.md#ci-vs-cd) |
| CI/CD pipeline | [The pipeline](cicd-demo-project/README.md#the-pipeline) |
| GitHub Actions, workflow, jobs, steps, runners, secrets, artifacts | [Building blocks table](cicd-demo-project/README.md#github-actions-building-blocks-used) and the workflow file |
| Build, Test | `build.sh`, `pytest` jobs, [Build and Test](cicd-demo-project/README.md#build-and-test) |
| Pipeline execution | [Pipeline execution](cicd-demo-project/README.md#pipeline-execution): green run, failing run, artifacts, CD deploy |

| Deliverable | Status |
| :--- | :--- |
| Application source code | `cicd-demo-project/app/`, `tests/` |
| Dockerfile | `cicd-demo-project/Dockerfile` |
| GitHub Actions workflow | `.github/workflows/session16-cicd.yml` (repo root) |
| CI pipeline | jobs `lint`, `test`, `build`, `docker`: executed, all green (screenshots `p-01`–`p-04`) |
| CD pipeline | jobs `publish`, `deploy`: deploy steps executed on minikube (`p-06`); run on GitHub after the first push |
| Screenshots of successful pipeline execution | [screenshots/](screenshots/) (local `act` run); GitHub Actions UI screenshots to be added after pushing |

### Screenshots

| File | Shows |
| :--- | :--- |
| `p-01-overview.png` | every job and step of the CI run succeeding |
| `p-02-test.png` | pytest output in the Python 3.12 matrix job, 10 passed, 95% coverage |
| `p-03-build-docker.png` | build artifact + Docker build, container smoke test, artifact uploads |
| `p-04-artifacts.png` | the artifacts the run produced (build, test reports, image) |
| `p-05-failing.png` | a broken test failing both matrix legs and blocking build/docker |
| `p-06-cd-deploy-minikube.png` | the CD deploy steps against Kubernetes |

## Session material

The instructor's topic folders `01-ci-vs-cd` … `10-final-cicd-pipeline` and `demo/` (moved up from the nested `session-16-github-actions/session-16-github-actions/` folder, unchanged), plus the instructor's updated version of the lessons in [instructor-v2/](instructor-v2/).
