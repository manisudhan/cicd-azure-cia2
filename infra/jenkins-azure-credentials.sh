#!/usr/bin/env bash
# ===========================================================================
# Loads the credentials the pipeline needs into the Jenkins credential store,
# reading the Azure values straight out of sp-credentials.json (written by
# infra/azure-setup.sh and git-ignored). Nothing has to be retyped, and no
# secret is ever echoed to the terminal.
#
#   bash infra/jenkins-azure-credentials.sh
#   SONAR_TOKEN=sqp_xxxx bash infra/jenkins-azure-credentials.sh   # also Sonar
#
# Creates or updates:
#   azure-sp               Username/Password  (appId / password)
#   azure-tenant-id        Secret text
#   azure-subscription-id  Secret text
#   sonarcloud-token       Secret text        (only when SONAR_TOKEN is set)
#
# Values are base64-encoded on the way into the Groovy script so that special
# characters in a generated password cannot break the quoting.
# ===========================================================================
set -euo pipefail

JENKINS_URL="${JENKINS_URL:-http://localhost:8090}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SP_FILE="${SP_FILE:-$PROJECT_ROOT/sp-credentials.json}"

COOKIE_JAR="$(mktemp)"
GROOVY_FILE="$(mktemp)"
trap 'rm -f "$COOKIE_JAR" "$GROOVY_FILE"' EXIT

PY_BIN="$(command -v python3 || command -v python || true)"
if [ -z "$PY_BIN" ]; then
    echo "ERROR: python3 or python must be on PATH."
    exit 1
fi

# ------------------------------------------------------- Jenkins credentials --
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$PROJECT_ROOT/.env"
    set +a
fi
JENKINS_ADMIN_USER="${JENKINS_ADMIN_USER:-admin}"
if [ -z "${JENKINS_ADMIN_PASSWORD:-}" ]; then
    echo "ERROR: JENKINS_ADMIN_PASSWORD is not set (see .env.example)."
    exit 1
fi
AUTH="${JENKINS_ADMIN_USER}:${JENKINS_ADMIN_PASSWORD}"

# ------------------------------------------------------------ Azure values ----
if [ ! -f "$SP_FILE" ]; then
    echo "ERROR: $SP_FILE not found."
    echo "Run infra/azure-setup.sh first; it writes that file."
    exit 1
fi

b64() { printf '%s' "$1" | base64 | tr -d '\n'; }

read_field() {
    "$PY_BIN" -c "import json,sys; print(json.load(open(sys.argv[1], encoding='utf-8'))['$1'])" "$SP_FILE"
}

APP_ID=$(read_field appId)
APP_PASSWORD=$(read_field password)
TENANT_ID=$(read_field tenant)
SUBSCRIPTION_ID=$(read_field subscriptionId)

if [ -z "$APP_ID" ] || [ -z "$APP_PASSWORD" ]; then
    echo "ERROR: $SP_FILE is missing appId or password."
    exit 1
fi

# ---------------------------------------------------------- build the script --
{
    cat <<'GROOVY_HEAD'
import com.cloudbees.plugins.credentials.CredentialsScope
import com.cloudbees.plugins.credentials.SystemCredentialsProvider
import com.cloudbees.plugins.credentials.domains.Domain
import com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl
import hudson.util.Secret
import org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl

def decode = { String s -> new String(s.decodeBase64(), 'UTF-8') }
def store = SystemCredentialsProvider.getInstance().getStore()
def domain = Domain.global()

def upsert = { creds ->
    def existing = store.getCredentials(domain).find { it.id == creds.id }
    if (existing != null) {
        store.updateCredentials(domain, existing, creds)
        println "updated: ${creds.id}"
    } else {
        store.addCredentials(domain, creds)
        println "added:   ${creds.id}"
    }
}
GROOVY_HEAD

    echo "def appId = decode('$(b64 "$APP_ID")')"
    echo "def appSecret = decode('$(b64 "$APP_PASSWORD")')"
    echo "def tenantId = decode('$(b64 "$TENANT_ID")')"
    echo "def subscriptionId = decode('$(b64 "$SUBSCRIPTION_ID")')"

    cat <<'GROOVY_AZURE'
upsert(new UsernamePasswordCredentialsImpl(
        CredentialsScope.GLOBAL, 'azure-sp',
        'Azure service principal (appId / password)', appId, appSecret))
upsert(new StringCredentialsImpl(
        CredentialsScope.GLOBAL, 'azure-tenant-id',
        'Azure Entra ID tenant id', Secret.fromString(tenantId)))
upsert(new StringCredentialsImpl(
        CredentialsScope.GLOBAL, 'azure-subscription-id',
        'Azure subscription id', Secret.fromString(subscriptionId)))
GROOVY_AZURE

    if [ -n "${SONAR_TOKEN:-}" ]; then
        echo "def sonarToken = decode('$(b64 "$SONAR_TOKEN")')"
        cat <<'GROOVY_SONAR'
upsert(new StringCredentialsImpl(
        CredentialsScope.GLOBAL, 'sonarcloud-token',
        'SonarQube Cloud analysis token', Secret.fromString(sonarToken)))
GROOVY_SONAR
    fi

    cat <<'GROOVY_TAIL'
println '---'
println 'credential ids now present: ' +
        store.getCredentials(Domain.global()).collect { it.id }.sort().join(', ')
GROOVY_TAIL
} > "$GROOVY_FILE"

# ------------------------------------------------------------------- apply ----
echo "Authenticating to Jenkins at $JENKINS_URL"
WHOAMI=$(curl -fsS -u "$AUTH" -c "$COOKIE_JAR" "$JENKINS_URL/whoAmI/api/json" 2>/dev/null \
    | "$PY_BIN" -c 'import json,sys; print(json.load(sys.stdin)["name"])' 2>/dev/null || true)
if [ -z "$WHOAMI" ] || [ "$WHOAMI" = "anonymous" ]; then
    echo "ERROR: could not authenticate to Jenkins as '$JENKINS_ADMIN_USER'."
    exit 1
fi

CRUMB_JSON=$(curl -fsS -u "$AUTH" -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
    "$JENKINS_URL/crumbIssuer/api/json")
CRUMB_FIELD=$("$PY_BIN" -c 'import json,sys; print(json.load(sys.stdin)["crumbRequestField"])' <<<"$CRUMB_JSON")
CRUMB=$("$PY_BIN" -c 'import json,sys; print(json.load(sys.stdin)["crumb"])' <<<"$CRUMB_JSON")

echo "Applying credentials"
curl -fsS -X POST "$JENKINS_URL/scriptText" \
    -u "$AUTH" -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
    -H "$CRUMB_FIELD: $CRUMB" \
    --data-urlencode "script@$GROOVY_FILE"

cat <<DONE

===========================================================================
 Done. Delete sp-credentials.json once you are happy Jenkins has the values:
     rm sp-credentials.json
===========================================================================
DONE
