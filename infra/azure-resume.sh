#!/usr/bin/env bash
# ===========================================================================
# Brings the paused Azure resources back up before a work session or the demo.
#
#   bash infra/azure-resume.sh
#
# Starts the AKS cluster and waits for the node to register. The application
# itself is redeployed by the next Jenkins run; to bring it back without a
# build, run the Ansible deploy playbook with the tag already in ACR.
# ===========================================================================
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-cicd-cia2}"
AKS_CLUSTER="${AKS_CLUSTER:-aks-cicd-cia2}"
K8S_NAMESPACE="${K8S_NAMESPACE:-cicd-demo}"

STATE=$(az aks show --resource-group "$RESOURCE_GROUP" --name "$AKS_CLUSTER" \
            --query powerState.code -o tsv 2>/dev/null || echo "NotFound")

if [ "$STATE" = "NotFound" ]; then
    echo "Cluster '$AKS_CLUSTER' not found. Run infra/azure-setup.sh first."
    exit 1
fi

if [ "$STATE" = "Stopped" ]; then
    echo "Starting AKS cluster '$AKS_CLUSTER'. Takes 3-5 minutes."
    az aks start --resource-group "$RESOURCE_GROUP" --name "$AKS_CLUSTER" --output none
else
    echo "Cluster '$AKS_CLUSTER' is already $STATE."
fi

echo "Fetching cluster credentials"
az aks get-credentials \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AKS_CLUSTER" \
    --admin --overwrite-existing

echo "Waiting for the node to become Ready"
kubectl wait --for=condition=Ready nodes --all --timeout=300s

echo
kubectl get nodes -o wide
echo
if kubectl get namespace "$K8S_NAMESPACE" >/dev/null 2>&1; then
    kubectl -n "$K8S_NAMESPACE" get deployment,pods,svc -o wide || true
    echo
    echo "If the Service has no EXTERNAL-IP yet, Azure is still creating the"
    echo "Load Balancer - give it 2-5 minutes, or just trigger a Jenkins build."
else
    echo "Namespace '$K8S_NAMESPACE' does not exist yet."
    echo "Trigger a Jenkins build, or deploy an image already in ACR with:"
    echo "  ansible-playbook ansible/deploy-app.yml -i ansible/inventory.ini \\"
    echo "      -e image_tag=latest -e build_number=manual -e commit_sha=manual"
fi

echo
echo "Remember to start Jenkins too: docker compose up -d"
