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

# Git Bash / MSYS on Windows rewrites any argument that looks like an absolute
# path. Azure resource ids and role-assignment scopes start with
# "/subscriptions/...", and without this they arrive as
# "C:/Program Files/Git/subscriptions/..." - which fails with the thoroughly
# unhelpful "(MissingSubscription) The request did not have a subscription".
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

# Pick a Python that actually RUNS, for the small amount of JSON parsing below.
# Testing with "command -v" alone is not enough on Windows: python3 there is
# often the Microsoft Store alias stub, which resolves fine but then prints
# "Python was not found" and exits non-zero when invoked.
PY_BIN=""
for candidate in python python3 py; do
    if command -v "$candidate" >/dev/null 2>&1 \
       && "$candidate" -c 'import json,sys' >/dev/null 2>&1; then
        PY_BIN="$candidate"
        break
    fi
done
if [ -z "$PY_BIN" ]; then
    echo "ERROR: no working Python found on PATH (tried python, python3, py)."
    echo "It is needed to parse the Azure CLI JSON output."
    exit 1
fi

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
echo "[1/5] Creating resource group $RESOURCE_GROUP"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

# --------------------------------------------------- 2. resource providers ---
# A new or newly renewed subscription often has these namespaces unregistered,
# and resource creation then fails with "MissingSubscriptionRegistration" -
# which looks nothing like the real cause. Registering is idempotent and only
# costs time the first time.
echo "[2/5] Registering the required resource providers"
for ns in Microsoft.ContainerRegistry Microsoft.ContainerService \
          Microsoft.Compute Microsoft.Network Microsoft.Storage \
          Microsoft.OperationalInsights Microsoft.Insights; do
    STATE=$(az provider show --namespace "$ns" --query registrationState -o tsv 2>/dev/null || echo Unknown)
    if [ "$STATE" = "Registered" ]; then
        echo "      $ns already registered"
    else
        echo "      $ns ($STATE) - registering, this can take a few minutes"
        az provider register --namespace "$ns" --wait --output none
        echo "      $ns registered"
    fi
done

# --------------------------------------------------------------- 3. ACR ------
echo "[3/5] Creating container registry $ACR_NAME (Basic)"
if az acr show --name "$ACR_NAME" --output none 2>/dev/null; then
    echo "      Registry $ACR_NAME already exists - reusing it"
elif ! ACR_ERROR=$(az acr create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$ACR_NAME" \
        --sku Basic \
        --output none 2>&1); then
    echo
    echo "ERROR: could not create the registry '$ACR_NAME'. Azure said:"
    printf '%s\n' "$ACR_ERROR" | sed 's/^/    /'
    echo
    case "$ACR_ERROR" in
        *AlreadyInUse*|*AlreadyExists*|*already*use*)
            echo "Registry names are globally unique across all of Azure, so this one"
            echo "is taken. Rerun with a different name, for example:"
            echo
            echo "    ACR_NAME=${ACR_NAME}ss bash infra/azure-setup.sh"
            echo
            echo "and set the same value for ACR_NAME and ACR_LOGIN_SERVER in"
            echo "Jenkinsfile, and for acr_login_server in ansible/deploy-app.yml."
            ;;
        *MissingSubscriptionRegistration*)
            echo "A resource provider is not registered on this subscription."
            echo "Step 2 of this script does that; if it was skipped, run:"
            echo "    az provider register --namespace Microsoft.ContainerRegistry --wait"
            ;;
    esac
    exit 1
fi
ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)

# --------------------------------------------------------------- 4. AKS ------
echo "[4/5] Creating AKS cluster $AKS_CLUSTER ($AKS_NODE_COUNT x $AKS_NODE_SIZE, ${AKS_DISK_SIZE}GB disk)"
if az aks show --resource-group "$RESOURCE_GROUP" --name "$AKS_CLUSTER" --output none 2>/dev/null; then
    echo "      Cluster $AKS_CLUSTER already exists - reusing it"
    # Check the AcrPull grant rather than re-attaching: "az aks update
    # --attach-acr" performs a full cluster update that takes several minutes
    # even when the grant is already in place, which is long enough to look
    # like a hang.
    KUBELET_ID=$(az aks show --resource-group "$RESOURCE_GROUP" --name "$AKS_CLUSTER" \
        --query identityProfile.kubeletidentity.objectId -o tsv 2>/dev/null || true)
    ACR_RESOURCE_ID=$(az acr show --name "$ACR_NAME" --query id -o tsv 2>/dev/null || true)
    if [ -n "$KUBELET_ID" ] && [ -n "$ACR_RESOURCE_ID" ] \
       && az role assignment list --assignee "$KUBELET_ID" --scope "$ACR_RESOURCE_ID" \
            --query "[?roleDefinitionName=='AcrPull'] | length(@)" -o tsv 2>/dev/null | grep -qv '^0$'; then
        echo "      AcrPull on $ACR_NAME already granted"
    else
        echo "      Granting AcrPull on $ACR_NAME (a few minutes)"
        az aks update \
            --resource-group "$RESOURCE_GROUP" \
            --name "$AKS_CLUSTER" \
            --attach-acr "$ACR_NAME" \
            --output none
        echo "      AcrPull granted"
    fi
else
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
fi

# ------------------------------------------------------ 5. service principal -
echo "[5/5] Creating service principal $SP_NAME for Jenkins"
RG_SCOPE="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP"
EXISTING_APP_ID=$(az ad sp list --display-name "$SP_NAME" --query "[0].appId" -o tsv 2>/dev/null || true)

if [ -n "${EXISTING_APP_ID:-}" ]; then
    # The principal survives a failed run, but its password is only ever shown
    # once, so there is nothing to recover - reset it to get a usable secret.
    echo "      Service principal already exists ($EXISTING_APP_ID) - resetting its password"
    SP_JSON=$(az ad sp credential reset --id "$EXISTING_APP_ID" --output json)
    SP_APP_ID="$EXISTING_APP_ID"
    SP_PASSWORD=$(echo "$SP_JSON" | "$PY_BIN" -c 'import sys,json; print(json.load(sys.stdin)["password"])')
    echo "      Granting Contributor on the resource group"
    az role assignment create \
        --assignee "$SP_APP_ID" \
        --role Contributor \
        --scope "$RG_SCOPE" \
        --output none 2>/dev/null || echo "      Contributor already assigned"
else
    SP_JSON=$(az ad sp create-for-rbac \
        --name "$SP_NAME" \
        --role Contributor \
        --scopes "$RG_SCOPE" \
        --output json)
    SP_APP_ID=$(echo "$SP_JSON" | "$PY_BIN" -c 'import sys,json; print(json.load(sys.stdin)["appId"])')
    SP_PASSWORD=$(echo "$SP_JSON" | "$PY_BIN" -c 'import sys,json; print(json.load(sys.stdin)["password"])')
fi

if [ -z "${SP_APP_ID:-}" ] || [ -z "${SP_PASSWORD:-}" ]; then
    echo "ERROR: could not obtain service principal credentials."
    exit 1
fi

# Also write the credentials to a git-ignored file so
# infra/jenkins-azure-credentials.sh can load them into Jenkins without the
# secret being retyped or pasted anywhere. Delete it once Jenkins has them.
SP_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/sp-credentials.json"
"$PY_BIN" - "$SP_FILE" "$SP_APP_ID" "$SP_PASSWORD" "$TENANT_ID" "$SUBSCRIPTION_ID" <<'PYEOF'
import json, os, stat, sys
path, app_id, password, tenant, subscription = sys.argv[1:6]
with open(path, "w", encoding="utf-8") as fh:
    json.dump({
        "appId": app_id,
        "password": password,
        "tenant": tenant,
        "subscriptionId": subscription,
    }, fh, indent=2)
os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
PYEOF
echo "      Credentials also written to sp-credentials.json (git-ignored)"

echo "      Granting AcrPush on the registry"
ACR_ID=$(az acr show --name "$ACR_NAME" --query id -o tsv)
az role assignment create \
    --assignee "$SP_APP_ID" \
    --role AcrPush \
    --scope "$ACR_ID" \
    --output none 2>/dev/null || echo "      AcrPush already assigned"

echo "      Granting Azure Kubernetes Service Cluster Admin on the cluster"
AKS_ID=$(az aks show --resource-group "$RESOURCE_GROUP" --name "$AKS_CLUSTER" --query id -o tsv)
az role assignment create \
    --assignee "$SP_APP_ID" \
    --role "Azure Kubernetes Service Cluster Admin Role" \
    --scope "$AKS_ID" \
    --output none 2>/dev/null || echo "      Cluster Admin already assigned"

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
