#!/usr/bin/env bash
# ===========================================================================
# Deletes everything created by azure-setup.sh so the free credits stop being
# consumed. Deleting the resource group removes the AKS cluster, its node
# resource group, the registry, the VM, the disks, the public IPs and the
# Load Balancer in one operation.
#
#   bash infra/azure-teardown.sh
#
# To pause instead of delete (keeps the cluster and images, stops most cost):
#   az vm stop      --resource-group rg-cicd-cia2 --name vm-jenkins
#   az vm deallocate --resource-group rg-cicd-cia2 --name vm-jenkins
#   az aks stop     --resource-group rg-cicd-cia2 --name aks-cicd-cia2
# and to resume:
#   az aks start    --resource-group rg-cicd-cia2 --name aks-cicd-cia2
#   az vm start     --resource-group rg-cicd-cia2 --name vm-jenkins
# ===========================================================================
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-cicd-cia2}"
SP_NAME="${SP_NAME:-sp-cicd-cia2}"

echo "This will PERMANENTLY DELETE the resource group '$RESOURCE_GROUP'"
echo "and every resource inside it (AKS, ACR with all images, the Jenkins VM)."
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
