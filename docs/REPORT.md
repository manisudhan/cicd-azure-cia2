# Design and Implementation of an End-to-End Cloud-Based CI/CD Pipeline

**CIA-2 Technical Report**

| | |
|---|---|
| Student | *<your name and registration number>* |
| Cloud provider | Microsoft Azure |
| CI/CD platform | Jenkins (declarative pipeline) on an Azure Ubuntu VM |
| Repository | `https://github.com/<you>/cicd-azure-cia2` |
| Live endpoint | `http://<loadbalancer-public-ip>` |
| Date | *<submission date>* |

---

## 1. Problem definition

A development team builds a Java web application by hand: a developer compiles
it locally, runs the tests when they remember to, builds a Docker image with
ad-hoc tags, and copies it to a server. This manual process has four concrete
failure modes:

1. **Not reproducible.** The artifact depends on whichever JDK, Maven version
   and local configuration the developer happened to have. "It works on my
   machine" cannot be disproved.
2. **Error-prone.** Any step can be skipped. Tests get bypassed under deadline
   pressure, and an untested build reaches users.
3. **Slow and serialising.** One person owns the deploy. Releases queue behind
   that person's availability.
4. **Untraceable.** With tags like `latest` or `v2-final`, nobody can say which
   commit is running in production, which makes a rollback guesswork.

The objective of this assignment is to replace that process with an automated
pipeline that triggers on a push to Git, builds and tests the application,
produces a uniquely identified container image, publishes it to a cloud
registry, deploys it to a managed Kubernetes cluster, and verifies that the new
version is actually serving traffic — with no manual step in between.

Two quality gates are added beyond the base requirement, because an automated
pipeline that ships defects or leaked credentials faster is not an improvement:

- **Gitleaks** — secret detection across the full Git history.
- **SonarQube Cloud** — static analysis with an enforced Quality Gate.

### 1.1 Architecture

```
  ┌───────────┐   git push    ┌──────────────────┐   webhook   ┌─────────────────────────┐
  │ Developer │──────────────▶│ GitHub           │────────────▶│ Jenkins (Azure VM)      │
  └───────────┘               │ public repository│             │ Ubuntu 24.04, B2s       │
                             └──────────────────┘             └───────────┬─────────────┘
                                                                          │
                     ┌────────────────────────────────────────────────────┘
                     │  Declarative pipeline, 8 stages
                     ▼
   ┌──────────────────────────────────────────────────────────────────────────────┐
   │ 1 Checkout  ─▶ 2 Gitleaks ─▶ 3 Maven build + 29 unit tests + JaCoCo         │
   │                  (security gate)                                            │
   │             ─▶ 4 SonarQube Cloud analysis + Quality Gate (quality gate)     │
   │             ─▶ 5 Docker build, tag <build>-<commit>                         │
   │             ─▶ 6 docker push ──────────────────────────────┐                │
   │             ─▶ 7 Ansible: render manifests, kubectl apply  │                │
   │             ─▶ 8 rollout status + HTTP smoke test          │                │
   └────────────────────────────────────────────────────────────┼────────────────┘
                                                               ▼
                 ┌──────────────────────────┐        ┌──────────────────────────┐
                 │ Azure Container Registry │───────▶│ Azure Kubernetes Service │
                 │ acrcicdcia2 (Basic)      │ AcrPull│ aks-cicd-cia2            │
                 └──────────────────────────┘ via MI │ Deployment: 2 replicas   │
                                                     │ Rolling update, HPA 2-5  │
                                                     └────────────┬─────────────┘
                                                                  ▼
                                                     ┌──────────────────────────┐
                                                     │ Azure Standard Load      │
                                                     │ Balancer — public IP     │
                                                     └────────────┬─────────────┘
                                                                  ▼
                                                              Browser
```

Trust boundaries: GitHub and SonarQube Cloud are external SaaS; the Jenkins VM,
ACR and AKS sit inside one Azure resource group; Jenkins authenticates to Azure
with a service principal scoped to that resource group only.

---

## 2. Tools selected and justification

| Requirement | Tool chosen | Why this one |
|---|---|---|
| Source control | **Git + GitHub** | Required by the brief. A public repository satisfies instructor access and unlocks the free SonarQube Cloud tier. Webhooks give push-triggered builds without polling. |
| Build & dependency management | **Maven 3.9 via the wrapper** | Standard for Java; declarative `pom.xml`; the wrapper pins the exact Maven version in Git, so the build server needs no Maven installed — removing a class of "works on the build server only" failures. |
| Application framework | **Spring Boot 3.4 / Java 21** | Produces a self-contained executable JAR, so the container needs no application server. Spring Boot Actuator supplies ready-made liveness and readiness endpoints that map directly onto Kubernetes probes. |
| Unit testing | **JUnit 5 + AssertJ + MockMvc** | 29 tests cover the service logic, the configuration binding and both controllers at the HTTP layer without starting a real server. |
| Coverage | **JaCoCo** | Produces the XML report SonarQube Cloud consumes; measured at **95.7% instruction / 88.5% branch**. |
| Secret scanning | **Gitleaks** | Scans the whole Git *history*, not just the working tree, so a credential that was committed and later deleted is still found. Single static binary, ~170 built-in rules, extended here with six Azure/Jenkins/Sonar-specific rules. |
| Static analysis | **SonarQube Cloud** | Hosted, so no server to maintain or secure. Enforces a Quality Gate that the build waits on, which turns code quality into a hard pass/fail rather than a report nobody reads. Free for public repositories. |
| Containerisation | **Docker, multi-stage** | The build stage carries the JDK and Maven; the runtime stage carries only a JRE, so the published image is ~190 MB instead of ~600 MB and has a much smaller CVE surface. |
| Registry | **Azure Container Registry** | Native to Azure; AKS authenticates to it with its managed identity, so no registry password is ever stored in Kubernetes or in Jenkins. |
| Orchestration | **Azure Kubernetes Service** | Managed control plane (free tier), integrated Load Balancer for the public endpoint, built-in `metrics-server` for the HPA, and declarative rolling updates. |
| CI/CD engine | **Jenkins** | Chosen over GitHub Actions deliberately: it demonstrates the full DevOps stack — a build server that must itself be provisioned and configured, which is what makes the Ansible deliverable meaningful rather than decorative. The `Jenkinsfile` lives in the repository, so the pipeline is version-controlled alongside the code. |
| Configuration management | **Ansible** | Two genuine uses: `jenkins-setup.yml` turns a bare Ubuntu VM into the build server idempotently, and `deploy-app.yml` performs the Kubernetes rollout from the pipeline. Agentless — only SSH is needed. |

### 2.1 Alternatives considered

- **GitHub Actions** would have been faster to set up and needs no VM, but it
  hides the build infrastructure, leaving no real role for Ansible.
- **Azure DevOps Pipelines** is Azure-native, but its free tier requires a
  parallelism grant that can take several days to approve.
- **Helm** would template the manifests more powerfully than `envsubst`, but it
  adds a release lifecycle to explain for a five-file deployment.
- **Self-hosted SonarQube** gives full control, but needs ~3 GB RAM and its own
  patching and backup story; SonarQube Cloud removes that operational burden.

---

## 3. CI/CD pipeline stages and their purpose

The pipeline is defined declaratively in `Jenkinsfile`. Stages run in order and
the build stops at the first failure, so a defect never reaches the cluster.

| # | Stage | What it does | Why it exists |
|---|---|---|---|
| 1 | **Checkout** | Clones the commit, reads the short SHA, author and message, and derives `IMAGE_TAG = <build-number>-<commit-sha>`. | Makes every artifact traceable. Given a running pod you can name the exact commit and Jenkins build that produced it. |
| 2 | **Secret Scan (Gitleaks)** | `gitleaks git .` over the whole history with `--exit-code 1`, redacted SARIF report archived. | Shift-left security. Placed first so it costs seconds and blocks a leaked credential *before* any artifact is published to a registry where it would be hard to recall. |
| 3 | **Build & Unit Test (Maven)** | `./mvnw clean verify` — compile, 29 unit tests, package the JAR, JaCoCo report. Results published to Jenkins via JUnit; JAR and coverage archived. | The core CI step. `verify` rather than `package` so coverage is generated for the next stage. A single failing test fails the build. |
| 4 | **Code Quality (SonarQube Cloud)** | `sonar:sonar` with `-Dsonar.qualitygate.wait=true`. | Enforcement, not reporting. The build blocks until SonarQube Cloud computes the Quality Gate and fails if it is red — so new bugs, vulnerabilities or a coverage drop stop the release. |
| 5 | **Docker Build & Tag** | Multi-stage build; tagged both `<build>-<commit>` and `latest`, with the build metadata baked in as OCI labels and `ARG`s. | Produces the immutable deployment artifact. The image, not the source, is what is promoted from here on. |
| 6 | **Push to ACR** | `az login` with the service principal, `az acr login`, push both tags, then list the newest tags as evidence. | Publishes the artifact to cloud storage AKS can pull from. The SP holds only `AcrPush`, not registry ownership. |
| 7 | **Deploy to AKS** | `az aks get-credentials`, then `ansible-playbook deploy-app.yml` renders the manifests with this build's image tag (`k8s/render.sh` + `envsubst`) and runs `kubectl apply`. The rendered YAML is archived. | Deployment automation. Rendering from templates means the deployed manifest is reproducible and auditable; archiving it records exactly what was sent to the cluster. |
| 8 | **Verify Deployment** | `kubectl rollout status`, prints deployment/pods/service, waits for the Load Balancer IP, then curls `/actuator/health` and asserts that `/api/v1/info` reports *this* build's `imageTag`. | Closes the loop. Without this the pipeline would be "green" when `kubectl apply` succeeded but the pods crash-looped. The assertion makes a false success impossible. |

`post` blocks always run: on failure the pipeline dumps pod status and the
deployment description for diagnosis, and it always logs out of Azure.

### 3.1 How a failure is contained

| Failure | Stage that catches it | Effect |
|---|---|---|
| Committed API key | 2 | Build fails; no image built or published. |
| Broken unit test | 3 | Build fails; JUnit report shows which test. |
| New bug or coverage drop | 4 | Quality Gate red; build fails. |
| Bad `Dockerfile` | 5 | Build fails; nothing pushed. |
| Wrong Azure permissions | 6 | Build fails; cluster untouched, old version still serving. |
| Pod crashes on startup | 8 | `rollout status` times out; `maxUnavailable: 0` means the previous ReplicaSet kept serving throughout. |

---

## 4. Cloud resources and deployment approach

### 4.1 Azure resources

All resources live in one resource group, `rg-cicd-cia2`, so teardown is a
single command and cost is easy to attribute.

| Resource | Name | SKU / size | Role |
|---|---|---|---|
| Resource group | `rg-cicd-cia2` | — | Blast radius and cost boundary |
| Container registry | `acrcicdcia2` | Basic | Stores the tagged images |
| Kubernetes service | `aks-cicd-cia2` | Free tier control plane, 1 × `Standard_B2s` | Runs the workload |
| Virtual machine | `vm-jenkins` | `Standard_B2s`, Ubuntu 24.04 | Jenkins controller and build agent |
| Load Balancer + public IP | created by the `Service` | Standard | Public application endpoint |
| Service principal | `sp-cicd-cia2` | — | Jenkins identity in Azure |

`infra/azure-setup.sh` creates all of it, including
`az aks create --attach-acr`, which grants the cluster's managed identity
`AcrPull` so no image-pull secret is needed anywhere.

### 4.2 Kubernetes deployment design

Five manifests in `k8s/`:

- **Namespace** `cicd-demo` — isolates the workload from `kube-system`.
- **ConfigMap** — non-secret runtime settings plus the build provenance
  (`APP_IMAGE_TAG`, `APP_BUILD_NUMBER`, `APP_COMMIT_SHA`), which the application
  displays. This is what makes a redeployment visible in a browser.
- **Deployment** — 2 replicas; `RollingUpdate` with `maxSurge: 1` and
  **`maxUnavailable: 0`**, so a new pod must pass its readiness probe before an
  old one is removed. CPU/memory requests and limits are set so the scheduler
  can place pods and one container cannot starve the node. Three probes:
  `startupProbe` gives the JVM up to 150 s to warm up, `readinessProbe` gates
  traffic, `livenessProbe` restarts a wedged container. Hardened
  `securityContext`: non-root UID 10001, `readOnlyRootFilesystem: true` (with an
  `emptyDir` at `/tmp` for Tomcat), `allowPrivilegeEscalation: false`, all
  capabilities dropped, `seccompProfile: RuntimeDefault`.
- **Service** — `type: LoadBalancer`, port 80 → 8080. Azure provisions the
  public IP, which is the endpoint demonstrated in the browser.
- **HorizontalPodAutoscaler** — 2 to 5 replicas at 70% CPU, using the
  `metrics-server` AKS enables by default.

### 4.3 Deployment strategy

The manifests are templates: the image reference and build metadata are
`${...}` placeholders. `k8s/render.sh` substitutes only a named allow-list of
variables with `envsubst` and writes the result to `k8s/rendered/`, which the
pipeline archives as evidence. `ansible/deploy-app.yml` calls that script, runs
`kubectl apply`, waits for the rollout and reports the public IP.

Each build produces a new image tag, so the pod template changes on every
deploy and Kubernetes always performs a genuine rolling update — avoiding the
classic `latest`-tag trap where `kubectl apply` reports "unchanged" and nothing
is actually redeployed. Rollback is `kubectl rollout undo deployment/cicd-demo-app -n cicd-demo`,
and `kubernetes.io/change-cause` records the Jenkins build and commit for each
revision in `kubectl rollout history`.

---

## 5. Screenshots and test results

### 5.1 Local test evidence (verified)

```
[INFO] Tests run: 29, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

JaCoCo coverage from `target/site/jacoco/`:

| Counter | Covered | Missed | Coverage |
|---|---|---|---|
| Instruction | 290 | 13 | **95.7%** |
| Branch | 23 | 3 | **88.5%** |
| Line | 70 | 5 | 93.3% |
| Complexity | 29 | 3 | 90.6% |
| Method | 18 | 1 | 94.7% |
| Class | 8 | 0 | 100% |

Gitleaks was verified to both pass and fail correctly: a clean tree reports
`no leaks found`, and a planted fake SonarQube token plus a fake Azure client
secret produced `leaks found: 3`, confirming the gate is not a no-op.

### 5.2 Screenshots to attach

Place these in `docs/screenshots/` and reference them here:

| # | Screenshot | Shows |
|---|---|---|
| 1 | Azure portal — resource group contents | Cloud resources provisioned |
| 2 | Azure portal — AKS cluster overview | Kubernetes cluster running |
| 3 | ACR → Repositories → `cicd-demo-app` tags | Image published to the registry |
| 4 | `kubectl -n cicd-demo get deployment,pods,svc -o wide` | Pods `Running`, deployment ready, `EXTERNAL-IP` assigned |
| 5 | Browser at `http://<public-ip>` | Application reachable, build metadata visible |
| 6 | Jenkins **Stage View**, all 8 stages green | Successful pipeline execution |
| 7 | Jenkins console log, Gitleaks stage | Secret scan passed |
| 8 | SonarCloud dashboard, Quality Gate **Passed** | Static analysis gate |
| 9 | Jenkins test result trend | 29 tests passing |
| 10 | GitHub webhook **Recent Deliveries** (green tick) | Automatic trigger |
| 11 | Build *N* page, then build *N+1* auto-triggered by the push | Change demonstration |
| 12 | Browser before and after, showing the changed message and build number | Change visible at the endpoint |

### 5.3 Change and redeployment demonstration

1. Edit `APP_RELEASE_MESSAGE` in `k8s/01-configmap.yaml`.
2. `git commit -am "Demo: change the release message" && git push`.
3. GitHub delivers the webhook; Jenkins starts build *N+1* with no manual action.
4. Stages 2–4 pass; stage 5 builds image tag `N+1-<new-sha>`.
5. Stage 6 pushes it to ACR, where both tags are now listed.
6. Stage 7 rolls out; `kubectl get pods` shows new pods replacing old ones
   one at a time while the service keeps answering.
7. Stage 8 asserts that `/api/v1/info` reports `imageTag: N+1-<new-sha>`.
8. Refreshing the browser shows the new message and the new build number.

---

## 6. Challenges encountered and solutions

| # | Challenge | Root cause | Solution adopted |
|---|---|---|---|
| 1 | Maven was not installed on the build host, and installing it per-host makes builds non-reproducible. | Tool versions drift between machines. | Committed the **Maven wrapper**. `./mvnw` downloads the pinned Maven 3.9.9, so the build is identical everywhere. |
| 2 | `kubectl apply` reported "unchanged" and no new code was deployed. | The manifest referenced a mutable `latest` tag, so the pod template was byte-identical. | Tagged every image `<build-number>-<commit-sha>` and templated the tag into the manifest, guaranteeing a changed pod spec per build. |
| 3 | A green pipeline did not prove the application worked — `kubectl apply` succeeds even if the pods then crash-loop. | The pipeline verified the API call, not the outcome. | Added stage 8: `rollout status`, then a smoke test that asserts the live `/api/v1/info` reports *this* build's image tag. |
| 4 | `readOnlyRootFilesystem: true` made the container fail at startup. | Embedded Tomcat needs a writable temp directory. | Mounted an `emptyDir` volume at `/tmp`, keeping the rest of the filesystem read-only. |
| 5 | Ansible does not run natively on Windows. | No Windows control node support. | Ran the control node in **WSL Ubuntu**, and documented an alternative that executes the playbook on the VM with `-c local`. |
| 6 | Jenkins could not run `docker build` even though the `jenkins` user was in the `docker` group. | Group membership is read at process start. | Added an Ansible handler that restarts Jenkins whenever the user's groups change. |
| 7 | SonarQube Cloud rejected the pipeline's analysis. | The project defaulted to SonarCloud *Automatic Analysis*, which is mutually exclusive with CI-based analysis. | Switched the analysis method to "With Jenkins"; documented in the troubleshooting table. |
| 8 | Gitleaks flagged its own rule file and the test fixtures. | The config contains the detection patterns; tests use a fixed dummy SHA. | Added a **narrow, documented allowlist** (this file, the Maven wrapper, build output, screenshots, and obvious placeholder patterns) rather than lowering the rules. |
| 9 | Two replicas would not schedule on a single `Standard_B2s` node. | System pods plus 2 × 150 m CPU requests exceed 2 vCPU in some configurations. | Tuned requests down to 150 m CPU / 320 Mi, and documented `az aks scale --node-count 2` as the fix. |
| 10 | The service principal could not fetch cluster credentials. | `Contributor` does not include `listClusterAdminCredential`. | Granted the *Azure Kubernetes Service Cluster Admin Role* explicitly, scoped to the cluster only. |

---

## 7. Security considerations

**What this implementation does**

1. **Secret detection as a hard gate.** Gitleaks scans the full history on every
   build and fails it on any finding, so a leaked credential cannot reach the
   registry. Six custom rules cover the credential types this project actually
   handles: Azure storage connection strings, service-principal secrets,
   kubeconfig client keys, ACR admin passwords, SonarQube tokens and Jenkins API
   tokens.
2. **No credentials in Git.** `.gitignore` and `.dockerignore` both exclude
   `.env`, `*.pem`, `*.key`, `kubeconfig*` and `*-credentials.json`. Jenkins
   holds the four secrets in its credential store and injects them only inside
   `withCredentials` blocks, which mask them in the console log.
3. **Least privilege in Azure.** The service principal is scoped to one resource
   group with `Contributor`, plus `AcrPush` on the registry and Cluster Admin on
   the cluster — not subscription-wide. AKS pulls images with its own managed
   identity, so no registry password exists in the cluster.
4. **Hardened container.** Multi-stage build ships only a JRE; the process runs
   as non-root UID 10001 with a read-only root filesystem, no privilege
   escalation, all Linux capabilities dropped and the default seccomp profile.
5. **Static analysis as a gate.** The SonarQube Cloud Quality Gate blocks the
   build on new vulnerabilities, security hotspots and bugs.
6. **Provenance.** Every image carries OCI labels and environment variables
   naming its commit and Jenkins build, so anything running can be traced to
   source.
7. **Supply-chain pinning.** Base images are pinned to specific tags, the Maven
   version is pinned by the wrapper, and the Gitleaks version is pinned in the
   Ansible playbook.

**Known limitations** (honest scope boundaries for a coursework build)

| # | Limitation | Risk | Production remedy |
|---|---|---|---|
| 1 | Jenkins is served over **HTTP on port 8080** with a public IP. | Credentials and webhook payloads travel in clear text. | Terminate TLS on an Azure Application Gateway or nginx with a Let's Encrypt certificate; restrict the NSG to known source IPs. |
| 2 | The application endpoint is **HTTP only**. | No transport encryption. | Add an ingress controller with TLS, or Azure Front Door. |
| 3 | A **long-lived service principal secret** is stored in Jenkins. | A stolen secret is valid until manually rotated. | Use a VM **managed identity** or OIDC workload-identity federation — no stored secret at all. |
| 4 | AKS uses **`--admin` (local account) credentials**. | Certificate-based cluster-admin bypasses Entra ID RBAC. | Disable local accounts, enable Entra ID integration with `kubelogin`, and bind the pipeline identity to a narrow `Role` instead of cluster-admin. |
| 5 | **No container image vulnerability scan.** | A base-image CVE could ship undetected. | Add a Trivy or `az acr` scan stage that fails on HIGH/CRITICAL findings. |
| 6 | **No image signing or SBOM.** | Image provenance cannot be cryptographically verified. | Sign with Cosign and generate a Syft SBOM, enforced by an admission policy. |
| 7 | **Single-node cluster, single Jenkins host.** | No high availability; the node or the VM is a single point of failure. | Multi-node pool across availability zones; Jenkins controller with agents, or a managed CI service. |
| 8 | **No network policies**; pods can talk to anything. | Lateral movement after a compromise. | Enable Azure or Calico network policy with default-deny egress. |
| 9 | **No staging environment or approval gate** — `main` goes straight to the single environment. | A bad change reaches the only running instance. | Separate dev/staging/production namespaces or clusters with a manual approval before production. |
| 10 | Secrets would sit in **Kubernetes Secrets** (base64, not encrypted) if the app needed any. | Readable by anyone with namespace read access. | Azure Key Vault with the Secrets Store CSI driver and workload identity. |

---

## 8. Conclusion

The pipeline replaces a manual, unreproducible release process with eight
automated stages that run on every push to `main`. A developer's only action is
`git push`; roughly five minutes later a uniquely tagged, scanned, tested and
statically analysed container image is running on Azure Kubernetes Service
behind a public endpoint, and the pipeline has proved it by querying that
endpoint.

The two added gates are what make the automation safe rather than merely fast.
Gitleaks ensures the speed-up does not also accelerate credential leaks, and the
SonarQube Cloud Quality Gate ensures it does not accelerate defects. Both fail
the build rather than filing a report, which is the difference between a gate
and a dashboard.

The design choices that mattered most were small and specific: tagging images
with `<build>-<commit>` instead of `latest`, which is what makes rolling updates
actually roll; setting `maxUnavailable: 0`, which is what makes them
zero-downtime; and asserting the deployed image tag at the live endpoint, which
is what makes a green build trustworthy.

---

## Appendix A — Key files

| File | Purpose |
|---|---|
| `Jenkinsfile` | The 8-stage declarative pipeline |
| `pom.xml` | Maven build, JaCoCo, SonarQube configuration |
| `Dockerfile` | Multi-stage image, non-root runtime |
| `.gitleaks.toml` | Secret-scanning rules and documented allowlist |
| `k8s/*.yaml`, `k8s/render.sh` | Kubernetes manifests and the renderer |
| `ansible/jenkins-setup.yml` | Provisions the Jenkins VM (configuration management) |
| `ansible/deploy-app.yml` | Renders and applies the manifests (deployment automation) |
| `infra/azure-setup.sh` | Creates every Azure resource |
| `infra/azure-teardown.sh` | Deletes them again |
| `docs/SETUP.md` | Step-by-step runbook with troubleshooting |

## Appendix B — Commands used in the viva

```bash
kubectl -n cicd-demo get deployment,pods,svc -o wide
kubectl -n cicd-demo rollout history deployment/cicd-demo-app
kubectl -n cicd-demo describe pod -l app.kubernetes.io/name=cicd-demo-app | head -40
kubectl -n cicd-demo logs -l app.kubernetes.io/name=cicd-demo-app --tail=30
az acr repository show-tags --name acrcicdcia2 --repository cicd-demo-app --orderby time_desc --output table
curl -s http://<public-ip>/api/v1/info
kubectl -n cicd-demo rollout undo deployment/cicd-demo-app   # rollback
```
