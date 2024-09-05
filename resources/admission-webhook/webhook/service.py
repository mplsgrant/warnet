from flask import Flask, jsonify, request

app = Flask(__name__)


with open("/etc/serviceaccounts/serviceaccounts") as f:
    restricted_service_accounts = [line.strip() for line in f if line.strip()]

with open("/etc/validImageHash/validImageHash") as f:
    valid_image_hash = f.read().strip()


@app.route("/validate", methods=["POST"])
def validate():
    request_data = request.get_json()

    # Extract pod spec from admission review request
    pod_spec = request_data["request"]["object"]["spec"]

    # Extract the ServiceAccount name
    service_account_name = pod_spec.get("serviceAccountName", "")
    print(f"got {service_account_name}")

    # Check if the ServiceAccount is in the allowed list
    if service_account_name not in restricted_service_accounts:
        return admission_response(True, "ServiceAccount not subject to validation")

    # Loop through the containers and validate their image hashes
    for container in pod_spec["containers"]:
        image = container["image"]
        if valid_image_hash not in image:
            return admission_response(False, "Invalid image hash", request_data)

    return admission_response(True, "Pod accepted", request_data)


def admission_response(allowed, message, request):
    response = {
        "response": {
            "uid": request.json["request"]["uid"],
            "allowed": allowed,
            "status": {"message": message},
        }
    }
    return jsonify(response)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=443, ssl_context=("/certs/tls.crt", "/certs/tls.key"))
