# All links — CIA-2 CI/CD pipeline

Everything in one place. Keep this open during the demo.

---

## 1. The live application

| What | Link |
|---|---|
| **Landing page** | <http://cicd-demo-cia2.centralindia.cloudapp.azure.com> |
| Build metadata (JSON) | <http://cicd-demo-cia2.centralindia.cloudapp.azure.com/api/v1/info> |
| Greeting API | <http://cicd-demo-cia2.centralindia.cloudapp.azure.com/api/v1/greeting?name=DevOps> |
| Health (what the K8s probes call) | <http://cicd-demo-cia2.centralindia.cloudapp.azure.com/actuator/health> |
| Liveness probe endpoint | <http://cicd-demo-cia2.centralindia.cloudapp.azure.com/actuator/health/liveness> |
| Readiness probe endpoint | <http://cicd-demo-cia2.centralindia.cloudapp.azure.com/actuator/health/readiness> |
| Raw IP (still works) | <http://20.219.204.192> |

---

## 2. Source code — GitHub

| What | Link |
|---|---|
| **Repository** | <https://github.com/manisudhan/cicd-azure-cia2> |
| Commit history | <https://github.com/manisudhan/cicd-azure-cia2/commits/main> |
| `Jenkinsfile` — the 8-stage pipeline | <https://github.com/manisudhan/cicd-azure-cia2/blob/main/Jenkinsfile> |
| `Dockerfile` — multi-stage image | <https://github.com/manisudhan/cicd-azure-cia2/blob/main/Dockerfile> |
| `.gitleaks.toml` — secret-scan rules | <https://github.com/manisudhan/cicd-azure-cia2/blob/main/.gitleaks.toml> |
| Kubernetes manifests | <https://github.com/manisudhan/cicd-azure-cia2/tree/main/k8s> |
| Ansible playbooks | <https://github.com/manisudhan/cicd-azure-cia2/tree/main/ansible> |
| Azure provisioning scripts | <https://github.com/manisudhan/cicd-azure-cia2/tree/main/infra> |

---

## 3. Jenkins — http://localhost:8090

Login: `admin`. Password is in the git-ignored `.env` file in the repo root.

> Jenkins runs in a local Docker container. Start it with `docker compose up -d`
> **before** the viva — these links are dead if the container is stopped.

| What | Link |
|---|---|
| **The job** | <http://localhost:8090/job/cicd-demo-app/> |
| **Build 13 — best Azure build, all 9 stages green** | <http://localhost:8090/job/cicd-demo-app/13/> |
| Build 13 — Stage View / pipeline graph | <http://localhost:8090/job/cicd-demo-app/13/pipeline-graph/> |
| Build 13 — full console log | <http://localhost:8090/job/cicd-demo-app/13/console> |
| Build 13 — test results (29 tests) | <http://localhost:8090/job/cicd-demo-app/13/testReport/> |
| Build 13 — archived artifacts (Gitleaks SARIF, JAR, JaCoCo) | <http://localhost:8090/job/cicd-demo-app/13/artifact/> |
| **Git polling log** — proves builds trigger automatically | <http://localhost:8090/job/cicd-demo-app/scmPollLog/> |
| Credentials store (the four secrets) | <http://localhost:8090/manage/credentials/store/system/domain/_/> |
| Installed plugins | <http://localhost:8090/manage/pluginManager/installed> |

**Which builds to show, and which to avoid**

| Builds | Result | Note |
|---|---|---|
| 8, 11, 12, 13 | SUCCESS, target `azure` | **Show these** — all 9 stages including ACR push |
| 6, 7, 9, 10 | SUCCESS, target `local` | Green, but stage 6 skipped (no ACR push) |
| 1 | SUCCESS, Sonar skipped | First proving run |
| 2–5 | FAILURE | Ran before SonarCloud was configured — the Quality Gate correctly refused. Don't show these |

---

## 4. SonarQube Cloud

| What | Link |
|---|---|
| **Project dashboard — Quality Gate** | <https://sonarcloud.io/project/overview?id=manisudhan_cicd-azure-cia2> |
| Issues | <https://sonarcloud.io/project/issues?id=manisudhan_cicd-azure-cia2> |
| Measures / coverage | <https://sonarcloud.io/component_measures?id=manisudhan_cicd-azure-cia2> |
| Security hotspots | <https://sonarcloud.io/project/security_hotspots?id=manisudhan_cicd-azure-cia2> |
| Analysis history | <https://sonarcloud.io/project/activity?id=manisudhan_cicd-azure-cia2> |
| Organisation | <https://sonarcloud.io/organizations/manisudhan> |

- Organisation key: `manisudhan`
- Project key: `manisudhan_cicd-azure-cia2`

---

## 5. Gitleaks

Gitleaks has **no website** — it is a single binary that runs as stage 2 inside the
pipeline. If asked "where do I see Gitleaks?", the answer is the build, not a dashboard.

| What | Where |
|---|---|
| **Stage 2 output in the build log** | <http://localhost:8090/job/cicd-demo-app/13/console> — search for `gitleaks` |
| The SARIF report it produces | <http://localhost:8090/job/cicd-demo-app/13/artifact/> |
| The rules (6 custom + ~170 default) | <https://github.com/manisudhan/cicd-azure-cia2/blob/main/.gitleaks.toml> |
| Project homepage | <https://github.com/gitleaks/gitleaks> |

Run it yourself:

```bash
gitleaks git . --config .gitleaks.toml --redact --exit-code 1
```

Expected on a clean repo: `no leaks found`.

---

## 6. Azure portal

Subscription `3b188369-d183-4b5b-9269-707168198a80`.

| What | Link |
|---|---|
| **Resource group `rg-cicd-cia2`** | <https://portal.azure.com/#resource/subscriptions/3b188369-d183-4b5b-9269-707168198a80/resourceGroups/rg-cicd-cia2/overview> |
| **AKS cluster overview** | <https://portal.azure.com/#resource/subscriptions/3b188369-d183-4b5b-9269-707168198a80/resourceGroups/rg-cicd-cia2/providers/Microsoft.ContainerService/managedClusters/aks-cicd-cia2/overview> |
| **Pods / Deployments (Workloads)** | <https://portal.azure.com/#resource/subscriptions/3b188369-d183-4b5b-9269-707168198a80/resourceGroups/rg-cicd-cia2/providers/Microsoft.ContainerService/managedClusters/aks-cicd-cia2/workloads> |
| **Container registry — image tags** | <https://portal.azure.com/#resource/subscriptions/3b188369-d183-4b5b-9269-707168198a80/resourceGroups/rg-cicd-cia2/providers/Microsoft.ContainerRegistry/registries/acrcicdcia2/repositories> |
| All subscriptions / credit | <https://portal.azure.com/#view/Microsoft_Azure_Billing/SubscriptionsBladeV2> |
| Cost analysis | <https://portal.azure.com/#view/Microsoft_Azure_CostManagement/Menu/~/costanalysis> |

**Inside the AKS blade, use the left menu for:**

- **Kubernetes resources → Workloads** — pods, deployments, replica sets
- **Kubernetes resources → Services and ingresses** — the external IP
- **Kubernetes resources → Configuration** — the ConfigMap
- **Node pools** — the VM behind it all
- **Run command** (under *Settings*) — run `kubectl` in the browser, no terminal needed

> In the Workloads blade, set the namespace filter to **`cicd-demo`**, otherwise you
> see the 14 `kube-system` pods that run Kubernetes itself.

---

## 7. Documentation in this repo

| Document | Purpose |
|---|---|
| `docs/CICD-Study-Guide.pdf` | 32 pages — the whole system explained |
| `docs/Viva-Survival-Sheet.pdf` | 2 pages — read right before the viva |
| `docs/REPORT.md` | The technical report |
| `docs/SETUP.md` | Azure runbook + troubleshooting |
| `docs/LOCAL.md` | Running it without Azure |
| `docs/screenshots/README.md` | The evidence checklist |

---

## 8. Before the viva — 60-second checklist

```bash
docker compose up -d                                   # Jenkins back up
az aks show -g rg-cicd-cia2 -n aks-cicd-cia2 --query powerState.code -o tsv   # should say Running
kubectl -n cicd-demo get pods                          # should be 2/2 Running
curl http://cicd-demo-cia2.centralindia.cloudapp.azure.com/api/v1/info
```

If the cluster was paused: `bash infra/azure-resume.sh` (takes 3–5 minutes).
