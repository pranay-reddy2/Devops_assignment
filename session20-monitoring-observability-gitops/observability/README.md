# Session 20 – Observability

**Author:** Pranay Reddy
**Course:** SST DevOps & Cloud [SWE]
**Session:** 20, Task 2 (Observability)

This task explains the three observability pillars, how they connect, why observability matters beyond plain monitoring, the common tools, and how observability is set up on Kubernetes. It builds on the instructor folders [01-monitoring-vs-observability](../01-monitoring-vs-observability/README.md), [02-metrics-logs-traces](../02-metrics-logs-traces/README.md), [03-prometheus](../03-prometheus/README.md) and [04-grafana](../04-grafana/README.md).

```text
Metrics = Numbers   -> HOW MUCH / HOW OFTEN
Logs    = Events    -> WHAT happened
Traces  = Journey   -> WHERE the request spent time
```

---

## Pillar 1: Metrics

**What it is:** a numeric measurement sampled over time. Each sample is `(metric name + labels, timestamp, value)`. Metrics are cheap to store, easy to aggregate and the natural input for dashboards and alerts.

**Data shape:** a time series. The metric name plus its set of labels identifies one series.

```text
http_requests_total{method="GET",code="200"} 1027
^ metric name       ^ labels (dimensions)     ^ value
```

Over time Prometheus stores:

```text
10:00:00  1003
10:00:15  1011
10:00:30  1027
```

**Prometheus metric types:**

| Type | Behaviour | Example |
| :--- | :--- | :--- |
| Counter | Only goes up (resets to 0 on restart). Use `rate()` on it. | `http_requests_total` |
| Gauge | Goes up and down. | `node_memory_MemAvailable_bytes`, queue length |
| Histogram | Counts observations into buckets (`_bucket`, `_sum`, `_count`). | `http_request_duration_seconds_bucket{le="0.5"}` |
| Summary | Client-side quantiles. Cannot be aggregated across instances. | `go_gc_duration_seconds{quantile="0.99"}` |

**Watch out for cardinality:** every unique label combination is a new series. Labels like `user_id` or `request_id` can create millions of series and overload Prometheus. Keep labels bounded (method, status code, route, pod).

---

## Pillar 2: Logs

**What it is:** a timestamped record of a discrete event, written by an application or system component. Logs carry the detail that metrics throw away (error messages, IDs, stack traces).

**Data shape:** unstructured text or, better, structured key-value records (JSON).

Unstructured (hard to query):

```text
2026-09-28 18:20:05 ERROR Database timeout for order 8812
```

Structured JSON (each field can be filtered and indexed):

```json
{"ts":"2026-09-28T18:20:05.412Z","level":"error","service":"order-service","pod":"order-7d9c4-x2k8p","msg":"database timeout","order_id":"8812","duration_ms":3000,"trace_id":"4bf92f3577b34da6a3ce929d0e0e4736","span_id":"00f067aa0ba902b7"}
```

In Kubernetes, containers should write logs to stdout/stderr. The container runtime stores them on the node under `/var/log/containers/`, which is where `kubectl logs` and log collectors read from.

---

## Pillar 3: Traces

**What it is:** the full path of one request as it moves through multiple services. A trace is made of **spans**. Each span is one unit of work (an HTTP call, a DB query) with a start time, duration, attributes and a parent span.

**Data shape:** a tree of spans sharing one `trace_id`.

| Field | Meaning |
| :--- | :--- |
| `trace_id` | Same for every span in one request |
| `span_id` | Unique per span |
| `parent_span_id` | Links child span to its caller |
| `name`, `start`, `duration` | What ran and how long |
| `attributes` | `http.method`, `db.statement`, `k8s.pod.name`, ... |

Context is passed between services in HTTP headers (W3C `traceparent`), so each service knows which trace it belongs to.

**Example trace as a waterfall** (trace_id `4bf92f35...`, total 820 ms):

```text
Span                         0ms      200ms     400ms     600ms     800ms
---------------------------  |---------|---------|---------|---------|
GET /checkout   (gateway)    [=========================================] 820ms
  order-service /orders        [======================================]  790ms
    user-service /users/42       [====]                                  80ms
    payment-service /charge             [======]                         120ms
    postgres SELECT orders                      [=====================]  600ms  <- slow
```

The waterfall shows at a glance that the database query is the bottleneck, which no single metric would have told us.

---

## How the Pillars Correlate

The pillars are most useful when you can jump from one to another during an incident:

```text
 ALERT (metric)            DRILL DOWN (trace)          ROOT CAUSE (log)
 p99 latency > 1s   --->   exemplar trace_id   --->    logs filtered by trace_id
 on /checkout              4bf92f35...                  "database timeout order 8812"
```

- **trace_id in logs:** the app (or OpenTelemetry SDK) injects the current `trace_id` and `span_id` into every log line. In Grafana, a Loki log line with a `trace_id` field can link straight to the trace in Tempo/Jaeger, and a span can link back to its logs.
- **Exemplars:** a histogram sample can carry an example `trace_id` alongside it. In a Grafana latency panel, the dots on the graph are exemplars: clicking a slow one opens that exact trace.

```text
http_request_duration_seconds_bucket{le="1.0"} 1532 # {trace_id="4bf92f35..."} 0.82
```

- **Shared labels:** using the same resource labels everywhere (`service`, `namespace`, `pod`) lets you pivot from a pod's CPU graph to that pod's logs.

---

## Why Observability Is Required

Monitoring answers "is it healthy?" using checks defined in advance. Observability answers "why is it behaving this way?" for questions nobody thought to ask in advance.

| | Monitoring | Observability |
| :--- | :--- | :--- |
| Problem type | Known-unknowns: failures we predicted (disk full, pod down) | Unknown-unknowns: new failure modes we did not predict |
| Approach | Predefined dashboards and threshold alerts | Explore high-detail telemetry, slice by any dimension |
| Output | "Error rate is 6%" | "Errors are only on v2 pods calling payment-service in zone b" |

Why it matters more now:

- **Microservices:** one user request may touch 10+ services, queues and databases. A failure in one shows up as latency in another. Without traces and correlated logs, teams guess.
- **Dynamic infrastructure:** pods are created and destroyed constantly, IPs change, and logs disappear with the pod unless collected.
- **MTTD (Mean Time To Detect):** good metrics and alerts reduce the time between a fault starting and someone knowing about it.
- **MTTR (Mean Time To Resolve/Recover):** traces and correlated logs reduce the time from "we know it is broken" to "we know why and have fixed it".
- **SLOs:** service level objectives (for example "99.9% of requests under 300 ms") need accurate metrics to measure error budgets.

Monitoring is a subset of observability. Production systems need both.

---

## Common Tools

| Tool | Pillar | Role |
| :--- | :--- | :--- |
| Prometheus | Metrics | Pull-based scraper and time-series database, PromQL queries, alert rules |
| Grafana | All (visualisation) | Dashboards over Prometheus, Loki, Tempo, Jaeger, Elasticsearch, CloudWatch |
| Alertmanager | Metrics (alerting) | Receives alerts from Prometheus, groups, deduplicates, silences, routes to Slack/PagerDuty/email |
| Loki | Logs | Log store that indexes only labels (not full text), queried with LogQL, cheap to run |
| ELK / OpenSearch | Logs | Elasticsearch/OpenSearch full-text log indexing + Logstash + Kibana/OpenSearch Dashboards |
| Fluent Bit | Logs (collection) | Lightweight log forwarder, usually a DaemonSet, ships to Loki/Elasticsearch/CloudWatch |
| Jaeger | Traces | Distributed tracing backend and UI (CNCF graduated) |
| Tempo | Traces | Grafana's trace store, uses object storage, looks up traces by ID |
| OpenTelemetry | All (instrumentation) | Vendor-neutral SDKs, APIs, OTLP protocol and Collector to generate and ship metrics, logs and traces |
| Datadog / New Relic | All (SaaS) | Commercial all-in-one platforms: agents, APM, dashboards, alerting |
| AWS CloudWatch | All (AWS) | Metrics, Logs, alarms, and X-Ray/Application Signals for traces on AWS |

---

## Kubernetes Observability

### Built-in signals

| Component | What it provides |
| :--- | :--- |
| `kubectl logs <pod>` | Container stdout/stderr (`-f` follow, `--previous` for the crashed container, `-c` for a specific container) |
| `kubectl get events` / `kubectl describe` | Scheduling failures, image pull errors, OOMKilled, probe failures |
| cAdvisor (inside kubelet) | Per-container CPU, memory, network, filesystem usage (`container_*` metrics) |
| metrics-server | Short-term CPU/memory from kubelets, serves the Metrics API used by `kubectl top` and the HPA. No history, no PromQL. |
| `kubectl top nodes` / `kubectl top pods` | Current CPU/memory from metrics-server |

### metrics-server vs Prometheus

| | metrics-server | Prometheus |
| :--- | :--- | :--- |
| Purpose | Autoscaling (HPA/VPA) and `kubectl top` | Full monitoring, dashboards, alerting |
| Data | CPU and memory only, latest value | Any metric, with history |
| Storage | In memory | On-disk TSDB with retention |
| Query | Metrics API | PromQL |

They are complementary: most clusters run both.

### Prometheus stack on Kubernetes

- **kube-prometheus-stack** (Helm chart): installs the Prometheus Operator, Prometheus, Alertmanager, Grafana, node-exporter, kube-state-metrics, and default dashboards and alert rules.
- **node-exporter** (DaemonSet): node-level OS metrics (CPU, memory, disk, network) as `node_*`.
- **kube-state-metrics** (Deployment): state of Kubernetes objects from the API server, e.g. `kube_deployment_status_replicas_available`, `kube_pod_container_status_restarts_total`.
- **cAdvisor**: scraped via the kubelet for `container_cpu_usage_seconds_total`, `container_memory_working_set_bytes`.
- **ServiceMonitor / PodMonitor** (CRDs from the Prometheus Operator): instead of editing `prometheus.yml`, you declare which Services to scrape:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: session20-app
  labels:
    release: kube-prometheus-stack   # must match the Prometheus serviceMonitorSelector
spec:
  selector:
    matchLabels:
      app: session20-app
  endpoints:
    - port: http
      path: /metrics
      interval: 30s
```

### Logs and traces on Kubernetes

- **Log collection via DaemonSet:** Fluent Bit (or Promtail/Grafana Alloy, Vector) runs one pod per node, tails `/var/log/containers/*.log`, adds Kubernetes metadata (namespace, pod, labels) and ships to Loki, Elasticsearch/OpenSearch or CloudWatch.
- **OpenTelemetry Collector:** receives OTLP traces/metrics/logs from instrumented apps, processes them (batching, adding `k8s.*` attributes), and exports to Tempo/Jaeger, Prometheus, Loki or a SaaS backend. Usually deployed as a DaemonSet (agent) plus a Deployment (gateway).

### Architecture

```text
+-------------------------- Kubernetes cluster ---------------------------+
|                                                                         |
|  Each node                                                              |
|  +-------------------------------------------------------------------+  |
|  |  app pods  --(/metrics)--+   --(stdout logs)--+  --(OTLP spans)--+ |  |
|  |  kubelet/cAdvisor -------+                    |                  | |  |
|  |  node-exporter (DS) -----+   Fluent Bit (DS) -+  OTel Coll. (DS)-+ |  |
|  +--------------------------|--------------------|------------------|-+  |
|                    scrape   |              ship  |           export |    |
|                             v                    v                  v    |
|  kube-state-metrics --> +------------+       +------+          +-------+ |
|  ServiceMonitors ---->  | Prometheus |       | Loki |          | Tempo | |
|                         +--+------+--+       +--+---+          +---+---+ |
|                alert rules |      | PromQL      | LogQL            | TraceQL
|                            v      |             |                  |     |
|                 +--------------+  +------+------+--------+---------+     |
|                 | Alertmanager |                v                         |
|                 +------+-------+         +-------------+                  |
|                        |                 |   Grafana   |  dashboards      |
|                        v                 +-------------+                  |
|            Slack / email / PagerDuty                                    |
|                                                                         |
|  metrics-server (separate path) --> Metrics API --> kubectl top, HPA    |
+-------------------------------------------------------------------------+
```

---

## Golden Signals, RED and USE

Three well-known checklists for what to measure:

| Method | Applies to | Signals |
| :--- | :--- | :--- |
| Four Golden Signals (Google SRE book) | User-facing services | **Latency**, **Traffic**, **Errors**, **Saturation** |
| RED (Tom Wilkie) | Request-driven services / microservices | **Rate** (req/s), **Errors** (failed req/s), **Duration** (latency distribution) |
| USE (Brendan Gregg) | Resources: CPU, memory, disk, network | **Utilisation** (% busy), **Saturation** (queued work), **Errors** (error count) |

Rule of thumb: RED for every service, USE for every node and resource, Golden Signals for the user-facing SLOs.

---

## PromQL Cheat Sheet

| Query | What it returns |
| :--- | :--- |
| `up` | 1 if the target was scraped successfully, 0 if down |
| `up == 0` | Only targets that are down (useful as an alert) |
| `rate(http_requests_total[5m])` | Per-second request rate averaged over 5 minutes (use on counters) |
| `sum by (code) (rate(http_requests_total[5m]))` | Request rate grouped by status code |
| `sum(rate(http_requests_total{code=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))` | Error ratio (RED: Errors) |
| `histogram_quantile(0.99, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))` | p99 latency (RED: Duration) |
| `sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="session20", container!=""}[5m]))` | CPU cores used per pod |
| `sum by (pod) (container_memory_working_set_bytes{namespace="session20", container!=""})` | Memory per pod (the value the OOM killer looks at) |
| `increase(kube_pod_container_status_restarts_total[1h]) > 0` | Containers that restarted in the last hour |

Notes:
- `rate()` only makes sense on counters. Never `rate()` a gauge.
- Always `sum by (le)` before `histogram_quantile`, otherwise the buckets do not line up.
- `container!=""` drops the pod-level cgroup series so values are not double-counted.

## Hands-on: the pillars on my minikube cluster

Captured while doing Task 1 (full walkthrough in [../README.md](../README.md#task-1-monitoring)):

| Pillar | What I collected | Evidence |
| :--- | :--- | :--- |
| Metrics | podinfo `/metrics` scraped by Prometheus via a ServiceMonitor; RED queries (rate by status, p95 latency) and cAdvisor CPU/memory | [02-metrics-cpu-memory-health.png](../screenshots/02-metrics-cpu-memory-health.png), [04-grafana-podinfo-dashboard.png](../screenshots/04-grafana-podinfo-dashboard.png) |
| Logs | podinfo structured JSON request logs and the busybox demo's plain-text logs via `kubectl logs` | [03-logs.png](../screenshots/03-logs.png) |
| Traces | not deployed in this lab (no OpenTelemetry collector/Tempo); covered conceptually above | - |
| Alerts (built on metrics) | `PodinfoDown` pending → firing → Alertmanager when the app was scaled to 0 | [09-alert-firing-terminal.png](../screenshots/09-alert-firing-terminal.png), [11-alertmanager-alert.png](../screenshots/11-alertmanager-alert.png) |

The same incident seen through two pillars: the dashboard's *Healthy targets* stat went from 2 to 0 (metrics) at the moment the pods stopped logging (logs), and the alert fired 75 s later because the rule waits `for: 30s` and is evaluated every 30 s.


---

## Key takeaways

- Metrics tell you something is wrong, traces tell you where, and logs tell you why. Each pillar answers a different question.
- Shared IDs (`trace_id` in logs, exemplars on histograms, consistent `service`/`pod` labels) let you move between pillars quickly during an incident, which lowers MTTR.
- Monitoring covers known failure modes. Observability is needed for unknown ones, especially in microservices on Kubernetes.
- On Kubernetes, metrics-server is for `kubectl top` and autoscaling. kube-prometheus-stack (Prometheus, node-exporter, kube-state-metrics, ServiceMonitors, Grafana, Alertmanager) is for real monitoring.
- Logs are collected by a node-level DaemonSet, and OpenTelemetry gives one vendor-neutral way to produce and ship all three signals.
- Use RED for services and USE for resources so dashboards and alerts cover the right signals.

---

## References

- Prometheus overview: https://prometheus.io/docs/introduction/overview/
- Prometheus metric types: https://prometheus.io/docs/concepts/metric_types/
- PromQL basics: https://prometheus.io/docs/prometheus/latest/querying/basics/
- Alertmanager: https://prometheus.io/docs/alerting/latest/alertmanager/
- Grafana documentation: https://grafana.com/docs/grafana/latest/
- Grafana Loki: https://grafana.com/docs/loki/latest/
- Grafana Tempo: https://grafana.com/docs/tempo/latest/
- OpenTelemetry concepts (signals, traces, logs): https://opentelemetry.io/docs/concepts/signals/
- OpenTelemetry Collector: https://opentelemetry.io/docs/collector/
- Kubernetes resource metrics pipeline: https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/
- Kubernetes logging architecture: https://kubernetes.io/docs/concepts/cluster-administration/logging/
- kube-state-metrics: https://kubernetes.io/docs/concepts/cluster-administration/kube-state-metrics/
