#!/usr/bin/env bash
# ===========================================================================
# Creates the Azure resources the CI/CD pipeline needs.
#
#   1. Resource group                    rg-cicd-cia2
#   2. Azure Container Registry (ACR)    acrcicdcia2    - stores images
#   3. Azure Kubernetes Service (AKS)    aks-cicd-cia2  - runs the application
#   4. Service principal                 sp-cicd-cia2   - Jenkins' Azure identity
#
# Jenkins itself runs locally in Docker (see docker-compose.yml), so there is
# no build VM, no second public IP and no second managed disk in the cloud.
#
# Prerequisites: Azure CLI installed and "az login" already done.
# Run from Git Bash, WSL, Linux or macOS:   bash infra/azure-setup.sh
#
# APPROXIMATE COST (Central India, pay-as-you-go, Nov 2026):
#   AKS control plane (free tier)   0.00 USD
#   1 x Standard_B2s node           0.0448 USD/hr
#   Standard Load Balancer          0.025  USD/hr
#   1 x static public IP            0.005  USD/hr
#   32 GB StandardSSD node disk    ~0.003  USD/hr
#   ACR Basic                      ~0.007  USD/hr
#   ------------------------------------------------
#   while running                  ~0.085  USD/hr  (~2.05 USD/day)
#   while paused (azure-pause.sh)  ~0.015  USD/hr  (~0.35 USD/day)
#
# Run infra/azure-pause.sh between sessions and infra/azure-teardown.sh when
# the assignment is finished.
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
# 32 GB instead of the 128 GB default: the default is a Premium SSD costing
# roughly 20 USD/month, and it is billed even while the cluster is stopped.
AKS_DISK_SIZE="${AKS_DISK_SIZE:-32}"
SP_NAME="${SP_NAME:-sp-cicd-cia2}"

echo "=== Azure CI/CD infrastructure setup ==="
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
ACCOUNT_NAME=$(az account show --query name -o tsv)
echo "Subscription : $ACCOUNT_NAME ($SUBSCRIPTION_ID)"
echo "Location     : $LOCATION"
echo

# ------------------------------------------------------- 1. resource group ---
echo "[1/4] Creating resource group $RESOURCE_GROUP"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

# --------------------------------------------------------------- 2. ACR ------
echo "[2/4] Creating container registry $ACR_NAME (Basic)"
if ! az acr create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$ACR_NAME" \
        --sku Basic \
        --output none 2>/dev/null; then
    echo
    echo "ERROR: could not create the registry '$ACR_NAME'."
    echo "Registry names are globally unique across all of Azure, so this one is"
    echo "probably taken. Rerun with a different name, for example:"
    echo
    echo "    ACR_NAME=${ACR_NAME}ss bash infra/azure-setup.sh"
    echo
    echo "and set the same value for ACR_NAME and ACR_LOGIN_SERVER in Jenkinsfile"
    echo "and for acr_login_server in ansible/deploy-app.yml."
    exit 1
fi
ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)

# --------------------------------------------------------------- 3. AKS ------
echo "[3/4] Creating AKS cluster $AKS_CLUSTER ($AKS_NODE_COUNT x $AKS_NODE_SIZE, ${AKS_DISK_SIZE}GB disk)"
echo "      This takes 5-10 minutes."
az aks create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AKS_CLUSTER" \
    --node-count "$AKS_NODE_COUNT" \
    --node-vm-size "$AKS_NODE_SIZE" \
    --node-osdisk-size "$AKS_DISK_SIZE" \
    --tier free \
    --generate-ssh-keys \
    --attach-acr "$ACR_NAME" \
    --enable-managed-identity \
    --output none
echo "      Cluster created and granted AcrPull on $ACR_NAME"

# ------------------------------------------------------ 4. service principal -
echo "[4/4] Creating service principal $SP_NAME for Jenkins"
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

# ------------------------------------------------------------- 5. summary ----
cat <<SUMMARY

===========================================================================
 AZURE RESOURCES CREATED
===========================================================================
 Resource group     : $RESOURCE_GROUP   (location $LOCATION)
 Container registry : $ACR_LOGIN_SERVER
 AKS cluster        : $AKS_CLUSTER      ($AKS_NODE_COUNT x $AKS_NODE_SIZE)
 Jenkins            : runs locally - docker compose up -d --build

===========================================================================
 NEXT STEPS
===========================================================================
 1. Start Jenkins locally and open http://localhost:8080
        docker compose up -d --build

 2. Add these credentials in Jenkins (Manage Jenkins > Credentials > global):

        ID                     Kind               Value
        ---------------------- ------------------ --------------------------
        azure-sp               Username/Password  user: $SP_APP_ID
                                                  pass: (printed below)
        azure-tenant-id        Secret text        $TENANT_ID
        azure-subscription-id  Secret text        $SUBSCRIPTION_ID
        sonarcloud-token       Secret text        (from sonarcloud.io)

 3. Check that these match in Jenkinsfile and ansible/deploy-app.yml:
        ACR_NAME         = $ACR_NAME
        ACR_LOGIN_SERVER = $ACR_LOGIN_SERVER
        AKS_CLUSTER      = $AKS_CLUSTER

 4. Pause the cluster between sessions to protect your credits:
        bash infra/azure-pause.sh      # ~0.35 USD/day instead of ~2.05
        bash infra/azure-resume.sh

===========================================================================
 SERVICE PRINCIPAL SECRET - shown once, copy it into Jenkins now.
 Do NOT commit it to Git; Gitleaks will fail the build if you do.
===========================================================================
 appId    : $SP_APP_ID
 password : $SP_PASSWORD
 tenant   : $TENANT_ID
===========================================================================
SUMMARY
