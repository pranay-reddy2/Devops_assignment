# Session 11: Kubernetes Services

| Folder | Lab |
| :--- | :--- |
| [01-clusterip/](01-clusterip/README.md) | Internal VIP, DNS, port-forward |
| [02-nodeport/](02-nodeport/README.md) | Host-port exposure, minikube tunnel |
| [03-loadbalancer/](03-loadbalancer/README.md) | Cloud LB type, `minikube tunnel` |
| [04-externalname/](04-externalname/README.md) | DNS CNAME to an external host |
| [05-headless/](05-headless/README.md) | `clusterIP: None` + StatefulSet per-pod DNS |
| `deployment/`, `service/`, `dns-test/`, `troubleshooting/` | One backend, three service types, and a broken-selector drill (below) |

Every lab README ends with a **Lab Run Output** section containing the real terminal output from minikube v1.39.0 / Kubernetes v1.37.0 (docker driver, macOS).

---

## Lab: one backend, three Service types

![terminal screenshot](screenshots/backend-services-troubleshooting.png)


`deployment/backend-deployment.yaml` runs a tiny Python HTTP server on port `5000` with a `/healthz` route. The three manifests in `service/` all select `app: yatri-backend` and map service port `80` to `targetPort: 5000`.

```bash
kubectl apply -f deployment/backend-deployment.yaml
kubectl rollout status deploy/yatri-backend
kubectl get pods -l app=yatri-backend -L tier
kubectl apply -f service/clusterip.yaml -f service/nodeport.yaml -f service/loadbalancer.yaml
kubectl get svc -l app=yatri-backend
kubectl get endpoints -l app=yatri-backend
```
```text
deployment.apps/yatri-backend configured
Waiting for deployment "yatri-backend" rollout to finish: 1 out of 3 new replicas have been updated...
Waiting for deployment "yatri-backend" rollout to finish: 2 out of 3 new replicas have been updated...
Waiting for deployment "yatri-backend" rollout to finish: 1 old replicas are pending termination...
deployment "yatri-backend" successfully rolled out
NAME                            READY   STATUS        RESTARTS   AGE   TIER
yatri-backend-cbc55c649-jn5xp   1/1     Terminating   0          12m
yatri-backend-cbc55c649-mvss2   1/1     Terminating   0          12m
yatri-backend-cbc55c649-x6llx   1/1     Terminating   0          12m
yatri-backend-dc5888c55-b9tqx   1/1     Running       0          1s    api
yatri-backend-dc5888c55-fbqlz   1/1     Running       0          1s    api
yatri-backend-dc5888c55-kq2pr   1/1     Running       0          1s    api
service/yatri-backend-service created
service/yatri-backend-nodeport created
service/yatri-backend-lb created
NAME                     TYPE           CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE
yatri-backend-lb         LoadBalancer   10.103.182.129   <pending>     80:32361/TCP   0s
yatri-backend-nodeport   NodePort       10.98.29.108     <none>        80:30080/TCP   0s
yatri-backend-service    ClusterIP      10.105.37.90     <none>        80/TCP         0s
NAME                     ENDPOINTS                                               AGE
yatri-backend-lb         10.244.0.102:5000,10.244.0.103:5000,10.244.0.104:5000   0s
yatri-backend-nodeport   10.244.0.102:5000,10.244.0.103:5000,10.244.0.104:5000   0s
yatri-backend-service    10.244.0.102:5000,10.244.0.103:5000,10.244.0.104:5000   0s
```
Three Services, one set of pods: each Service independently resolves the same selector to the same three endpoints. (The `Terminating` pods are from the session 10 version of this Deployment; `kubectl apply` rolled it to the session 11 template.)

### Test with the diagnostic pod
```bash
kubectl apply -f dns-test/curl-test-pod.yaml
kubectl exec curl-test-pod -- curl -s http://yatri-backend-service
kubectl exec curl-test-pod -- curl -s http://yatri-backend-service/healthz
minikube ssh -- "curl -s http://localhost:30080/healthz"
```
```text
pod/curl-test-pod created
Backend v1.0.0 listening on port 5000
{"status":"healthy","service":"yatri-backend"}
{"status":"healthy","service":"yatri-backend"}
```

---

## Troubleshooting drill: empty endpoints

`troubleshooting/empty-endpoints.yaml` is a ClusterIP Service whose selector is `app: wrong-backend-name`. No pod carries that label.

```bash
kubectl apply -f troubleshooting/empty-endpoints.yaml
kubectl get svc broken-backend-service
kubectl get endpoints broken-backend-service
kubectl describe svc broken-backend-service | grep -E "Selector|Endpoints"
kubectl exec curl-test-pod -- curl -s --connect-timeout 3 http://broken-backend-service
```
```text
service/broken-backend-service created
NAME                     TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)   AGE
broken-backend-service   ClusterIP   10.104.145.147   <none>        80/TCP    0s
NAME                     ENDPOINTS   AGE
broken-backend-service   <none>      0s
Selector:                 app=wrong-backend-name
Endpoints:
command terminated with exit code 7
```

How to read it:
* The Service is created fine and gets a ClusterIP. The API server does not validate that a selector matches anything.
* `ENDPOINTS <none>` is the tell. A Service with no endpoints accepts the connection at the VIP and then has nowhere to send it, so curl fails with exit code 7 (connection refused).
* Confirm the mismatch by querying pods with the Service's selector:
```bash
kubectl get pods -l app=wrong-backend-name      # No resources found in default namespace.
kubectl get pods -l app=yatri-backend           # the 3 real pods
```
* Fix: make `spec.selector` match the pod template labels (`app: yatri-backend`), re-apply, and the endpoints populate immediately.

### Cleanup
```bash
kubectl delete -f troubleshooting/ -f dns-test/ -f service/
kubectl delete -f deployment/backend-deployment.yaml
```
