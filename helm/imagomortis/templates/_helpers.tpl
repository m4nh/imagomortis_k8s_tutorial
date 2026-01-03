{{/*
Expand the name of the chart.
*/}}
{{- define "imagomortis.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
*/}}
{{- define "imagomortis.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "imagomortis.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "imagomortis.labels" -}}
helm.sh/chart: {{ include "imagomortis.chart" . }}
{{ include "imagomortis.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: imagomortis
{{- end }}

{{/*
Selector labels
*/}}
{{- define "imagomortis.selectorLabels" -}}
app.kubernetes.io/name: {{ include "imagomortis.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the namespace
*/}}
{{- define "imagomortis.namespace" -}}
{{- if .Values.namespace.create }}
{{- .Values.namespace.name | default .Release.Namespace }}
{{- else }}
{{- .Release.Namespace }}
{{- end }}
{{- end }}

{{/*
Create the name of the config map
*/}}
{{- define "imagomortis.configMapName" -}}
{{- printf "%s-config" (include "imagomortis.fullname" .) }}
{{- end }}

{{/*
Create the name of the secret
*/}}
{{- define "imagomortis.secretName" -}}
{{- if .Values.database.existingSecret }}
{{- .Values.database.existingSecret }}
{{- else }}
{{- printf "%s-db-secret" (include "imagomortis.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Create postgres service name
*/}}
{{- define "imagomortis.postgresHost" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "%s-postgres" (include "imagomortis.fullname" .) }}
{{- else }}
{{- .Values.database.host }}
{{- end }}
{{- end }}

{{/*
Get image repository with registry prefix if specified
*/}}
{{- define "imagomortis.image" -}}
{{- $registry := .Values.imageRegistry | default "" -}}
{{- $repository := .repository -}}
{{- $tag := .tag | default "latest" -}}
{{- if $registry }}
{{- printf "%s/%s:%s" $registry $repository $tag }}
{{- else }}
{{- printf "%s:%s" $repository $tag }}
{{- end }}
{{- end }}

{{/*
Uploads PVC name
*/}}
{{- define "imagomortis.uploadsPvcName" -}}
{{- printf "%s-uploads" (include "imagomortis.fullname" .) }}
{{- end }}

{{/*
Postgres PVC name
*/}}
{{- define "imagomortis.postgresPvcName" -}}
{{- printf "%s-postgres-data" (include "imagomortis.fullname" .) }}
{{- end }}

{{/*
Scheduler shared PVC name
*/}}
{{- define "imagomortis.schedulerPvcName" -}}
{{- default "scheduler-shared-pvc" .Values.scheduler.persistence.pvcName }}
{{- end }}

{{/*
Loki PVC name
*/}}
{{- define "imagomortis.lokiPvcName" -}}
{{- printf "%s-loki-data" (include "imagomortis.fullname" .) }}
{{- end }}

{{/*
Scheduler service account name
*/}}
{{- define "imagomortis.schedulerServiceAccountName" -}}
{{- if .Values.scheduler.serviceAccount.create }}
{{- default (printf "%s-scheduler" (include "imagomortis.fullname" .)) .Values.scheduler.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.scheduler.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Fluent Bit service account name
*/}}
{{- define "imagomortis.fluentBitServiceAccountName" -}}
{{- if .Values.logging.fluentBit.serviceAccount.create }}
{{- default (printf "%s-fluent-bit" (include "imagomortis.fullname" .)) .Values.logging.fluentBit.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.logging.fluentBit.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Image task full image name
*/}}
{{- define "imagomortis.imageTaskImage" -}}
{{- $registry := .Values.imageRegistry | default "" -}}
{{- $repository := .Values.scheduler.imageTask.image.repository -}}
{{- $tag := .Values.scheduler.imageTask.image.tag | default "latest" -}}
{{- if $registry }}
{{- printf "%s/%s:%s" $registry $repository $tag }}
{{- else }}
{{- printf "%s:%s" $repository $tag }}
{{- end }}
{{- end }}
