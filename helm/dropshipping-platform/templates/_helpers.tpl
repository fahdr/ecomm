{{/*
===========================================================================
  Dropshipping Platform — Helm Template Helpers
===========================================================================
  Reusable template functions for names, labels, selectors, images, and
  environment variable blocks shared across all Kubernetes manifests.
===========================================================================
*/}}

{{/*
Chart name, truncated to 63 chars (Kubernetes name limit).
*/}}
{{- define "dropshipping.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Fully qualified app name: <release>-<chart>, truncated to 63 chars.
If release name already contains chart name, skip duplication.
*/}}
{{- define "dropshipping.fullname" -}}
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
Chart label value: "<name>-<version>"
*/}}
{{- define "dropshipping.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Target namespace. Uses the override from values or falls back to release namespace.
*/}}
{{- define "dropshipping.namespace" -}}
{{- if .Values.namespace.name }}
{{- .Values.namespace.name }}
{{- else }}
{{- .Release.Namespace }}
{{- end }}
{{- end }}

{{/*
Common labels applied to every resource.
*/}}
{{- define "dropshipping.labels" -}}
helm.sh/chart: {{ include "dropshipping.chart" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: dropshipping-platform
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}

{{/*
Component labels. Call with dict "root" . "component" "core-backend".
*/}}
{{- define "dropshipping.componentLabels" -}}
{{ include "dropshipping.labels" .root }}
app.kubernetes.io/name: {{ .component }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
{{- end }}

{{/*
Selector labels for a component. Used in matchLabels for deployments/services.
*/}}
{{- define "dropshipping.selectorLabels" -}}
app.kubernetes.io/name: {{ .component }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
{{- end }}

{{/*
Resolve an image reference. Call with dict "root" . "repo" "" "defaultRepo" "core-backend" "tag" ""
If repo is empty, falls back to global.imageRegistry/defaultRepo.
If tag is empty, falls back to global.imageTag.
*/}}
{{- define "dropshipping.image" -}}
{{- $registry := .root.Values.global.imageRegistry -}}
{{- $repo := .repo -}}
{{- $tag := .tag -}}
{{- if not $repo -}}
  {{- $repo = printf "%s/%s" $registry .defaultRepo -}}
{{- end -}}
{{- if not $tag -}}
  {{- $tag = .root.Values.global.imageTag -}}
{{- end -}}
{{- printf "%s:%s" $repo $tag -}}
{{- end }}

{{/*
Image pull secrets block. Renders imagePullSecrets list if configured.
*/}}
{{- define "dropshipping.imagePullSecrets" -}}
{{- if .Values.global.imagePullSecrets }}
imagePullSecrets:
{{- range .Values.global.imagePullSecrets }}
  - name: {{ .name }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Service account name. Falls back to fullname if not explicitly set.
*/}}
{{- define "dropshipping.serviceAccountName" -}}
{{- if .Values.serviceAccount.name }}
{{- .Values.serviceAccount.name }}
{{- else }}
{{- include "dropshipping.fullname" . }}
{{- end }}
{{- end }}

{{/*
PostgreSQL DSN for asyncpg (used by FastAPI backends).
*/}}
{{- define "dropshipping.databaseUrl" -}}
postgresql+asyncpg://{{ .Values.global.postgresql.user }}:{{ .Values.global.postgresql.password }}@{{ .Values.global.postgresql.host }}:{{ .Values.global.postgresql.port }}/{{ .Values.global.postgresql.database }}
{{- end }}

{{/*
PostgreSQL DSN for psycopg2 (used by Celery workers and Alembic).
*/}}
{{- define "dropshipping.databaseUrlSync" -}}
postgresql+psycopg2://{{ .Values.global.postgresql.user }}:{{ .Values.global.postgresql.password }}@{{ .Values.global.postgresql.host }}:{{ .Values.global.postgresql.port }}/{{ .Values.global.postgresql.database }}
{{- end }}

{{/*
Redis URL. Call with dict "root" . "db" "0".
*/}}
{{- define "dropshipping.redisUrl" -}}
redis://{{ .root.Values.global.redis.host }}:{{ .root.Values.global.redis.port }}/{{ .db }}
{{- end }}

{{/*
Celery broker URL (always Redis DB 1).
*/}}
{{- define "dropshipping.celeryBrokerUrl" -}}
redis://{{ .Values.global.redis.host }}:{{ .Values.global.redis.port }}/1
{{- end }}

{{/*
Celery result backend URL (always Redis DB 2).
*/}}
{{- define "dropshipping.celeryResultBackend" -}}
redis://{{ .Values.global.redis.host }}:{{ .Values.global.redis.port }}/2
{{- end }}

{{/*
LLM Gateway internal URL.
*/}}
{{- define "dropshipping.llmGatewayUrl" -}}
http://{{ include "dropshipping.fullname" . }}-gateway:8200
{{- end }}

{{/*
Common backend environment variables block. Renders the shared env vars
that every backend pod needs (DB, Redis, JWT, Stripe, etc.).
Call from a container spec's env: section.
*/}}
{{- define "dropshipping.backendEnv" -}}
- name: DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: {{ include "dropshipping.fullname" .root }}-secrets
      key: database-url
- name: DATABASE_URL_SYNC
  valueFrom:
    secretKeyRef:
      name: {{ include "dropshipping.fullname" .root }}-secrets
      key: database-url-sync
- name: REDIS_URL
  value: {{ include "dropshipping.redisUrl" (dict "root" .root "db" (default "0" .redisDb)) }}
- name: CELERY_BROKER_URL
  value: {{ include "dropshipping.celeryBrokerUrl" .root }}
- name: CELERY_RESULT_BACKEND
  value: {{ include "dropshipping.celeryResultBackend" .root }}
- name: JWT_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "dropshipping.fullname" .root }}-secrets
      key: jwt-secret-key
- name: JWT_ALGORITHM
  value: {{ .root.Values.global.secrets.jwtAlgorithm | quote }}
- name: JWT_ACCESS_TOKEN_EXPIRE_MINUTES
  value: {{ .root.Values.global.secrets.jwtAccessTokenExpireMinutes | quote }}
- name: STRIPE_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "dropshipping.fullname" .root }}-secrets
      key: stripe-secret-key
- name: STRIPE_WEBHOOK_SECRET
  valueFrom:
    secretKeyRef:
      name: {{ include "dropshipping.fullname" .root }}-secrets
      key: stripe-webhook-secret
- name: STRIPE_FREE_PRICE_ID
  value: {{ .root.Values.global.secrets.stripeFreePrice | quote }}
- name: STRIPE_PRO_PRICE_ID
  value: {{ .root.Values.global.secrets.stripeProPrice | quote }}
- name: STRIPE_ENTERPRISE_PRICE_ID
  value: {{ .root.Values.global.secrets.stripeEnterprisePrice | quote }}
- name: LLM_GATEWAY_URL
  value: {{ include "dropshipping.llmGatewayUrl" .root }}
- name: LLM_GATEWAY_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "dropshipping.fullname" .root }}-secrets
      key: llm-gateway-key
- name: PLATFORM_WEBHOOK_SECRET
  valueFrom:
    secretKeyRef:
      name: {{ include "dropshipping.fullname" .root }}-secrets
      key: platform-webhook-secret
- name: SENTRY_DSN
  value: {{ .root.Values.global.secrets.sentryDsn | quote }}
{{- end }}

{{/*
Standard liveness probe for Python/FastAPI backends.
*/}}
{{- define "dropshipping.livenessProbe" -}}
livenessProbe:
  httpGet:
    path: /health
    port: http
  initialDelaySeconds: 30
  periodSeconds: 15
  timeoutSeconds: 5
  failureThreshold: 3
{{- end }}

{{/*
Standard readiness probe for Python/FastAPI backends.
*/}}
{{- define "dropshipping.readinessProbe" -}}
readinessProbe:
  httpGet:
    path: /health
    port: http
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
{{- end }}

{{/*
Standard liveness probe for Next.js frontends.
*/}}
{{- define "dropshipping.frontendLivenessProbe" -}}
livenessProbe:
  httpGet:
    path: /
    port: http
  initialDelaySeconds: 20
  periodSeconds: 15
  timeoutSeconds: 5
  failureThreshold: 3
{{- end }}

{{/*
Standard readiness probe for Next.js frontends.
*/}}
{{- define "dropshipping.frontendReadinessProbe" -}}
readinessProbe:
  httpGet:
    path: /
    port: http
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
{{- end }}
