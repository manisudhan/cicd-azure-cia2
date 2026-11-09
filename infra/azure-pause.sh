#!/usr/bin/env bash
# ===========================================================================
# Pauses the Azure resources between work sessions so the free credits last.
#
#   bash infra/azure-pause.sh
#
# Stopping the AKS cluster deallocates the node, which is the largest hourly
# charge. The registry, the 32 GB node disk and the Load Balancer's public IP
# keep their (small) charges so the images and the cluster configuration
# survive - roughly 0.35 USD/day paused versus 2.05 USD/day running.
#
# Note: the Kubernetes Service and its public IP are deleted along with the
# node pool state, so azure-resume.sh re-runs the deployment to recreate them.
# The next pipeline run does this automatically anyway.
#
# Jenkins runs locally, so stop it separately with:  docker compose stop
# ===========================================================================
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-cicd-cia2}"
AKS_CLUSTER="${AKS_CLUSTER:-aks-cicd-cia2}"

STATE=$(az aks show --resource-group "$RESOURCE_GROUP" --name "$AKS_CLUSTER" \
            --query powerState.code -o tsv 2>/dev/null || echo "NotFound")

case "$STATE" in
    NotFound)
        echo "Cluster '$AKS_CLUSTER' not found in '$RESOURCE_GROUP' - nothing to pause."
        exit 0
        ;;
    Stopped)
        echo "Cluster '$AKS_CLUSTER' is already stopped."
        ;;
    *)
        echo "Stopping AKS cluster '$AKS_CLUSTER' (currently $STATE). Takes 2-5 minutes."
        az aks stop --resource-group "$RESOURCE_GROUP" --name "$AKS_CLUSTER" --output none
        echo "Stopped."
        ;;
esac

echo
echo "Paused. Still billing (small): ACR Basic, the node OS disk, the public IP."
echo "Resume with: bash infra/azure-resume.sh"
echo "Also stop the local Jenkins if you are done: docker compose stop"
