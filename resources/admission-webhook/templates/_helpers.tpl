{{/*
Helper to create namespace names.
*/}}
{{- define "namespaceName" -}}
wargame-{{ . }}
{{- end }}

{{/*
Helper to create service account names.
*/}}
{{- define "serviceAccountName" -}}
sa-{{ . }}
{{- end }}
