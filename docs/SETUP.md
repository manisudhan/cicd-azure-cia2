# Setup Runbook

Follow these steps in order. Expect about 60–90 minutes end to end, most of it
waiting for Azure to create the AKS cluster.

---

## 0. Prerequisites on your laptop

| Tool | Check | Install on Windows |
|---|---|---|
| Git | `git --version` | already installed |
| Java 21 | `java -version` | already installed |
| Docker Desktop | `docker info` | already installed — **start it** |
| kubectl | `kubectl version --client` | already installed |
| Azure CLI | `az version` | `winget install Microsoft.AzureCLI` |
| GitHub CLI | `gh --version` | `winget install GitHub.cli` |
| Ansible | `ansible --version` | runs in WSL — see step 3 |

Maven is **not** required: the repository ships the Maven wrapper (`./mvnw`).

---

## 1. Push the repository to GitHub

```bash
gh auth login
```

```bash
cd /c/Users/mmani/Downloads/CICD && gh repo create cicd-azure-cia2 --public --source=. --remote=origin --push
```

The repository must be **public** so that SonarQube Cloud analysis is free and
your instructor can access it.

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
| Container registry | `acrcicdcia2` | Basic SKU |
| AKS cluster | `aks-cicd-cia2` | 1 × `Standard_B2s`, free control plane, `AcrPull` granted |
| Jenkins VM | `vm-jenkins` | Ubuntu 24.04, `Standard_B2s`, port 8080 open |
| Service principal | `sp-cicd-cia2` | `Contributor` on the group, `AcrPush`, AKS Cluster Admin |

> **ACR names are globally unique.** If `acrcicdcia2` is taken, rerun with
> `ACR_NAME=acrcicdcia2<yourinitials> bash infra/azure-setup.sh` and update the
> same value in `Jenkinsfile` and `ansible/deploy-app.yml`.

**Copy the service principal `appId`, `password` and `tenant` from the output
now** — the password is shown only once. Do not paste them into any file in the
repository; Gitleaks will fail the build.

---

## 3. Configure the Jenkins VM with Ansible

Ansible does not run natively on Windows, so use WSL:

```bash
wsl --install -d Ubuntu
```

Inside WSL:

```bash
sudo apt update && sudo apt install -y ansible openssh-client
```

Copy the SSH key Azure generated, put the VM's public IP into the inventory,
and run the playbook:

```bash
cp -r /mnt/c/Users/$USER/.ssh ~/ && chmod 600 ~/.ssh/id_rsa
```

```bash
cd /mnt/c/Users/mmani/Downloads/CICD/ansible && sed -i "s/VM_PUBLIC_IP/<your-vm-public-ip>/" inventory.ini
```

```bash
ansible-playbook -i inventory.ini jenkins-setup.yml
```

The playbook installs Java 21, Jenkins, Docker, kubectl, Azure CLI, Gitleaks
and Ansible, adds the `jenkins` user to the `docker` group, and prints the
Jenkins initial admin password.

> **Alternative without WSL:** SSH to the VM, `sudo apt install -y ansible git`,
> clone this repository there, then
> `ansible-playbook -i "localhost," -c local ansible/jenkins-setup.yml`.

---

## 4. Set up SonarQube Cloud

1. Go to <https://sonarcloud.io> and sign in **with GitHub**.
2. Create an organisation (free plan) and import the `cicd-azure-cia2` repository.
3. Choose **"With Jenkins"** as the analysis method, which disables SonarCloud's
   own automatic analysis — required, otherwise the pipeline's analysis is rejected.
4. Note your **organisation key** and **project key**.
5. Create a token: avatar → **My Account → Security → Generate Token**.

Update the two keys in `Jenkinsfile`:

```groovy
SONAR_ORG         = 'your-org-key'
SONAR_PROJECT_KEY = 'your-org-key_cicd-azure-cia2'
```

The same keys also appear in `pom.xml` as defaults; the pipeline overrides them
on the command line, so editing the `Jenkinsfile` is sufficient.

---

## 5. Configure Jenkins

Open `http://<vm-public-ip>:8080`.

1. Unlock with the initial admin password, choose **Install suggested plugins**,
   and create your admin user.
2. **Manage Jenkins → Plugins → Available** — install, then restart:
   - *Pipeline*, *Git*, *GitHub*, *Credentials Binding*, *JUnit*, *Timestamper*
3. **Manage Jenkins → Credentials → System → Global credentials** — add:

   | ID | Kind | Value |
   |---|---|---|
   | `azure-sp` | Username with password | username = SP `appId`, password = SP `password` |
   | `azure-tenant-id` | Secret text | the `tenant` GUID |
   | `azure-subscription-id` | Secret text | `az account show --query id -o tsv` |
   | `sonarcloud-token` | Secret text | the SonarCloud token from step 4 |

   The IDs must match exactly — the `Jenkinsfile` looks them up by ID.

4. **New Item → Pipeline**, name it `cicd-demo-app`:
   - Build Triggers → tick **GitHub hook trigger for GITScm polling**
   - Pipeline → **Pipeline script from SCM** → SCM **Git**
   - Repository URL: `https://github.com/<you>/cicd-azure-cia2.git`
   - Branch: `*/main`, Script Path: `Jenkinsfile`
   - Save.

---

## 6. Add the GitHub webhook

In the GitHub repository: **Settings → Webhooks → Add webhook**

- Payload URL: `http://<vm-public-ip>:8080/github-webhook/`
- Content type: `application/json`
- Event: *Just the push event*

A green tick under **Recent Deliveries** confirms it works. The pipeline also
polls SCM every five minutes as a fallback.

---

## 7. Run the pipeline

Click **Build Now** for the first run, then push a commit to see the webhook
trigger it automatically.

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

Watch the build start by itself, then refresh the browser: the message and the
build number change while the service stays up, because the deployment uses
`maxUnavailable: 0`.

---

## 9. Collect the screenshots

Save these into `docs/screenshots/` — see that folder's README for the list.

---

## 10. Shut down to protect your credits

```bash
az aks stop --resource-group rg-cicd-cia2 --name aks-cicd-cia2 && az vm deallocate --resource-group rg-cicd-cia2 --name vm-jenkins
```

```bash
bash infra/azure-teardown.sh
```

---

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `docker: permission denied` in stage 5 | The `jenkins` user was added to `docker` but Jenkins was not restarted: `sudo systemctl restart jenkins`. |
| Stage 4 fails with *"Project was already analysed by SonarCloud Automatic Analysis"* | Turn off Automatic Analysis in the SonarCloud project's **Administration → Analysis Method**. |
| Stage 6 `unauthorized: authentication required` | The service principal lacks `AcrPush`, or `ACR_NAME` in the `Jenkinsfile` does not match the real registry. |
| Stage 7 `az aks get-credentials` forbidden | The SP needs the *Azure Kubernetes Service Cluster Admin Role*; `azure-setup.sh` grants it. |
| Pods stuck `ImagePullBackOff` | AKS was not attached to ACR: `az aks update -g rg-cicd-cia2 -n aks-cicd-cia2 --attach-acr acrcicdcia2`. |
| Service `EXTERNAL-IP` stays `<pending>` | Azure takes 2–5 minutes to create the Load Balancer; the pipeline waits up to 5 minutes. |
| Pods `Pending` with *Insufficient cpu* | One `B2s` node cannot host 2 replicas plus system pods: `az aks scale -g rg-cicd-cia2 -n aks-cicd-cia2 --node-count 2`. |
| Webhook never fires | NSG port 8080 closed, or the payload URL is missing the trailing slash in `/github-webhook/`. |
