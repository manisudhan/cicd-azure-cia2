#!/usr/bin/env bash
# ===========================================================================
# Connects the Jenkins container to Docker Desktop's built-in Kubernetes, so
# the pipeline can run end to end with DEPLOY_TARGET=local and no Azure
# subscription.
#
#   bash infra/local-connect.sh
#
# Run it after enabling Kubernetes in Docker Desktop, and again whenever the
# Jenkins container is recreated or the Docker Desktop cluster is reset.
#
# What it does, and why each step is needed:
#
#   1. Attaches the Jenkins container to the "kind" Docker network.
#      Docker Desktop's Kubernetes is kind-based: the control plane runs as a
#      container on that network and publishes its API server on the HOST's
#      loopback only. A container therefore cannot reach it via
#      host.docker.internal (connection refused) - it has to join the network
#      and address the node directly.
#
#   2. Copies the host kubeconfig into the container's persistent volume and
#      rewrites only the server field, to the node's container name.
#      The CA data is deliberately preserved, and the node name is used rather
#      than its IP because that name is in the API server certificate's SAN
#      list - so TLS is still fully verified. Note the field is changed with
#      "kubectl config set", not "kubectl config set-cluster": the latter
#      rewrites every flag-backed field and would silently drop the CA data.
# ===========================================================================
set -euo pipefail

# Git Bash / MSYS on Windows rewrites absolute paths in command arguments, so
# "docker exec ... /var/jenkins_home" would arrive as
# "C:/Program Files/Git/var/jenkins_home". Every absolute path below is a path
# INSIDE the container, so that translation must be switched off.
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

CONTAINER="${CONTAINER:-cicd-jenkins}"
CONTEXT="${CONTEXT:-docker-desktop}"
KIND_NETWORK="${KIND_NETWORK:-kind}"
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

HOST_KUBECONFIG="${KUBECONFIG_SRC:-${USERPROFILE:-$HOME}/.kube/config}"
if [ ! -f "$HOST_KUBECONFIG" ]; then
    echo "ERROR: no kubeconfig found at $HOST_KUBECONFIG"
    echo
    echo "Enable Kubernetes in Docker Desktop first:"
    echo "  Settings -> Kubernetes -> Enable Kubernetes -> Apply & Restart"
    exit 1
fi

if ! kubectl --kubeconfig "$HOST_KUBECONFIG" config get-contexts -o name 2>/dev/null \
        | grep -qx "$CONTEXT"; then
    echo "ERROR: the kubeconfig has no '$CONTEXT' context."
    echo "Enable Kubernetes in Docker Desktop (Settings -> Kubernetes)."
    echo "Contexts currently available:"
    kubectl --kubeconfig "$HOST_KUBECONFIG" config get-contexts -o name 2>/dev/null \
        | sed 's/^/  /' || echo "  (none)"
    exit 1
fi

echo "Host cluster check:"
kubectl --kubeconfig "$HOST_KUBECONFIG" --context "$CONTEXT" get nodes

# Identify the control-plane node; its container name is also the DNS name on
# the kind network and a SAN in the API server certificate.
NODE_NAME=$(kubectl --kubeconfig "$HOST_KUBECONFIG" --context "$CONTEXT" \
    get nodes -o jsonpath='{.items[0].metadata.name}')
if [ -z "$NODE_NAME" ]; then
    echo "ERROR: could not determine the control-plane node name."
    exit 1
fi
echo "Control-plane node: $NODE_NAME"

# ------------------------------------------------- 1. join the kind network --
if ! docker network ls --format '{{.Name}}' | grep -qx "$KIND_NETWORK"; then
    echo "ERROR: Docker network '$KIND_NETWORK' does not exist."
    echo "That network is created when Docker Desktop's Kubernetes starts."
    exit 1
fi

if docker inspect -f '{{range $n, $_ := .NetworkSettings.Networks}}{{$n}} {{end}}' \
        "$CONTAINER" | grep -qw "$KIND_NETWORK"; then
    echo "Container already attached to the '$KIND_NETWORK' network."
else
    echo "Attaching $CONTAINER to the '$KIND_NETWORK' network"
    docker network connect "$KIND_NETWORK" "$CONTAINER"
fi

# ------------------------------------------- 2. install and retarget config --
echo "Installing the kubeconfig into $CONTAINER:$IN_CONTAINER_KUBECONFIG"
docker exec "$CONTAINER" mkdir -p "$(dirname "$IN_CONTAINER_KUBECONFIG")"
docker cp "$HOST_KUBECONFIG" "$CONTAINER:$IN_CONTAINER_KUBECONFIG"

docker exec "$CONTAINER" kubectl config use-context "$CONTEXT"
# Only the server field changes; the CA stays, so TLS remains verified.
docker exec "$CONTAINER" kubectl config set \
    "clusters.${CONTEXT}.server" "https://${NODE_NAME}:6443"

# ------------------------------------------------------------- 3. verify -----
echo
echo "Verifying from inside the Jenkins container (full TLS verification):"
docker exec "$CONTAINER" kubectl get nodes -o wide

cat <<DONE

===========================================================================
 Jenkins can now reach Docker Desktop's Kubernetes.
===========================================================================
 Run the pipeline with DEPLOY_TARGET = local (the default).

 Stage 6 (push to ACR) is skipped: Docker Desktop's Kubernetes reads the
 Docker image store, so the image built in stage 5 is already visible to the
 cluster and the Deployment's imagePullPolicy: IfNotPresent uses it directly.

 After a successful build the application is browsable at:

     http://localhost

 Docker Desktop's cloud-provider-kind publishes the LoadBalancer Service on the
 host's port 80. If something else already holds port 80, the Service will stay
 EXTERNAL-IP <pending>; use a port-forward in that case:

     kubectl port-forward -n cicd-demo svc/cicd-demo-app 8081:80

 Re-run this script if you recreate the Jenkins container (docker compose up
 --force-recreate) or reset the Docker Desktop cluster: the network attachment
 and the kubeconfig live in the container, not in the image.
===========================================================================
DONE
