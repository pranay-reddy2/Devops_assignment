# Session 20 – GitOps

**Author:** Pranay Reddy
**Course:** SST DevOps & Cloud [SWE]
**Session:** 20, Task 3 (GitOps)

This task explains GitOps: what it is, why Git is the source of truth, declarative configuration, continuous reconciliation, the end-to-end workflow, and how Argo CD implements it on Kubernetes. It builds on the instructor folders [05-introduction-to-gitops](../05-introduction-to-gitops/README.md), [06-git-as-source-of-truth](../06-git-as-source-of-truth/README.md), [07-argocd](../07-argocd/README.md) and [08-mini-project](../08-mini-project/README.md).

```text
GIT        -> desired state
ARGO CD    -> reconciliation
KUBERNETES -> actual state
```

---

## What is GitOps?

GitOps is a way of operating infrastructure and applications where **the desired state of the whole system is stored declaratively in Git**, and **a software agent running inside the environment continuously pulls that state and makes the live system match it**.

The OpenGitOps project (CNCF) defines four principles:

| # | Principle | Meaning |
| :--- | :--- | :--- |
| 1 | Declarative | The system's desired state is expressed declaratively (YAML manifests, Helm charts, Kustomize). |
| 2 | Versioned and Immutable | Desired state is stored in a way that keeps a complete, immutable version history (Git commits). |
| 3 | Pulled Automatically | Agents automatically pull the desired state from the source. No one pushes into the cluster. |
| 4 | Continuously Reconciled | Agents continuously observe actual state and try to apply the desired state. |

Traditional vs GitOps:

```text
Traditional:  Developer --> kubectl apply --> Kubernetes

GitOps:       Developer --> Git (PR) --> Argo CD (in cluster) --> Kubernetes
```

In GitOps, a routine production change is a Git commit, not a `kubectl` command.

---

## Git as the Source of Truth

Git holds **what we want** (desired state). The cluster holds **what we have** (actual state). If the two disagree, Git wins.

What Git gives us for free:

| Git feature | Operational benefit |
| :--- | :--- |
| Commit history | Full audit trail: who changed what, when, and why (commit message) |
| Pull requests | Peer review and approval before anything reaches the cluster |
| `git diff` | Exact preview of a change (`-  replicas: 2` / `+  replicas: 3`) |
| Branch protection | Only reviewed changes on `main` are deployed |
| `git revert` | Rollback to any earlier known-good state |
| Clone | Disaster recovery: a new cluster can be rebuilt from the repo |

Example repo layout (from 06-git-as-source-of-truth):

```text
my-company-gitops/
|-- apps/
|   |-- payments/
|   |-- orders/
|-- environments/
    |-- dev/
    |-- staging/
    |-- production/
```

Because the cluster is just a copy of Git, nobody needs direct `kubectl` write access to production. Engineers get read access, and the Argo CD controller holds the write permissions.

---

## Declarative Configuration

**Imperative:** you tell the system the steps to perform. **Declarative:** you describe the end result and let a controller work out the steps.

| Imperative (kubectl commands) | Declarative (manifest in Git) |
| :--- | :--- |
| `kubectl create deployment session20-app --image=nginx:1.27-alpine` | `kind: Deployment` with `image: nginx:1.27-alpine` |
| `kubectl scale deployment session20-app --replicas=3` | `replicas: 3` |
| `kubectl set image deployment/session20-app nginx=nginx:1.28-alpine` | change the `image:` line and commit |
| `kubectl expose deployment session20-app --port=80` | `kind: Service` with `port: 80` |
| Result depends on current state and order of commands | Same file always produces the same result (idempotent) |
| History lives in someone's shell | History lives in Git |

Side by side, getting 3 nginx replicas behind a Service:

```text
IMPERATIVE                                    DECLARATIVE (app/deployment.yaml + app/service.yaml)
------------------------------------------    ----------------------------------------------------
kubectl create namespace session20            apiVersion: apps/v1
kubectl create deployment session20-app \     kind: Deployment
  --image=nginx:1.27-alpine -n session20      metadata:
kubectl scale deployment session20-app \        name: session20-app
  --replicas=3 -n session20                     namespace: session20
kubectl expose deployment session20-app \     spec:
  --port=80 -n session20                        replicas: 3
                                                selector:
# Running these twice errors                      matchLabels: {app: session20-app}
# ("AlreadyExists"). Nothing records            template:
# that replicas was changed to 3.                 metadata:
                                                    labels: {app: session20-app}
                                                  spec:
                                                    containers:
                                                      - name: nginx
                                                        image: nginx:1.27-alpine
                                                        ports: [{containerPort: 80}]
                                              ---
                                              apiVersion: v1
                                              kind: Service
                                              metadata: {name: session20-app, namespace: session20}
                                              spec:
                                                selector: {app: session20-app}
                                                ports: [{port: 80, targetPort: 80}]
```

GitOps requires the declarative style, because a controller can only compare Git to the cluster if Git contains the full desired state.

---

## Continuous Reconciliation

Argo CD runs a control loop, the same idea as a Kubernetes controller:

```text
          +---------------------------+
          |   Git (desired state)     |
          |   replicas: 3             |
          +-------------+-------------+
                        |  1. fetch (poll every ~3 min, or webhook)
                        v
          +---------------------------+
          |  Argo CD                  |
          |  2. render manifests      |      Synced    -> do nothing
          |  3. diff desired vs live  |----> OutOfSync -> 4. sync (apply diff)
          +-------------+-------------+
                        ^                          |
     5. observe again   |                          v
          +-------------+-------------+    +---------------+
          |  Kubernetes (live state)  |<---|  kubectl-like |
          |  replicas: 3              |    |  apply/delete |
          +---------------------------+    +---------------+
                     (loop repeats forever)
```

Key terms:

| Term | Meaning |
| :--- | :--- |
| Desired state | What the manifests in Git say at `targetRevision` |
| Live state | What the Kubernetes API currently reports |
| Drift | Any difference between the two (someone ran `kubectl scale`, edited a ConfigMap, deleted a Service) |
| Sync status | `Synced` (live = Git) or `OutOfSync` (drift or new commit) |
| Health status | `Healthy`, `Progressing`, `Degraded`, `Missing` (whether the resources are actually working) |
| Self-heal | With `selfHeal: true`, Argo CD reverts drift caused by manual changes in the cluster |
| Prune | With `prune: true`, resources deleted from Git are also deleted from the cluster |

Self-heal example (from 08-mini-project): Git says `replicas: 3`, someone runs `kubectl scale deployment session20-mini --replicas=1`. Argo CD sees `OutOfSync`, re-applies Git, and the Deployment goes back to 3/3. Without `prune`, removing `service.yaml` from Git would leave an orphaned Service running.

---

## GitOps Workflow

```text
 Developer        Git hosting           CI (GitHub Actions)        Argo CD (in cluster)       Kubernetes
     |                 |                        |                          |                       |
     |-- branch + PR ->|                        |                          |                       |
     |   (replicas 3)  |-- run checks --------->|                          |                       |
     |                 |   (yaml lint, kubeconform, tests)                 |                       |
     |<- review -------|                        |                          |                       |
     |-- approve/merge>|  main updated          |                          |                       |
     |                 |<------------- poll / webhook ---------------------|                       |
     |                 |                                                   |-- diff: OutOfSync     |
     |                 |                                                   |-- sync (apply) ------>|
     |                 |                                                   |<- status: Healthy ----|
     |                 |                                                   |   Synced + Healthy    |
```

For an application code change the flow is two-step: CI builds and pushes a new image (e.g. `app:1.4.2`), then CI or a bot opens a PR in the config repo that updates the image tag. Argo CD deploys that commit.

### Push-based CI/CD vs pull-based GitOps

| | Push-based CI/CD | Pull-based GitOps |
| :--- | :--- | :--- |
| Who deploys | CI pipeline runs `kubectl apply` / `helm upgrade` | Agent inside the cluster (Argo CD / Flux) pulls from Git |
| Cluster credentials | Stored in CI (kubeconfig secret), cluster API must be reachable from CI | Stay inside the cluster, no inbound access needed |
| Drift detection | None: deploys once, then forgets | Continuous: detects and can fix drift |
| Source of truth | Pipeline run + whatever is in the cluster | Git |
| Rollback | Re-run an old pipeline or manual commands | `git revert` |
| Audit | CI logs (may expire) | Git history |
| Multi-cluster | One pipeline step per cluster | Each cluster pulls on its own |

CI is still used in GitOps, but only for building, testing and publishing artifacts, not for deploying to the cluster.

---

## Kubernetes + GitOps

Argo CD installs CRDs into the cluster. The main one is `Application`. This is the repo's [07-argocd/app/argocd-application.yaml](../07-argocd/app/argocd-application.yaml):

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: session20-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/Nency-Ravaliya/gitops-demo.git
    targetRevision: main
    path: app
  destination:
    server: https://kubernetes.default.svc
    namespace: session20
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

| Field | Meaning |
| :--- | :--- |
| `metadata.namespace: argocd` | Application objects live in Argo CD's own namespace, not the app's |
| `spec.project: default` | AppProject that limits which repos, clusters and namespaces this app may use |
| `source.repoURL` | Git repository to watch |
| `source.targetRevision: main` | Branch, tag or commit SHA to track |
| `source.path: app` | Folder in the repo containing the manifests (plain YAML here; Helm and Kustomize also supported) |
| `destination.server` | Target cluster API. `https://kubernetes.default.svc` means the same cluster Argo CD runs in |
| `destination.namespace: session20` | Namespace the resources are deployed into |
| `syncPolicy.automated` | Sync automatically when Git changes. Without it, sync is manual (UI/CLI) |
| `automated.prune: true` | Delete live resources that no longer exist in Git |
| `automated.selfHeal: true` | Revert manual changes made directly in the cluster |
| `syncOptions: CreateNamespace=true` | Create `session20` if it does not exist |

This file is applied once by an admin (`kubectl apply -f app/argocd-application.yaml`) and kept outside the watched `path`, as the instructor notes. After that, every commit under `app/` is deployed by Argo CD. Check status with `kubectl get applications -n argocd` (expected `Synced` / `Healthy`).

### Argo CD vs Flux

| | Argo CD | Flux (v2) |
| :--- | :--- | :--- |
| CNCF status | Graduated | Graduated |
| Main object | `Application` / `ApplicationSet` | `GitRepository` + `Kustomization` / `HelmRelease` |
| UI | Built-in web UI with resource tree and diffs | No built-in UI (CLI, third-party UIs) |
| Multi-tenancy | AppProjects, SSO, RBAC in Argo CD | Kubernetes RBAC and namespaces |
| Multi-cluster | One Argo CD can manage many clusters | Usually one Flux per cluster |
| Image automation | Separate Argo CD Image Updater | Built-in image reflector/automation controllers |
| Feel | Application-centric, good for teams that want visibility | Toolkit of small controllers, very Kubernetes-native |

---

## Rollback via git revert

Because the cluster follows Git, rollback is just another commit:

```bash
git log --oneline -3
# 9c1e2f7 Bump nginx to 1.28-alpine   <- broke the app
# 4a7b3d1 Scale up to 3 replicas
# 2f0c9e8 Add session 20 application manifests

git revert 9c1e2f7
git push
```

Argo CD sees the new commit, shows `OutOfSync`, and syncs the cluster back to the previous image. The bad change and its revert both stay in history for the post-incident review.

Avoid rolling back with `kubectl rollout undo` or the Argo CD UI "Rollback" button while auto-sync is on: the cluster would no longer match Git, and with `selfHeal` Argo CD would immediately re-apply the broken version. Fix Git, not the cluster.

---

## Best Practices

- **Separate app and config repos:** application source code + Dockerfile in one repo (CI builds images); Kubernetes manifests in a config/GitOps repo (Argo CD watches). This keeps deploy history clean and avoids CI loops where a manifest commit triggers a new build.
- **Environments as folders, Helm values or Kustomize overlays,** not long-lived branches per environment:

```text
config-repo/
|-- base/                      # shared Deployment, Service
|   |-- deployment.yaml
|   |-- kustomization.yaml
|-- overlays/
    |-- dev/kustomization.yaml         # replicas: 1, image tag: latest-build
    |-- staging/kustomization.yaml     # replicas: 2
    |-- production/kustomization.yaml  # replicas: 5, resource limits
```

  With Helm, the same chart is used with `values-dev.yaml`, `values-prod.yaml`. One Argo CD Application (or an ApplicationSet) per environment points at the right path.
- **Never store plain Secrets in Git.** Base64 is encoding, not encryption. Options:

| Tool | How it works |
| :--- | :--- |
| Sealed Secrets (Bitnami) | Encrypt with the controller's public key (`kubeseal`); only the in-cluster controller can decrypt. The `SealedSecret` is safe to commit. |
| External Secrets Operator | Git stores an `ExternalSecret` reference; the operator fetches the value from AWS Secrets Manager, Vault, GCP Secret Manager, etc. |
| SOPS (with age/KMS) | Encrypts values inside YAML files; decrypted at sync time (Flux native, Argo CD via plugin/KSOPS). |

- **Protect `main`:** require PR reviews and CI checks (lint, `kubeconform`, policy checks) before merge.
- **Pin versions:** use immutable image tags or digests, never `latest`, so a commit always means the same thing.
- **No manual changes in production:** give humans read-only cluster access and keep `selfHeal` on, so drift is corrected automatically.
- **Use AppProjects** to restrict which repos and namespaces each team's Applications can touch.

## Hands-on: GitOps on my minikube cluster

Argo CD v3.5.4 watching `app/` in a Git repository on an in-cluster Gitea server (full walkthrough in [../README.md](../README.md#task-3-gitops)):

| GitOps idea | What I did | Result |
| :--- | :--- | :--- |
| Git as source of truth | pushed namespace + deployment (2 replicas) + service, created the Application | Synced / Healthy, 2 pods ([14](../screenshots/14-gitops-initial-sync.png)) |
| Continuous reconciliation (self-heal) | `kubectl scale --replicas=5`, `kubectl delete service` | replicas back to 2 within 0.4 s; Service recreated ([15](../screenshots/15-gitops-self-heal.png)) |
| Change through Git | commit `replicas: 3` + push | 3 pods, history entry for the commit ([16](../screenshots/16-gitops-commit-sync.png)) |
| Prune | `git rm app/service.yaml` | Service deleted from the cluster |
| Rollback | `git revert` of both commits | Service back, replicas 2, five revisions in Argo CD history ([17](../screenshots/17-gitops-revert-and-prune.png), [20](../screenshots/20-gitea-commit-history.png)) |


---

## Key takeaways

- GitOps = declarative desired state in Git + an in-cluster agent that pulls and continuously reconciles it (the four OpenGitOps principles).
- Git is the source of truth: every change is reviewed, auditable and reversible, and the cluster can be rebuilt from the repo.
- Reconciliation compares desired vs live state. `selfHeal` fixes drift and `prune` removes resources deleted from Git.
- Pull-based GitOps keeps cluster credentials inside the cluster and detects drift. Push-based CI deploys once and forgets.
- An Argo CD `Application` ties a repo/path/revision to a cluster/namespace, and rollback is a `git revert`, not a manual cluster change.
- Keep config separate from code, model environments with overlays or values files, and keep secrets out of plain Git (Sealed Secrets, External Secrets, SOPS).

---

## References

- OpenGitOps principles: https://opengitops.dev/
- Argo CD documentation: https://argo-cd.readthedocs.io/en/stable/
- Argo CD core concepts: https://argo-cd.readthedocs.io/en/stable/core_concepts/
- Argo CD Application specification: https://argo-cd.readthedocs.io/en/stable/user-guide/application-specification/
- Argo CD automated sync policy (prune, selfHeal): https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/
- Argo CD secret management: https://argo-cd.readthedocs.io/en/stable/operator-manual/secret-management/
- Kubernetes declarative object management: https://kubernetes.io/docs/tasks/manage-kubernetes-objects/declarative-config/
- Kubernetes imperative commands: https://kubernetes.io/docs/tasks/manage-kubernetes-objects/imperative-command/
- Kustomize in Kubernetes: https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/
- Kubernetes Secrets: https://kubernetes.io/docs/concepts/configuration/secret/
