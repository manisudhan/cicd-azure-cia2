#!/usr/bin/env bash
# ===========================================================================
# Connects the Jenkins container to Docker Desktop's built-in Kubernetes, so
# the pipeline can run end to end with DEPLOY_TARGET=local and no Azure
# subscription.
#
#   bash infra/local-connect.sh
#
# Run it once after enabling Kubernetes in Docker Desktop, and again if you
# reset the cluster (the client certificate changes).
#
# What it does and why:
#   1. Copies the host kubeconfig into the Jenkins container's persistent volume.
#   2. Rewrites the API server address. The host kubeconfig points at
#      https://127.0.0.1:6443, which inside the container means the container
#      itself; host.docker.internal is the address of the host from a container.
#   3. Disables TLS verification for that cluster, because Docker Desktop's API
#      server certificate is issued for 127.0.0.1 / kubernetes.docker.internal
#      and not for host.docker.internal. This is a local development cluster on
#      the loopback interface; it is never used for the Azure target.
# ===========================================================================
set -euo pipefail

CONTAINER="${CONTAINER:-cicd-jenkins}"
CONTEXT="${CONTEXT:-docker-desktop}"
IN_CONTAINER_KUBECONFIG="/var/jenkins_home/.kube/config"

# ------------------------------------------------------------ host checks ----
if ! docker info >/dev/null 2>&1; then
    echo "ERROR: the Docker daemon is not reachable."
    echo "Start Docker Desktop from the Start menu, wait for the whale icon to"
    echo "stop animating, then run this script again."
    exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    echo "ERROR: the Jenkins container '$CONTAINER' is not running."
    echo "Start it with:  docker compose up -d --build"
    exit 1
fi

# Locate the host kubeconfig. USERPROFILE is set on Windows, HOME elsewhere.
HOST_KUBECONFIG="${KUBECONFIG_SRC:-${USERPROFILE:-$HOME}/.kube/config}"
if [ ! -f "$HOST_KUBECONFIG" ]; then
    echo "ERROR: no kubeconfig found at $HOST_KUBECONFIG"
    echo
    echo "Enable Kubernetes in Docker Desktop first:"
    echo "  Settings -> Kubernetes -> Enable Kubernetes -> Apply & Restart"
    echo "It takes a few minutes to download and start the control plane."
    exit 1
fi

if ! kubectl config get-contexts -o name 2>/dev/null | grep -qx "$CONTEXT"; then
    echo "ERROR: kubeconfig has no '$CONTEXT' context."
    echo "Enable Kubernetes in Docker Desktop (Settings -> Kubernetes)."
    echo "Contexts currently available:"
    kubectl config get-contexts -o name 2>/dev/null | sed 's/^/  /' || echo "  (none)"
    exit 1
fi

echo "Host cluster check:"
kubectl --context "$CONTEXT" get nodes -o wide

# -------------------------------------------------- install into container ---
echo
echo "Installing the kubeconfig into $CONTAINER:$IN_CONTAINER_KUBECONFIG"
docker exec "$CONTAINER" mkdir -p "$(dirname "$IN_CONTAINER_KUBECONFIG")"
docker cp "$HOST_KUBECONFIG" "$CONTAINER:$IN_CONTAINER_KUBECONFIG"

echo "Pointing it at the host and relaxing TLS for this local cluster only"
docker exec -e KUBECONFIG="$IN_CONTAINER_KUBECONFIG" "$CONTAINER" \
    kubectl config use-context "$CONTEXT"
docker exec -e KUBECONFIG="$IN_CONTAINER_KUBECONFIG" "$CONTAINER" \
    kubectl config set-cluster "$CONTEXT" --server="https://host.docker.internal:6443"
# A CA file and --insecure-skip-tls-verify cannot both be set, so drop the CA.
docker exec -e KUBECONFIG="$IN_CONTAINER_KUBECONFIG" "$CONTAINER" \
    kubectl config unset "clusters.${CONTEXT}.certificate-authority-data" >/dev/null 2>&1 || true
docker exec -e KUBECONFIG="$IN_CONTAINER_KUBECONFIG" "$CONTAINER" \
    kubectl config unset "clusters.${CONTEXT}.certificate-authority" >/dev/null 2>&1 || true
docker exec -e KUBECONFIG="$IN_CONTAINER_KUBECONFIG" "$CONTAINER" \
    kubectl config set-cluster "$CONTEXT" --insecure-skip-tls-verify=true

# ------------------------------------------------------------- verify --------
echo
echo "Verifying from inside the Jenkins container:"
docker exec "$CONTAINER" kubectl get nodes -o wide
echo
docker exec "$CONTAINER" kubectl version --output=yaml | grep -E 'gitVersion' | head -2

cat <<'DONE'

===========================================================================
 Jenkins can now reach Docker Desktop's Kubernetes.
===========================================================================
 Run the pipeline with DEPLOY_TARGET = local (the default).

 Stage 6 (push to ACR) is skipped: Docker Desktop's Kubernetes reads the
 Docker image store, so the image built in stage 5 is already visible to the
 cluster and the Deployment's imagePullPolicy: IfNotPresent uses it directly.

 Docker Desktop has no working LoadBalancer controller, so the Service keeps
 EXTERNAL-IP <pending>. That is expected: stage 8 smoke-tests the Service from
 inside the cluster instead. To open the app in a browser, run:

     kubectl port-forward -n cicd-demo svc/cicd-demo-app 8081:80

 then browse http://localhost:8081   (8080 is taken by Jenkins)
===========================================================================
DONE
