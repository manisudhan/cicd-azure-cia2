#!/usr/bin/env bash
# Renders the Kubernetes manifest templates in this directory.
#
# The Jenkins pipeline calls this script, and it can also be run by hand for a
# manual deployment or to inspect exactly what will be sent to the cluster.
#
# Usage:
#   ACR_LOGIN_SERVER=myacr.azurecr.io IMAGE_TAG=12-a1b2c3d ./render.sh
#   kubectl apply -f rendered/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${OUT_DIR:-$SCRIPT_DIR/rendered}"

# Values the pipeline supplies; the defaults keep a manual run working.
export ACR_LOGIN_SERVER="${ACR_LOGIN_SERVER:?set ACR_LOGIN_SERVER, e.g. myacr.azurecr.io}"
export IMAGE_NAME="${IMAGE_NAME:-cicd-demo-app}"
export IMAGE_TAG="${IMAGE_TAG:-latest}"
export IMAGE="${IMAGE:-$ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG}"
export BUILD_NUMBER="${BUILD_NUMBER:-manual}"
export COMMIT_SHA="${COMMIT_SHA:-manual}"
export RELEASE_MESSAGE="${RELEASE_MESSAGE:-Deployed to Azure Kubernetes Service by Jenkins}"

# Only these names are substituted, so nothing else in the YAML is touched.
VARS='${IMAGE} ${IMAGE_TAG} ${BUILD_NUMBER} ${COMMIT_SHA} ${RELEASE_MESSAGE}'

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

for template in "$SCRIPT_DIR"/*.yaml; do
    envsubst "$VARS" < "$template" > "$OUT_DIR/$(basename "$template")"
done

echo "Rendered $(ls -1 "$OUT_DIR" | wc -l) manifest(s) into $OUT_DIR"
echo "  image : $IMAGE"
echo "  build : $BUILD_NUMBER (commit $COMMIT_SHA)"
