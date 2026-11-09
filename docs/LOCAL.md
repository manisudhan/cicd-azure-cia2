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
| Stage 8 (verify) | smoke-tests the Service from inside the cluster | smoke-tests the public LoadBalancer IP |
| Browser access | `http://localhost` (LoadBalancer on host port 80) | the LoadBalancer's public IP |
| Azure account | not needed | required |
| Cost | $0 | ~$2.05/day |

**Why stage 6 is skipped.** Docker Desktop's Kubernetes can read the Docker image
store of the daemon that builds the image, so the image produced in stage 5 is
already visible to the cluster. The Deployment already specifies
`imagePullPolicy: IfNotPresent`, so Kubernetes uses the local image instead of
trying to pull it. A local registry would add a moving part for no benefit.

This was verified rather than assumed: an image tagged `local-probe:v1` — a tag
that exists nowhere on Docker Hub — was built locally and scheduled into the
cluster. Kubernetes reported `Successfully pulled image "local-probe:v1" in
944ms` and the pod reached `Running`, which it could only do from the local
store.

**The LoadBalancer works, but it needs host port 80 free.** Docker Desktop's
`cloud-provider-kind` publishes a `type: LoadBalancer` Service on the host, so
after a successful build the app is browsable at **<http://localhost>** with no
port-forward.

There is a trap worth knowing about, because it cost time here. A first probe
using a Service on port **8080** left `EXTERNAL-IP <pending>` and logged
`failed to create containers kindccm-... exit status 125`. That looked like a
broken controller, but the real cause was that the host's port 8080 was already
taken by an unrelated native Jenkins installation, so the load balancer
container could not bind its published port. The application Service uses port
80, which was free, and it received its address normally. If host port 80 is
also occupied on your machine, the same `<pending>` symptom appears — use a
port-forward in that case (step 6).

Stage 8 nevertheless smoke-tests the Service from *inside* the cluster, with a
short-lived `curlimages/curl` pod hitting
`http://cicd-demo-app.cicd-demo.svc.cluster.local/api/v1/info`. That is
deliberate: it does not depend on a host port being free, and from inside the
Jenkins container `localhost` is the container rather than the host. It still
proves the Service routes traffic to a ready pod serving this exact build,
which is the thing worth proving.

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

Open <http://localhost:8090>, unlock it, choose **Select plugins to install →
None** (they are baked into the image), and create your admin user.

---

## 3. Connect Jenkins to the local cluster

```bash
bash infra/local-connect.sh
```

This gets the Jenkins container talking to the cluster. Three things are worth
being able to explain in the viva, because each was a real obstacle:

- **The container has to join the `kind` network.** Docker Desktop's Kubernetes
  is kind-based: the control plane runs as a container on a Docker network
  called `kind`, and its API server is published on the **host's loopback
  only**. So `host.docker.internal:6443` is refused from inside a container —
  there is nothing listening on the host gateway address. The script attaches
  the Jenkins container to that network instead.
- **The node is addressed by name, not IP.** The server field becomes
  `https://desktop-control-plane:6443`. That name resolves over the `kind`
  network's DNS, and — importantly — it is in the API server certificate's SAN
  list, so **TLS verification stays fully enabled**. Using the node's IP would
  have forced `--insecure-skip-tls-verify`; using the name avoids that.
- **`kubectl config set`, not `kubectl config set-cluster`.** `set-cluster`
  rewrites every flag-backed field, so calling it to change the server silently
  drops the `certificate-authority-data` the CA check needs. `config set`
  changes exactly one field.

The script ends by running `kubectl get nodes` from inside the container, so you
know the connection works before starting a build.

Re-run it whenever you recreate the Jenkins container or reset the Docker
Desktop cluster: the network attachment and the kubeconfig live in the
container, not in the image.

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
| 8 Verify | in-cluster smoke test passes, `imageTag` matches the build |

```bash
kubectl -n cicd-demo get deployment,pods,svc -o wide
```

You should see `2/2` ready pods and an `EXTERNAL-IP` on the Service.

Open <http://localhost>. The landing page shows the build number, commit and the
pod that served you — refresh a few times and the pod name alternates between
the two replicas, demonstrating the Service load-balancing.

If the Service shows `EXTERNAL-IP <pending>`, something else holds host port 80.
Use a port-forward instead (leave it running in its own terminal):

```bash
kubectl port-forward -n cicd-demo svc/cicd-demo-app 8081:80
```

Then open <http://localhost:8081>. Port 8081 stays clear of 8080, which a
separately installed native Jenkins may already occupy.

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
| LoadBalancer | `cloud-provider-kind`, published on host port 80 | Azure Standard Load Balancer with a public IP | Works locally at `http://localhost`, but it is bound to this machine only — not reachable from another device, so the public-endpoint evidence is still stronger from Azure |
| TLS to API server | verification skipped | fully verified | Local only; noted in the report's security limitations |

The screenshots in `docs/screenshots/README.md` that specifically require
Azure — the resource group, the AKS blade and the ACR tag list — can only be
captured once the subscription is live. Everything else can be captured now.
