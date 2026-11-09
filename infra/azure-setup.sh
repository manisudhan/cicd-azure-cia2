#!/usr/bin/env bash
# ===========================================================================
# Creates every Azure resource the CI/CD pipeline needs:
#
#   1. Resource group                    rg-cicd-cia2
#   2. Azure Container Registry (ACR)    acrcicdcia2        - stores images
#   3. Azure Kubernetes Service (AKS)    aks-cicd-cia2      - runs the app
#   4. Ubuntu VM                         vm-jenkins         - runs Jenkins
#   5. Service principal                 sp-cicd-cia2       - used by Jenkins
#
# Prerequisites: Azure CLI installed and "az login" already done.
# Run from Git Bash, WSL, Linux or macOS:   bash infra/azure-setup.sh
#
# COST NOTE: AKS nodes, the VM and the Load Balancer are billed per hour.
# Run infra/azure-teardown.sh when the demo is finished, or stop the VM and
# scale the node pool to 0 between sessions.
# ===========================================================================
set -euo pipefail

# --------------------------------------------------------------- settings ----
LOCATION="${LOCATION:-centralindia}"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-cicd-cia2}"
# ACR names are globally unique, lowercase and alphanumeric only.
ACR_NAME="${ACR_NAME:-acrcicdcia2}"
AKS_CLUSTER="${AKS_CLUSTER:-aks-cicd-cia2}"
AKS_NODE_COUNT="${AKS_NODE_COUNT:-1}"
AKS_NODE_SIZE="${AKS_NODE_SIZE:-Standard_B2s}"
VM_NAME="${VM_NAME:-vm-jenkins}"
VM_SIZE="${VM_SIZE:-Standard_B2s}"
VM_IMAGE="${VM_IMAGE:-Ubuntu2404}"
VM_ADMIN="${VM_ADMIN:-azureuser}"
SP_NAME="${SP_NAME:-sp-cicd-cia2}"

echo "=== Azure CI/CD infrastructure setup ==="
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
echo "Subscription : $SUBSCRIPTION_ID"
echo "Location     : $LOCATION"
echo

# ------------------------------------------------------- 1. resource group ---
echo "[1/6] Creating resource group $RESOURCE_GROUP"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

# --------------------------------------------------------------- 2. ACR ------
echo "[2/6] Creating container registry $ACR_NAME (Basic)"
az acr create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$ACR_NAME" \
    --sku Basic \
    --output none
ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)

# --------------------------------------------------------------- 3. AKS ------
echo "[3/6] Creating AKS cluster $AKS_CLUSTER ($AKS_NODE_COUNT x $AKS_NODE_SIZE) - takes 5-10 minutes"
az aks create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AKS_CLUSTER" \
    --node-count "$AKS_NODE_COUNT" \
    --node-vm-size "$AKS_NODE_SIZE" \
    --tier free \
    --generate-ssh-keys \
    --attach-acr "$ACR_NAME" \
    --enable-managed-identity \
    --output none
echo "      AKS created and granted AcrPull on $ACR_NAME"

# --------------------------------------------------- 4. Jenkins VM + ports ---
echo "[4/6] Creating Jenkins VM $VM_NAME"
az vm create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$VM_NAME" \
    --image "$VM_IMAGE" \
    --size "$VM_SIZE" \
    --admin-username "$VM_ADMIN" \
    --generate-ssh-keys \
    --public-ip-sku Standard \
    --output none

VM_PUBLIC_IP=$(az vm show -d \
    --resource-group "$RESOURCE_GROUP" \
    --name "$VM_NAME" \
    --query publicIps -o tsv)

echo "      Opening port 8080 for the Jenkins web UI"
az vm open-port \
    --resource-group "$RESOURCE_GROUP" \
    --name "$VM_NAME" \
    --port 8080 \
    --priority 1001 \
    --output none

# ------------------------------------------------------ 5. service principal -
echo "[5/6] Creating service principal $SP_NAME for Jenkins"
SP_JSON=$(az ad sp create-for-rbac \
    --name "$SP_NAME" \
    --role Contributor \
    --scopes "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP" \
    --output json)

SP_APP_ID=$(echo "$SP_JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin)["appId"])')
SP_PASSWORD=$(echo "$SP_JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin)["password"])')

echo "      Granting AcrPush on the registry"
ACR_ID=$(az acr show --name "$ACR_NAME" --query id -o tsv)
az role assignment create \
    --assignee "$SP_APP_ID" \
    --role AcrPush \
    --scope "$ACR_ID" \
    --output none

echo "      Granting Azure Kubernetes Service Cluster Admin on the cluster"
AKS_ID=$(az aks show --resource-group "$RESOURCE_GROUP" --name "$AKS_CLUSTER" --query id -o tsv)
az role assignment create \
    --assignee "$SP_APP_ID" \
    --role "Azure Kubernetes Service Cluster Admin Role" \
    --scope "$AKS_ID" \
    --output none

# ------------------------------------------------------------- 6. summary ----
echo "[6/6] Done."
cat <<SUMMARY

===========================================================================
 AZURE RESOURCES CREATED
===========================================================================
 Resource group     : $RESOURCE_GROUP   (location $LOCATION)
 Container registry : $ACR_LOGIN_SERVER
 AKS cluster        : $AKS_CLUSTER
 Jenkins VM         : $VM_NAME
 Jenkins URL        : http://$VM_PUBLIC_IP:8080
 SSH to the VM      : ssh $VM_ADMIN@$VM_PUBLIC_IP

===========================================================================
 NEXT STEPS
===========================================================================
 1. Put the VM IP into ansible/inventory.ini, replacing VM_PUBLIC_IP, then:
        cd ansible && ansible-playbook -i inventory.ini jenkins-setup.yml

 2. Add these credentials in Jenkins (Manage Jenkins > Credentials > global):

        ID                     Kind               Value
        ---------------------- ------------------ --------------------------
        azure-sp               Username/Password  user: $SP_APP_ID
                                                  pass: (printed below)
        azure-tenant-id        Secret text        $TENANT_ID
        azure-subscription-id  Secret text        $SUBSCRIPTION_ID
        sonarcloud-token       Secret text        (from sonarcloud.io)

 3. Check that Jenkinsfile and ansible/deploy-app.yml use:
        ACR_NAME         = $ACR_NAME
        ACR_LOGIN_SERVER = $ACR_LOGIN_SERVER
        AKS_CLUSTER      = $AKS_CLUSTER

===========================================================================
 SERVICE PRINCIPAL SECRET - shown once, copy it into Jenkins now.
 Do NOT commit it to Git; Gitleaks will fail the build if you do.
===========================================================================
 appId    : $SP_APP_ID
 password : $SP_PASSWORD
 tenant   : $TENANT_ID
===========================================================================
SUMMARY
