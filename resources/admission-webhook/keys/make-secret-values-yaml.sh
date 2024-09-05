#!/bin/bash

# Prompt the user for information
read -p "Enter the service name (default: image-validator-service): " service_name
service_name=${service_name:-image-validator-service}

read -p "Enter the namespace (default: admission-control): " namespace
namespace=${namespace:-admission-control}

# Create the directory for key material if it doesn't exist
key_material_dir="key_material"
mkdir -p "$key_material_dir"

# Create the SAN configuration file (san.cnf) in the key_material directory
cat <<EOF > "${key_material_dir}/san.cnf"
[req]
distinguished_name = req_distinguished_name
req_extensions = req_ext
x509_extensions = v3_req
prompt = no
[req_distinguished_name]
CN = ${service_name}.${namespace}.svc
[req_ext]
subjectAltName = @alt_names
[v3_req]
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
[alt_names]
DNS.1 = ${service_name}
DNS.2 = ${service_name}.${namespace}
DNS.3 = ${service_name}.${namespace}.svc
EOF

echo "san.cnf has been generated in ${key_material_dir} with the following configuration:"
cat "${key_material_dir}/san.cnf"
echo ""

# Generate the TLS private key in the key_material directory
openssl genrsa -out "${key_material_dir}/tls.key" 2048
echo "tls.key has been generated in ${key_material_dir}."

# Generate the TLS certificate using the SAN configuration, outputting to the key_material directory
openssl req -x509 -new -nodes -key "${key_material_dir}/tls.key" -sha256 -days 365 -out "${key_material_dir}/tls.crt" -config "${key_material_dir}/san.cnf"
echo "tls.crt has been generated in ${key_material_dir}."

# Generate the base64-encoded CA bundle without line breaks (for ValidatingWebhookConfiguration)
ca_bundle=$(cat "${key_material_dir}/tls.crt" | base64 | tr -d '\n')
echo "Base64-encoded CA bundle generated."

# Create the secret-values.yaml file with the base64-encoded CA bundle
cat <<EOF > secret-values.yaml
# secret-values.yaml

# Base64-encoded TLS certificate and private key for Helm chart
tlsCert: |
  $(cat "${key_material_dir}/tls.crt" | base64 | tr -d '\n')

tlsKey: |
  $(cat "${key_material_dir}/tls.key" | base64 | tr -d '\n')

# Base64-encoded CA Bundle for ValidatingWebhookConfiguration
caBundle: |
  $ca_bundle
EOF

echo "secret-values.yaml has been generated with the following contents:"
cat secret-values.yaml
echo ""

echo "Done! The following files have been generated in the ${key_material_dir} directory:"
echo "- san.cnf (SAN configuration)"
echo "- tls.key (private key)"
echo "- tls.crt (certificate)"
echo "secret-values.yaml has been generated with the base64-encoded CA bundle."

