# End-to-End Cloud CI/CD Pipeline on Microsoft Azure

A Java web application built, tested, scanned, containerised and deployed to
**Azure Kubernetes Service** automatically on every push to `main`.

**CIA-2 — Design and Implementation of an End-to-End Cloud-Based CI/CD Pipeline**

---

## Architecture

Jenkins runs locally in Docker; Azure hosts only the registry and the cluster.
That keeps the cloud bill to about **$2/day while running** and **$0.35/day
paused**, instead of ~$4.50/day for a cloud-hosted Jenkins VM.

```mermaid
flowchart LR
    DEV[Developer] -->|git push| GH[(GitHub<br/>public repo)]
    GH -->|SCM poll / webhook| J[Jenkins<br/>local Docker container]

    subgraph PIPE[Jenkins pipeline]
        direction TB
        S1[1 Checkout] --> S2[2 Gitleaks<br/>secret scan]
        S2 --> S3[3 Maven<br/>build + tests]
        S3 --> S4[4 SonarQube Cloud<br/>Quality Gate]
        S4 --> S5[5 Docker build]
        S5 --> S6[6 Push to ACR]
        S6 --> S7[7 Deploy via Ansible]
        S7 --> S8[8 Verify + smoke test]
    end

    J --> PIPE

    subgraph AZ[Microsoft Azure: rg-cicd-cia2]
        ACR[(Azure Container<br/>Registry)]
        AKS[Azure Kubernetes<br/>Service]
        LB[Azure Load Balancer<br/>public IP]
        ACR -->|image pull via<br/>managed identity| AKS
        AKS --> LB
    end

    S6 --> ACR
    S7 --> AKS
    LB --> USER[Browser]
```

| Layer | Technology |
|---|---|
| Source control | Git + GitHub (public repository) |
| Build & test | Maven 3.9 (wrapper), Java 21, JUnit 5, JaCoCo |
| Secret scanning | **Gitleaks** — scans full Git history, fails the build on any finding |
| Static analysis | **SonarQube Cloud** — bugs, vulnerabilities, coverage, Quality Gate |
| Containerisation | Docker, multi-stage build, non-root Alpine JRE runtime |
| Registry | Azure Container Registry (ACR) |
| Orchestration | Azure Kubernetes Service (AKS), 2 replicas, rolling update, HPA |
| CI/CD engine | Jenkins (declarative `Jenkinsfile`), local Docker container |
| Config management | Ansible — drives the AKS deployment; VM playbook kept as the cloud option |

---

## Repository layout

```
.
├── Jenkinsfile                  8-stage declarative CI/CD pipeline
├── docker-compose.yml           Local Jenkins controller
├── jenkins/
│   ├── Dockerfile               Jenkins + docker CLI, az, kubectl, gitleaks, ansible
│   └── plugins.txt              Plugins pre-installed at image build time
│
├── pom.xml                      Maven build, JaCoCo + Sonar configuration
├── mvnw, mvnw.cmd, .mvn/        Maven wrapper (no Maven install needed)
├── Dockerfile                   Multi-stage app image, runs as UID 10001
├── .dockerignore                Keeps build context small and secret-free
├── .gitleaks.toml               Secret-scanning rules + documented allowlist
├── .gitattributes               Forces LF on scripts so they run on Linux
├── .env.example                 Config template (never a real secret)
│
├── src/main/java/com/example/cicd/
│   ├── CicdDemoApplication.java
│   ├── config/AppProperties.java              Build metadata from the pipeline
│   ├── controller/HomeController.java         HTML landing page
│   ├── controller/GreetingApiController.java  REST API
│   ├── model/                                 Response records
│   └── service/                               Business logic
├── src/main/resources/
│   ├── application.yml          Actuator probes, externalised config
│   ├── templates/index.html     Page that proves which build is live
│   └── static/css/app.css
├── src/test/java/...            29 unit tests (95.7% instruction coverage)
│
├── k8s/
│   ├── 00-namespace.yaml  01-configmap.yaml  02-deployment.yaml
│   ├── 03-service.yaml    04-hpa.yaml
│   └── render.sh                 Substitutes this build's image tag
│
├── ansible/
│   ├── ansible.cfg  inventory.ini
│   ├── deploy-app.yml            USED: renders manifests, applies, verifies
│   └── jenkins-setup.yml         OPTIONAL: provisions a Jenkins VM instead
│
├── infra/
│   ├── azure-setup.sh            Creates RG, ACR, AKS, service principal
│   ├── azure-pause.sh            Stops the cluster (~$0.35/day)
│   ├── azure-resume.sh           Starts it again
│   └── azure-teardown.sh         Deletes everything
│
└── docs/
    ├── SETUP.md                  Step-by-step runbook
    ├── REPORT.md                 Technical report
    └── screenshots/              Evidence for submission
```

---

## Quick start

Full instructions are in **[docs/SETUP.md](docs/SETUP.md)**. In short:

```bash
bash infra/azure-setup.sh
```

```bash
docker compose up -d --build
```

Then open <http://localhost:8080>, add the four credentials, point a Pipeline
job at this repository, and push a commit.

### Run the application locally

```bash
./mvnw spring-boot:run
```

Then open <http://localhost:8080> — note this clashes with Jenkins, so stop one
or the other first.

```bash
./mvnw clean verify
```

Runs the 29 unit tests and writes coverage to `target/site/jacoco/index.html`.

```bash
docker build -t cicd-demo-app:local . && docker run --rm -p 9090:8080 cicd-demo-app:local
```

Builds and runs the container image exactly as the pipeline does.

---

## Endpoints

| Endpoint | Purpose |
|---|---|
| `/` | Landing page showing the live image tag, build number, commit and pod name |
| `/api/v1/greeting?name=X` | JSON greeting plus the pod that served the request |
| `/api/v1/info` | Build metadata — used by the pipeline's smoke test |
| `/actuator/health` | Overall health |
| `/actuator/health/liveness` | Kubernetes liveness probe |
| `/actuator/health/readiness` | Kubernetes readiness probe |

---

## Demonstrating a change flowing through the pipeline

Edit the release message, commit and push:

```bash
sed -i 's/APP_RELEASE_MESSAGE: .*/APP_RELEASE_MESSAGE: "Release 2 - shipped automatically"/' k8s/01-configmap.yaml && git commit -am "Update release message" && git push
```

Jenkins picks the push up within about two minutes (SCM polling) and runs all
eight stages. A new image tag `<build>-<commit>` appears in ACR, AKS performs a
zero-downtime rolling update, and the new message plus the new build number are
visible in the browser.

---

## Cost control

Only ACR and AKS bill in Azure. Approximate Central India rates:

| State | Cost |
|---|---|
| Running (AKS node + Load Balancer + IP + disk + ACR) | ~$0.085/hr ≈ **$2.05/day** |
| Paused (`azure-pause.sh`) | ~$0.015/hr ≈ **$0.35/day** |
| Jenkins (local Docker) | $0 |

Between sessions:

```bash
bash infra/azure-pause.sh && docker compose stop
```

Before a session:

```bash
bash infra/azure-resume.sh && docker compose up -d
```

When finished for good:

```bash
bash infra/azure-teardown.sh
```
