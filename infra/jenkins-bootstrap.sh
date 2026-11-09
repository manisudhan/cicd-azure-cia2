#!/usr/bin/env bash
# ===========================================================================
# Creates (or updates) the Jenkins pipeline job from jenkins/job-config.xml and
# optionally starts a build - all through the Jenkins REST API, so the job is
# defined by a version-controlled file rather than clicked together in the UI.
#
#   bash infra/jenkins-bootstrap.sh                 # create/update the job
#   bash infra/jenkins-bootstrap.sh --build         # ...and start a build
#   DEPLOY_TARGET=azure RUN_SONAR=true bash infra/jenkins-bootstrap.sh --build
#
# Credentials come from .env (JENKINS_ADMIN_USER / JENKINS_ADMIN_PASSWORD).
# ===========================================================================
set -euo pipefail

JENKINS_URL="${JENKINS_URL:-http://localhost:8090}"
JOB_NAME="${JOB_NAME:-cicd-demo-app}"
DEPLOY_TARGET="${DEPLOY_TARGET:-local}"
RUN_SONAR="${RUN_SONAR:-false}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
JOB_CONFIG="$PROJECT_ROOT/jenkins/job-config.xml"
COOKIE_JAR="$(mktemp)"
trap 'rm -f "$COOKIE_JAR"' EXIT

# Load .env without exporting it into the surrounding shell permanently.
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$PROJECT_ROOT/.env"
    set +a
fi

JENKINS_ADMIN_USER="${JENKINS_ADMIN_USER:-admin}"
if [ -z "${JENKINS_ADMIN_PASSWORD:-}" ]; then
    echo "ERROR: JENKINS_ADMIN_PASSWORD is not set. Copy .env.example to .env."
    exit 1
fi
AUTH="${JENKINS_ADMIN_USER}:${JENKINS_ADMIN_PASSWORD}"

if [ ! -f "$JOB_CONFIG" ]; then
    echo "ERROR: $JOB_CONFIG not found."
    exit 1
fi

# ------------------------------------------------------ wait for Jenkins -----
echo "Waiting for Jenkins at $JENKINS_URL"
for i in $(seq 1 60); do
    if curl -fsS -o /dev/null "$JENKINS_URL/login"; then break; fi
    sleep 5
done
if ! curl -fsS -o /dev/null "$JENKINS_URL/login"; then
    echo "ERROR: Jenkins did not become reachable at $JENKINS_URL"
    echo "Check it with: docker compose logs --tail=40 jenkins"
    exit 1
fi

# Confirm the credentials work before doing anything else.
WHOAMI=$(curl -fsS -u "$AUTH" -c "$COOKIE_JAR" \
    "$JENKINS_URL/whoAmI/api/json" 2>/dev/null \
    | python -c 'import json,sys; print(json.load(sys.stdin)["name"])' 2>/dev/null || true)
if [ -z "$WHOAMI" ] || [ "$WHOAMI" = "anonymous" ]; then
    echo "ERROR: could not authenticate to Jenkins as '$JENKINS_ADMIN_USER'."
    echo "If you changed the password after the first boot, the admin account was"
    echo "already created; use the original password or recreate the volume with"
    echo "  docker compose down -v && docker compose up -d"
    exit 1
fi
echo "Authenticated as: $WHOAMI"

# Jenkins requires a CSRF crumb on POSTs. It is bound to the session, so the
# same cookie jar must be reused for the crumb request and the POST.
CRUMB_JSON=$(curl -fsS -u "$AUTH" -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
    "$JENKINS_URL/crumbIssuer/api/json")
CRUMB_FIELD=$(echo "$CRUMB_JSON" | python -c 'import json,sys; print(json.load(sys.stdin)["crumbRequestField"])')
CRUMB=$(echo "$CRUMB_JSON" | python -c 'import json,sys; print(json.load(sys.stdin)["crumb"])')

# --------------------------------------------------- create or update job ----
if curl -fsS -o /dev/null -u "$AUTH" "$JENKINS_URL/job/$JOB_NAME/api/json" 2>/dev/null; then
    echo "Job '$JOB_NAME' exists - updating its configuration"
    ENDPOINT="$JENKINS_URL/job/$JOB_NAME/config.xml"
else
    echo "Creating job '$JOB_NAME'"
    ENDPOINT="$JENKINS_URL/createItem?name=$JOB_NAME"
fi

curl -fsS -X POST "$ENDPOINT" \
    -u "$AUTH" -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
    -H "$CRUMB_FIELD: $CRUMB" \
    -H 'Content-Type: application/xml' \
    --data-binary "@$JOB_CONFIG"
echo "Job configuration applied."

# ------------------------------------------------------------ start build ----
if [ "${1:-}" = "--build" ]; then
    echo
    echo "Starting a build (DEPLOY_TARGET=$DEPLOY_TARGET, RUN_SONAR=$RUN_SONAR)"
    # buildWithParameters only accepts parameters the job already knows about.
    # A pipeline job learns its parameters from the first run of the Jenkinsfile,
    # so fall back to a plain build if the parameter POST is rejected.
    if ! curl -fsS -X POST \
            "$JENKINS_URL/job/$JOB_NAME/buildWithParameters?DEPLOY_TARGET=$DEPLOY_TARGET&RUN_SONAR=$RUN_SONAR" \
            -u "$AUTH" -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
            -H "$CRUMB_FIELD: $CRUMB" -o /dev/null; then
        echo "Parameterised build was rejected (first run registers the parameters)."
        echo "Starting an unparameterised build instead; it uses the Jenkinsfile defaults."
        curl -fsS -X POST "$JENKINS_URL/job/$JOB_NAME/build" \
            -u "$AUTH" -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
            -H "$CRUMB_FIELD: $CRUMB" -o /dev/null
    fi
    echo "Build queued."
fi

cat <<DONE

===========================================================================
 Job  : $JENKINS_URL/job/$JOB_NAME/
 Watch: $JENKINS_URL/job/$JOB_NAME/lastBuild/console
===========================================================================
DONE
