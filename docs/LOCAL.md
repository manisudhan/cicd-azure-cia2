# Running the full pipeline without an Azure subscription

This path proves all eight pipeline stages end to end against **Docker
Desktop's built-in Kubernetes**. Nothing in Azure is needed, and nothing is
wasted: switching to ACR + AKS later is a single parameter change
(`DEPLOY_TARGET = azure`), not new work.

Use it when the Azure subscription is not available yet, or to iterate quickly
without paying for cluster time.

| | `DEPLOY_TARGET=local` | `DEPLOY_TARGET=azure` |
|---|---|---|
| Stages 1–5 | identical | identical |
| Stage 6 (push to registry) | skipped — see below | pushes to ACR |
| Stage 7 (deploy) | Docker Desktop Kubernetes | AKS |
| Stage 8 (verify) | smoke-tests `http://localhost` | smoke-tests the LoadBalancer IP |
| Azure account | not needed | required |
| Cost | $0 | ~$2.05/day |

**Why stage 6 is skipped.** Docker Desktop's Kubernetes shares the Docker image
store with the daemon that builds the image, so the image produced in stage 5 is
already visible to the cluster. The Deployment already specifies
`imagePullPolicy: IfNotPresent`, so Kubernetes uses the local image instead of
trying to pull it. A local registry would add a moving part for no benefit.

---

## 1. Enable Kubernetes in Docker Desktop

Start Docker Desktop from the Start menu (it needs an admin prompt the first
time), then:

**Settings → Kubernetes → Enable Kubernetes → Apply & Restart**

It downloads and starts a single-node control plane — a few minutes. Confirm:

```bash
kubectl config use-context docker-desktop && kubectl get nodes
```

You should see one node in `Ready` state.

---

## 2. Start Jenkins

```bash
docker compose up -d --build
```

```bash
docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Open <http://localhost:8080>, unlock it, choose **Select plugins to install →
None** (they are baked into the image), and create your admin user.

---

## 3. Connect Jenkins to the local cluster

```bash
bash infra/local-connect.sh
```

This copies your kubeconfig into the Jenkins container and repoints the API
server address. Two things need explaining for the viva:

- The host kubeconfig points at `https://127.0.0.1:6443`. Inside a container
  `127.0.0.1` is the *container*, so the script rewrites it to
  `host.docker.internal`, which is how a container addresses its host.
- Docker Desktop's API server certificate is issued for `127.0.0.1` and
  `kubernetes.docker.internal`, not for `host.docker.internal`, so the script
  sets `--insecure-skip-tls-verify` **for this local cluster only**. The Azure
  target is unaffected: it gets a fresh, fully verified kubeconfig from
  `az aks get-credentials`.

The script ends by running `kubectl get nodes` from inside the container, so you
know the connection works before you start a build.

Re-run it if you ever reset the Docker Desktop cluster — the client certificate
changes.

---

## 4. Set up SonarQube Cloud

This works without Azure, so do it now — it is a graded deliverable.

1. <https://sonarcloud.io> → sign in **with GitHub**.
2. Create a free organisation, import `cicd-azure-cia2`.
3. Analysis method → **With Jenkins** (this disables Automatic Analysis, which
   would otherwise reject the pipeline's analysis).
4. Note the organisation key and project key; create a token under
   **My Account → Security**.
5. Put the two keys into `Jenkinsfile` (`SONAR_ORG`, `SONAR_PROJECT_KEY`),
   commit and push.
6. Add the token to Jenkins as a **Secret text** credential with ID
   `sonarcloud-token`.

If you want a green build before SonarCloud is wired up, untick **RUN_SONAR**
on the first run — but tick it again before collecting evidence.

---

## 5. Create the Jenkins job

**New Item → Pipeline**, name `cicd-demo-app`:

- Build Triggers → **Poll SCM** (the schedule comes from the `Jenkinsfile`)
- Pipeline → **Pipeline script from SCM** → Git
- Repository URL: `https://github.com/manisudhan/cicd-azure-cia2.git`
- Branch `*/main`, Script Path `Jenkinsfile`
- Save

The first run registers the parameters, so **Build Now** may run with defaults
before **Build with Parameters** appears. `DEPLOY_TARGET` defaults to `local`,
which is what you want.

---

## 6. Run it

**Build with Parameters** → `DEPLOY_TARGET = local` → **Build**.

Expected:

| Stage | Expected result |
|---|---|
| 1 Checkout | image tag `<build>-<commit>`, no registry prefix |
| 2 Gitleaks | `no secrets detected in git history` |
| 3 Build & Test | `Tests run: 29, Failures: 0` |
| 4 SonarQube Cloud | Quality Gate **Passed** |
| 5 Docker Build | `Built [cicd-demo-app:<tag> cicd-demo-app:latest]` |
| 6 Push to ACR | **skipped** (`DEPLOY_TARGET` is not `azure`) |
| 7 Deploy | Ansible applies 5 manifests, rollout completes |
| 8 Verify | smoke test passes, `imageTag` matches the build |

Then open <http://localhost> — the landing page shows the build number, commit
and the pod that served you.

```bash
kubectl -n cicd-demo get deployment,pods,svc -o wide
```

---

## 7. Prove a change flows through

```bash
sed -i 's/APP_RELEASE_MESSAGE: .*/APP_RELEASE_MESSAGE: "Release 2 - shipped automatically by Jenkins"/' k8s/01-configmap.yaml
```

```bash
git commit -am "Demo: change the release message" && git push
```

Within two minutes Jenkins starts a build on its own. Refresh
<http://localhost> and the message and build number change, with no downtime
because the Deployment uses `maxUnavailable: 0`.

---

## 8. Switching to Azure later

Once the subscription is active:

```bash
bash infra/azure-setup.sh
```

Add the three Azure credentials to Jenkins, then run **Build with Parameters →
`DEPLOY_TARGET = azure`**. Stages 1–5 behave identically; stage 6 starts
pushing to ACR and stages 7–8 target AKS.

Nothing in the application, the Dockerfile, the manifests or the Ansible
playbook changes — which is itself a useful point for the report: the pipeline
is portable across clusters because the only environment-specific parts are the
image reference and the kubeconfig.

---

## Differences from the Azure target, for the report

| Aspect | Local | Azure | Consequence |
|---|---|---|---|
| Registry | none (shared image store) | ACR | Local cannot prove the registry deliverable — Azure evidence is still required for that |
| Node count | 1 (your machine) | 1 × `Standard_B2s` | Same scheduling constraints |
| `metrics-server` | not installed | installed by default | The HPA applies but reports `<unknown>` locally and will not scale |
| LoadBalancer | Docker Desktop publishes on `localhost` | Azure Standard Load Balancer with a public IP | Local endpoint is not reachable from another machine |
| TLS to API server | verification skipped | fully verified | Local only; noted in the report's security limitations |

The screenshots in `docs/screenshots/README.md` that specifically require
Azure — the resource group, the AKS blade and the ACR tag list — can only be
captured once the subscription is live. Everything else can be captured now.
