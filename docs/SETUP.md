# Setup Runbook

Follow these steps in order. Expect about 45–60 minutes, most of it waiting for
Azure to create the AKS cluster and for the Jenkins image to build.

Jenkins runs **locally in Docker**; Azure hosts only the container registry and
the Kubernetes cluster.

---

## 0. Prerequisites

| Tool | Check | Install on Windows |
|---|---|---|
| Git | `git --version` | already installed |
| Docker Desktop | `docker info` | already installed — **it must be running** |
| Azure CLI | `az version` | already installed |
| GitHub CLI | `gh --version` | already installed |
| Java 21 | `java -version` | already installed (only needed to run the app outside Docker) |
| kubectl | `kubectl version --client` | already installed (optional — the Jenkins image has its own) |

Maven is **not** required: the repository ships the Maven wrapper (`./mvnw`).
Ansible is **not** required on your machine: it is built into the Jenkins image.

> **Docker Desktop must use the WSL 2 backend** (Settings → General → "Use the
> WSL 2 based engine"). The Jenkins container mounts the host Docker socket to
> build the application image, which needs that backend.

> **Ports.** Jenkins is published on **8090**, not 8080, because a separately
> installed native Jenkins may already hold 8080 on this machine (that was the
> case here). The Spring Boot app still uses 8080 when run directly with
> `./mvnw spring-boot:run`, so the two no longer clash. Change the published
> port in `docker-compose.yml` if 8090 is taken too.

---

## 1. Push the repository to GitHub

```bash
gh auth login
```

```bash
cd /c/Users/mmani/Downloads/CICD && gh repo create cicd-azure-cia2 --public --source=. --remote=origin --push
```

The repository must be **public** so SonarQube Cloud analysis is free and your
instructor can access it.

---

## 2. Provision the Azure resources

```bash
az login
```

```bash
az account show --output table
```

```bash
bash infra/azure-setup.sh
```

This creates:

| Resource | Name | Notes |
|---|---|---|
| Resource group | `rg-cicd-cia2` | everything lives here |
| Container registry | `acrcicdcia2` | Basic SKU, ~$5/month |
| AKS cluster | `aks-cicd-cia2` | 1 × `Standard_B2s`, free control plane, 32 GB disk, `AcrPull` granted |
| Service principal | `sp-cicd-cia2` | `Contributor` on the group, `AcrPush`, AKS Cluster Admin |

> **ACR names are globally unique.** If `acrcicdcia2` is taken the script stops
> and tells you to rerun as `ACR_NAME=acrcicdcia2ss bash infra/azure-setup.sh`.
> If you change it, update `ACR_NAME` and `ACR_LOGIN_SERVER` in `Jenkinsfile`
> and `acr_login_server` in `ansible/deploy-app.yml`.

**Copy the service principal `appId`, `password` and `tenant` from the output
now** — the password is shown only once. Do not paste them into any file in the
repository; Gitleaks will fail the build.

---

## 3. Start Jenkins locally

```bash
docker compose up -d --build
```

The first build takes about five minutes: it installs the Docker CLI, Azure
CLI, kubectl, Gitleaks and Ansible into the Jenkins image, and pre-installs the
plugins listed in `jenkins/plugins.txt` — so there is no plugin wizard to click
through.

```bash
docker compose logs -f jenkins
```

Watch for `Jenkins is fully up and running`, then get the unlock password:

```bash
docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Open <http://localhost:8090>, paste the password, choose **Select plugins to
install → None** (they are already installed), and create your admin user.

Confirm the toolchain that was baked into the image:

```bash
docker compose exec jenkins cat /usr/local/share/toolchain.txt
```

---

## 4. Set up SonarQube Cloud

1. Go to <https://sonarcloud.io> and sign in **with GitHub**.
2. Create an organisation (free plan) and import the `cicd-azure-cia2` repository.
3. Choose **"With Jenkins"** as the analysis method. This disables SonarCloud's
   Automatic Analysis — required, otherwise the pipeline's analysis is rejected.
4. Note your **organisation key** and **project key**.
5. Create a token: avatar → **My Account → Security → Generate Token**.

Update the two keys in `Jenkinsfile`:

```groovy
SONAR_ORG         = 'your-org-key'
SONAR_PROJECT_KEY = 'your-org-key_cicd-azure-cia2'
```

Commit and push that change — the pipeline reads the `Jenkinsfile` from Git.

---

## 5. Configure Jenkins

**Manage Jenkins → Credentials → System → Global credentials** — add four:

| ID | Kind | Value |
|---|---|---|
| `azure-sp` | Username with password | username = SP `appId`, password = SP `password` |
| `azure-tenant-id` | Secret text | the `tenant` GUID |
| `azure-subscription-id` | Secret text | `az account show --query id -o tsv` |
| `sonarcloud-token` | Secret text | the SonarCloud token from step 4 |

The IDs must match exactly — the `Jenkinsfile` looks them up by ID.

**New Item → Pipeline**, name it `cicd-demo-app`:

- Build Triggers → tick **Poll SCM** (the schedule comes from the `Jenkinsfile`)
- Pipeline → **Pipeline script from SCM** → SCM **Git**
- Repository URL: `https://github.com/<you>/cicd-azure-cia2.git`
- Branch: `*/main`, Script Path: `Jenkinsfile`
- Save.

---

## 6. Automatic triggering

**Default — SCM polling (no setup).** The `Jenkinsfile` declares
`pollSCM('H/2 * * * *')`, so Jenkins checks GitHub every two minutes and starts
a build by itself when it sees a new commit. No inbound network access is
needed, which is what makes a local controller viable. This satisfies "the
pipeline runs automatically" — nobody clicks Build.

**Optional — a real webhook.** GitHub cannot reach `localhost`, so expose
Jenkins through a free tunnel if you want instant triggering and a GitHub
"Recent Deliveries" screenshot:

```bash
winget install Cloudflare.cloudflared
```

```bash
cloudflared tunnel --url http://localhost:8090
```

That prints a public `https://<random>.trycloudflare.com` URL. In the GitHub
repository: **Settings → Webhooks → Add webhook**

- Payload URL: `https://<random>.trycloudflare.com/github-webhook/`
- Content type: `application/json`
- Event: *Just the push event*

The URL changes each time you restart the tunnel, so update the webhook then.

---

## 7. Run the pipeline

Click **Build Now** for the first run, then push a commit to see polling
trigger it on its own.

Expected stage outcomes:

| Stage | Evidence |
|---|---|
| 1 Checkout | commit SHA and image tag printed |
| 2 Gitleaks | `no secrets detected in git history`, SARIF archived |
| 3 Build & Test | `Tests run: 29, Failures: 0`, JUnit trend chart |
| 4 SonarQube Cloud | Quality Gate **Passed** on the SonarCloud dashboard |
| 5 Docker Build | image tagged `<build>-<commit>` and `latest` |
| 6 Push to ACR | `az acr repository show-tags` lists the new tag |
| 7 Deploy to AKS | Ansible output ends with the public IP |
| 8 Verify | rollout succeeded, `/api/v1/info` returns this build's `imageTag` |

Get the endpoint at any time:

```bash
kubectl -n cicd-demo get svc cicd-demo-app -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

---

## 8. Demonstrate a change flowing through

```bash
sed -i 's/APP_RELEASE_MESSAGE: .*/APP_RELEASE_MESSAGE: "Release 2 - shipped automatically by Jenkins"/' k8s/01-configmap.yaml
```

```bash
git commit -am "Demo: change the release message" && git push
```

Within two minutes the build starts by itself. Then refresh the browser: the
message and the build number change while the service stays up, because the
deployment uses `maxUnavailable: 0`.

---

## 9. Collect the screenshots

Save them into `docs/screenshots/` — see that folder's README for the list.

---

## 10. Protect your credits

Between sessions:

```bash
bash infra/azure-pause.sh && docker compose stop
```

Before the next session:

```bash
bash infra/azure-resume.sh && docker compose up -d
```

When the assignment is finished:

```bash
bash infra/azure-teardown.sh
```

Running ≈ $2.05/day, paused ≈ $0.35/day, Jenkins ≈ $0.

---

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `docker: command not found` or `Cannot connect to the Docker daemon` in stage 5 | Docker Desktop is not running, or it is not using the WSL 2 backend, so the mounted socket is dead. Start Docker Desktop and `docker compose restart jenkins`. |
| `permission denied while trying to connect to the Docker daemon socket` | The container is not running as root. Check `user: root` is still in `docker-compose.yml`, then `docker compose up -d --force-recreate`. |
| Stage 4 fails with *"Project was already analysed by SonarCloud Automatic Analysis"* | Turn off Automatic Analysis in the SonarCloud project's **Administration → Analysis Method**. |
| Stage 6 `unauthorized: authentication required` | The service principal lacks `AcrPush`, or `ACR_NAME` in the `Jenkinsfile` does not match the real registry. |
| Stage 7 `az aks get-credentials` forbidden | The SP needs the *Azure Kubernetes Service Cluster Admin Role*; `azure-setup.sh` grants it. |
| Pods stuck `ImagePullBackOff` | AKS was not attached to ACR: `az aks update -g rg-cicd-cia2 -n aks-cicd-cia2 --attach-acr acrcicdcia2`. |
| Service `EXTERNAL-IP` stays `<pending>` | Azure takes 2–5 minutes to create the Load Balancer; the pipeline waits up to 5 minutes. |
| Pods `Pending` with *Insufficient cpu* | One `B2s` node cannot host 2 replicas plus system pods: `az aks scale -g rg-cicd-cia2 -n aks-cicd-cia2 --node-count 2` (doubles the node cost). |
| Push does not trigger a build | Polling runs every two minutes — wait, or click **Build Now**. Check the job's *Git Polling Log* for errors. |
| Webhook delivery fails | The `trycloudflare.com` URL changes on every tunnel restart; update the webhook's Payload URL. |
| Jenkins is slow or the build OOMs | Raise the container's memory in Docker Desktop (Settings → Resources) and `JAVA_OPTS` in `docker-compose.yml`. |
| `ports are not available: exposing port TCP 0.0.0.0:8090` | Something else holds the port. Find it with `Get-NetTCPConnection -LocalPort 8090 -State Listen` then `Get-Process -Id <pid>`, and either stop it or change the published port in `docker-compose.yml`. |
| `bash: ./mvnw: /bin/sh^M: bad interpreter` | Line endings. `.gitattributes` forces LF; re-clone, or run `git add --renormalize .`. |
