# Idea
Deploy an Authenticating Web Hook that prevents users from spawning any pods unless those pods have containers matching a sepcific hash.

# Secrets
The web hook requires secrets. There is a keys folder with a script that generates key material. Copy the secret-values.yaml file and place it next to the regular values.yaml file.

Git should ignore this secret-values.yaml file.

# Helm install...

helm install wargame-helm-chart ./wargame-helm-chart --values secret-values.yaml --namespace admission-control --create-namespace

# Things that are broken
## Connection refused
$ kubectl get events -n admission-control

Error creating: Internal error occurred: failed calling webhook "pod-image-hash-check.admission-control.svc": failed to call webhook: Post "https://image-validator-service.admission-control.svc:443/validate?timeout=10s": dial tcp 10.97.69.224:443: connect: connection refused

