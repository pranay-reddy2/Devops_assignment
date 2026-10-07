{{- define "spendwise.fullname" -}}{{ .Release.Name }}-spendwise{{- end }}

{{- define "spendwise.labels" -}}
app.kubernetes.io/name: spendwise
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{- define "spendwise.selector" -}}
app.kubernetes.io/name: spendwise
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "spendwise.secretName" -}}
{{- if .Values.postgres.existingSecret }}{{ .Values.postgres.existingSecret }}{{ else }}{{ include "spendwise.fullname" . }}-db{{ end }}
{{- end }}

{{- define "spendwise.image" -}}
{{ .repository }}:{{ .tag | default .appVersion }}
{{- end }}

{{- define "spendwise.podSecurity" -}}
securityContext:
  runAsNonRoot: true
  seccompProfile: {type: RuntimeDefault}
automountServiceAccountToken: false
{{- end }}

{{- define "spendwise.containerSecurity" -}}
securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities: {drop: ["ALL"]}
{{- end }}
