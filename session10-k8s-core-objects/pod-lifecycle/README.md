# Kubernetes Pod Lifecycle Lab

This lab demonstrates the major Pod lifecycle situations using small, independent YAML files.

## Recommended

1. Running
2. Pending
3. Init container
4. Readiness
5. Liveness
6. Startup probe
7. Succeeded
8. Failed
9. CrashLoopBackOff
10. ImagePullBackOff
11. Multi-container Pod
12. Graceful termination

## Start the live watch

Run this in Terminal 1:

```bash
kubectl get pods -w
```

Then apply examples from another terminal.

## Basic commands

Create:
```bash
kubectl apply -f 01-running.yaml
```

Watch:
```bash
kubectl get pods -w
```

Detailed lifecycle:
```bash
kubectl describe pod lifecycle-running
```

Logs:
```bash
kubectl logs lifecycle-running
```

Container state:
```bash
kubectl get pod lifecycle-running -o jsonpath='{.status.containerStatuses[0].state}'
```

Full YAML/status:
```bash
kubectl get pod lifecycle-running -o yaml
```

Delete:
```bash
kubectl delete pod lifecycle-running
```

## Important note about STATUS

`kubectl get pods` may display values such as:

- Pending
- Running
- Completed
- Error
- CrashLoopBackOff
- ImagePullBackOff
- ContainerCreating
- Terminating

These are not all official Pod phases.

Official Pod phases are:

- Pending
- Running
- Succeeded
- Failed
- Unknown

Container states are:

- Waiting
- Running
- Terminated

## 1. Running

```bash
kubectl apply -f 01-running.yaml
kubectl get pod lifecycle-running
```

Expected:
```text
NAME                READY   STATUS    RESTARTS
lifecycle-running   1/1     Running   0
```

## 2. Pending

```bash
kubectl apply -f 02-pending.yaml
kubectl get pod lifecycle-pending
kubectl describe pod lifecycle-pending
```

This requests impossible CPU/memory resources, so on a normal small cluster it should remain Pending.

The exact message depends on the cluster.

## 3. Succeeded

```bash
kubectl apply -f 03-succeeded.yaml
kubectl get pod lifecycle-succeeded
kubectl logs lifecycle-succeeded
```

Expected status:
```text
Completed
```

Pod phase:
```text
Succeeded
```

## 4. Failed

```bash
kubectl apply -f 04-failed.yaml
kubectl get pod lifecycle-failed
kubectl logs lifecycle-failed
```

Expected status:
```text
Error
```

Pod phase:
```text
Failed
```

## 5. CrashLoopBackOff

```bash
kubectl apply -f 05-crashloopbackoff.yaml
kubectl get pod lifecycle-crashloop -w
```

The container starts, exits with code 1, gets restarted, and keeps failing.

Inspect:
```bash
kubectl describe pod lifecycle-crashloop
kubectl logs lifecycle-crashloop
kubectl logs lifecycle-crashloop --previous
```

## 6. ImagePullBackOff

```bash
kubectl apply -f 06-imagepullbackoff.yaml
kubectl get pod lifecycle-image-error
kubectl describe pod lifecycle-image-error
```

The image tag intentionally does not exist.

## 7. Readiness probe

```bash
kubectl apply -f 07-readiness.yaml
kubectl get pod lifecycle-readiness -w
```

Inspect:
```bash
kubectl describe pod lifecycle-readiness
```

Important teaching point:

```text
Running != Ready
```

Readiness answers:
"Should this Pod receive traffic?"

## 8. Liveness probe

```bash
kubectl apply -f 08-liveness.yaml
kubectl get pod lifecycle-liveness -w
```

The health file is removed after 20 seconds. The liveness probe then fails and Kubernetes restarts the container.

Watch:
```bash
kubectl get pod lifecycle-liveness -w
```

Look at:
```text
RESTARTS
```

## 9. Startup probe

```bash
kubectl apply -f 09-startup.yaml
kubectl get pod lifecycle-startup -w
```

The application intentionally takes 30 seconds to start.

The startup probe gives it time before normal health management takes over.

## 10. Init container

```bash
kubectl apply -f 10-init-container.yaml
kubectl get pod lifecycle-init -w
```

Inspect:
```bash
kubectl describe pod lifecycle-init
kubectl logs lifecycle-init -c setup
```

Teaching point:

```text
Init container runs first
        ↓
Init completes
        ↓
Main container starts
```

## 11. Multi-container Pod

```bash
kubectl apply -f 11-multi-container.yaml
kubectl get pod lifecycle-multi-container
```

Expected:
```text
2/2
```

View individual container logs:
```bash
kubectl logs lifecycle-multi-container -c app
kubectl logs lifecycle-multi-container -c sidecar
```

Teaching point:

```text
One Pod
  ├── app container
  └── sidecar container
```

## 12. Graceful termination

```bash
kubectl apply -f 12-termination.yaml
kubectl get pod lifecycle-termination
```

Then in another terminal:

```bash
kubectl delete pod lifecycle-termination
```

Watch:
```bash
kubectl get pod lifecycle-termination -w
```

The process handles SIGTERM, performs cleanup, and exits.

## Lab Run Output (minikube v1.39.0, Kubernetes v1.37.0, 1 node, 8 GiB allocatable)

![terminal screenshot](../screenshots/pod-lifecycle.png)


All 12 manifests were applied back to back with `kubectl get pods -w` running in another terminal. State 40 seconds later:

```text
NAME                        READY   STATUS             RESTARTS      AGE
lifecycle-crashloop         0/1     Error              2 (34s ago)   41s
lifecycle-failed            0/1     Error              0             41s
lifecycle-image-error       0/1     ImagePullBackOff   0             41s
lifecycle-init              1/1     Running            0             41s
lifecycle-liveness          1/1     Running            0             41s
lifecycle-multi-container   2/2     Running            0             41s
lifecycle-pending           0/1     Pending            0             41s
lifecycle-readiness         1/1     Running            0             41s
lifecycle-running           1/1     Running            0             41s
lifecycle-startup           1/1     Running            0             41s
lifecycle-succeeded         0/1     Completed          0             41s
lifecycle-termination       1/1     Running            0             40s
```

### 1. Running
```text
NAME                READY   STATUS    RESTARTS   AGE
lifecycle-running   1/1     Running   0          58s
{"running":{"startedAt":"2026-09-17T06:33:40Z"}}
```
Container state `running`, pod phase `Running`, READY `1/1`.

### 2. Pending
```text
NAME                READY   STATUS    RESTARTS   AGE
lifecycle-pending   0/1     Pending   0          58s
Warning  FailedScheduling  default-scheduler  0/1 nodes are available: 1 Insufficient memory. preemption: 0/1 nodes are available: 1 Preemption is not helpful for scheduling.
allocatable memory: 8124516Ki
```
The pod requests `9Gi`; the node has about 7.7 GiB allocatable. It never leaves `Pending` and never gets a node or an IP. `describe` is the only way to see why.

### 3. Succeeded
```text
NAME                  READY   STATUS      RESTARTS   AGE
lifecycle-succeeded   0/1     Completed   0          58s
Task started
Task completed successfully
phase: Succeeded
```
`kubectl get` says `Completed`, the real phase is `Succeeded`.

### 4. Failed
```text
NAME               READY   STATUS   RESTARTS   AGE
lifecycle-failed   0/1     Error    0          58s
Task started
Task failed
phase: Failed, exitCode: 1
```
`kubectl get` says `Error`, the real phase is `Failed`. Same script as #3, only the exit code differs. `restartPolicy: Never` is why RESTARTS stays 0.

### 5. CrashLoopBackOff
From the watch (this is the loop, with the back-off delay growing 0s, 10s, 20s...):
```text
lifecycle-crashloop   1/1     Running            0               1s
lifecycle-crashloop   0/1     Error              0               4s
lifecycle-crashloop   1/1     Running            1 (0s ago)      4s
lifecycle-crashloop   0/1     Error              1 (4s ago)      8s
lifecycle-crashloop   0/1     CrashLoopBackOff   1 (12s ago)     19s
lifecycle-crashloop   1/1     Running            2 (12s ago)     19s
lifecycle-crashloop   0/1     Error              2 (16s ago)     23s
lifecycle-crashloop   0/1     CrashLoopBackOff   2 (25s ago)     47s
lifecycle-crashloop   1/1     Running            3 (25s ago)     47s
lifecycle-crashloop   0/1     Error              3 (28s ago)     50s
```
```text
$ kubectl logs lifecycle-crashloop
Application started
Application crashed
$ kubectl describe pod lifecycle-crashloop   (events)
Normal   Started    kubelet  Container started                                   (x4)
Warning  BackOff    kubelet  Back-off restarting failed container crashing-app   (x3)
```
Default `restartPolicy: Always` is the difference from #4: same exit 1, but here kubelet keeps restarting with exponential back-off (capped at 5 minutes).

### 6. ImagePullBackOff
```text
lifecycle-image-error   0/1     ErrImagePull       0     19s
lifecycle-image-error   0/1     ImagePullBackOff   0     31s
lifecycle-image-error   0/1     ErrImagePull       0     45s
lifecycle-image-error   0/1     ImagePullBackOff   0     59s
```
```text
Warning  Failed   kubelet  Failed to pull image "jakwehrgkaejw:kahsdfgkhj": failed to pull and unpack image "docker.io/library/jakwehrgkaejw:kahsdfgkhj": failed to resolve reference "docker.io/library/jakwehrgkaejw:kahsdfgkhj": pull access denied, repository does not exist or may require authorization: server message: insufficient_scope: authorization failed
Warning  Failed   kubelet  Error: ErrImagePull
Normal   BackOff  kubelet  Back-off pulling image "jakwehrgkaejw:kahsdfgkhj"
```
`ErrImagePull` is the attempt, `ImagePullBackOff` is the wait between attempts. The container never starts, so RESTARTS stays 0 and phase stays `Pending`. Note the message says "denied" for a missing image too; Docker Hub does not reveal whether a private repo exists.

### 7. Readiness probe
```text
lifecycle-readiness   0/1     Running   0     20s     <- Running but NOT ready
lifecycle-readiness   1/1     Running   0     25s     <- first probe passed at initialDelay 5s
```
```text
Readiness:      http-get http://:80/ delay=5s timeout=1s period=5s successThreshold=1 failureThreshold=3
Ready           True
ContainersReady True
```
The 5 seconds of `0/1 Running` is the teaching point: the pod would be excluded from Service endpoints during that window.

### 8. Liveness probe
```text
lifecycle-liveness   1/1     Running   0             1s
lifecycle-liveness   1/1     Running   1 (0s ago)    61s    <- restarted by kubelet
```
```text
App started
Warning  Unhealthy  kubelet  Liveness probe failed:                                       (x2)
Normal   Killing    kubelet  Container app failed liveness probe, will be restarted
Normal   Started    kubelet  Container started                                            (x2)
```
Timeline: file removed at 20s, `failureThreshold: 2` x `periodSeconds: 5` = two failures, container killed and restarted around 30s. RESTARTS went to 1 and the pod stayed `Running` throughout (liveness restarts the container, not the pod).

### 9. Startup probe
```text
lifecycle-startup   0/1     Running   0     1s
lifecycle-startup   1/1     Running   0     36s
```
```text
Application starting...
Application started
Warning  Unhealthy  kubelet  Startup probe failed:   (x6 over 68s)
```
Six startup-probe failures and zero restarts: that is the whole point. The budget is `failureThreshold: 10` x `periodSeconds: 5` = 50s, and the app needed 30s. With a liveness probe instead, six failures would have restarted the container.

### 10. Init container
```text
lifecycle-init   0/1     Init:0/1          0     0s
lifecycle-init   0/1     PodInitializing   0     11s
lifecycle-init   1/1     Running           0     23s
```
```text
$ kubectl logs lifecycle-init -c setup
Init container running
Init complete
Normal  Created  kubelet  spec.initContainers{setup}: Container created   (t=0s)
Normal  Started  kubelet  spec.initContainers{setup}: Container started
Normal  Created  kubelet  spec.containers{app}: Container created         (t=22s)
Normal  Started  kubelet  spec.containers{app}: Container started
```
`Init:0/1` means 0 of 1 init containers done. The nginx container was not even created until the init container exited.

### 11. Multi-container
```text
NAME                        READY   STATUS    RESTARTS   AGE
lifecycle-multi-container   2/2     Running   0          74s
$ kubectl logs lifecycle-multi-container -c sidecar --tail=2
Sidecar is running
Sidecar is running
$ kubectl logs lifecycle-multi-container -c app --tail=2
2026/09/17 06:33:44 [notice] 1#1: start worker process 37
2026/09/17 06:33:44 [notice] 1#1: start worker process 38
```
`-c` is mandatory for logs once a pod has more than one container.

### 12. Graceful termination
`kubectl logs -f` was attached before running `kubectl delete pod lifecycle-termination`:
```text
Application running
SIGTERM received; cleaning up...
Cleanup complete
```
```text
lifecycle-termination   1/1     Terminating   0     80s
lifecycle-termination   0/1     Completed     0     90s
pod "lifecycle-termination" deleted from default namespace
delete returned after 10s
```
The trap handler ran for its full 10s `sleep` and the pod exited with `Completed`, not `Error`, because the handler did `exit 0`. If the handler had taken longer than `terminationGracePeriodSeconds: 20`, kubelet would have sent SIGKILL.

### Cleanup output
```text
$ kubectl delete -f .
pod "lifecycle-running" deleted from default namespace
... (12 pods)
```

---

## Cleanup everything

```bash
kubectl delete -f .
```

If you want to remove only these lab Pods:

```bash
kubectl delete pod lifecycle-running lifecycle-pending lifecycle-succeeded lifecycle-failed lifecycle-crashloop lifecycle-image-error lifecycle-readiness lifecycle-liveness lifecycle-startup lifecycle-init lifecycle-multi-container lifecycle-termination
```

## Suggested teaching flow

Use:

```bash
kubectl get pods -w
```

while applying each YAML.

For every example ask students:

1. What state/status do you see?
2. Is the container running?
3. Is the Pod ready?
4. Did the container restart?
5. Why did this happen?
6. Which command would you use to debug it?

The three most useful debugging commands are:

```bash
kubectl get pod <pod>
kubectl describe pod <pod>
kubectl logs <pod>
```
