#!/usr/bin/env bash
# ===========================================================================
# Deletes everything created by azure-setup.sh so the free credits stop being
# consumed. Deleting the resource group removes the AKS cluster, its node
# resource group, the registry and every image in it, the node disk, the public
# IP and the Load Balancer in one operation.
#
#   bash infra/azure-teardown.sh
#
# To PAUSE instead of delete - keeps the cluster config and the images, and
# drops the cost from about 2.05 to about 0.35 USD/day - use:
#   bash infra/azure-pause.sh      and      bash infra/azure-resume.sh
#
# Jenkins runs locally, so it costs nothing in Azure. Stop it with:
#   docker compose down            (keeps the cicd_jenkins_home volume)
# ===========================================================================
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-cicd-cia2}"
SP_NAME="${SP_NAME:-sp-cicd-cia2}"

echo "This will PERMANENTLY DELETE the resource group '$RESOURCE_GROUP'"
echo "and every resource inside it (the AKS cluster and the ACR registry with"
echo "all its images). Your local Jenkins and its build history are untouched."
az resource list --resource-group "$RESOURCE_GROUP" \
    --query "[].{name:name, type:type}" --output table 2>/dev/null || {
        echo "Resource group '$RESOURCE_GROUP' not found - nothing to do."
        exit 0
    }

read -r -p "Type the resource group name to confirm: " CONFIRM
if [ "$CONFIRM" != "$RESOURCE_GROUP" ]; then
    echo "Names did not match. Aborted; nothing was deleted."
    exit 1
fi

echo "Deleting resource group $RESOURCE_GROUP ..."
az group delete --name "$RESOURCE_GROUP" --yes --no-wait
echo "Deletion started (running in the background)."

APP_ID=$(az ad sp list --display-name "$SP_NAME" --query "[0].appId" -o tsv 2>/dev/null || true)
if [ -n "${APP_ID:-}" ]; then
    echo "Deleting service principal $SP_NAME ($APP_ID)"
    az ad sp delete --id "$APP_ID"
fi

echo "Done. Check the portal in a few minutes to confirm the group is gone."
