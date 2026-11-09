# ---------------------------------------------------------------------------
# Jenkins controller image for the CI/CD pipeline.
#
# Jenkins runs locally in Docker rather than on an Azure VM, which keeps the
# Azure bill to ACR + AKS only. Every tool the Jenkinsfile shells out to is
# baked in here, so the build agent is reproducible and there is nothing to
# install by hand:
#
#   docker CLI  - stage 5 builds the application image (uses the host daemon
#                 through the mounted socket; no daemon runs in this container)
#   az          - stages 6 and 7 authenticate to Azure, ACR and AKS
#   kubectl     - stages 7 and 8 apply manifests and check the rollout
#   gitleaks    - stage 2 secret scanning
#   ansible     - stage 7 deployment automation
#   envsubst    - k8s/render.sh manifest rendering (gettext-base)
#
# Build and run it with:  docker compose up -d --build
# ---------------------------------------------------------------------------
FROM jenkins/jenkins:2.516.3-lts-jdk21

# Pre-install the plugins the pipeline needs so the setup wizard does not have
# to be clicked through, and the job works on first run.
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

# Tool installation needs root; Jenkins drops back to the jenkins user below.
USER root

ARG KUBECTL_VERSION=v1.31.0
ARG GITLEAKS_VERSION=8.30.1

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        gnupg \
        unzip \
        jq \
        gettext-base \
        python3 \
        python3-pip \
        ansible; \
    rm -rf /var/lib/apt/lists/*

# Docker CLI only - the daemon is the host's, reached via the mounted socket.
RUN set -eux; \
    install -m 0755 -d /etc/apt/keyrings; \
    curl -fsSL https://download.docker.com/linux/debian/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg; \
    chmod a+r /etc/apt/keyrings/docker.gpg; \
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        > /etc/apt/sources.list.d/docker.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends docker-ce-cli docker-buildx-plugin; \
    rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    curl -fsSLo /usr/local/bin/kubectl \
        "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"; \
    chmod 0755 /usr/local/bin/kubectl; \
    kubectl version --client=true

RUN set -eux; \
    curl -fsSL "https://aka.ms/InstallAzureCLIDeb" | bash; \
    az version

RUN set -eux; \
    curl -fsSLo /tmp/gitleaks.tar.gz \
        "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz"; \
    tar -xzf /tmp/gitleaks.tar.gz -C /usr/local/bin gitleaks; \
    chmod 0755 /usr/local/bin/gitleaks; \
    rm -f /tmp/gitleaks.tar.gz; \
    gitleaks version

# Record the toolchain in the image so "docker run ... versions" can prove it.
RUN printf '%s\n' \
    "java     : $(java -version 2>&1 | head -1)" \
    "git      : $(git --version)" \
    "docker   : $(docker --version)" \
    "kubectl  : $(kubectl version --client=true -o yaml | grep gitVersion | head -1 | tr -d ' ')" \
    "az       : $(az version -o tsv --query '\"azure-cli\"')" \
    "gitleaks : $(gitleaks version)" \
    "ansible  : $(ansible --version | head -1)" \
    > /usr/local/share/toolchain.txt \
 && cat /usr/local/share/toolchain.txt

USER jenkins
