# Screenshot evidence checklist

Save each screenshot here with the filename shown, then reference it from
`docs/REPORT.md` section 5.2.

## Cloud resources

| File | Capture |
|---|---|
| `01-resource-group.png` | Azure portal → `rg-cicd-cia2` → Overview, listing the ACR registry and the AKS cluster |
| `02-aks-cluster.png` | Azure portal → `aks-cicd-cia2` → Overview, status **Succeeded / Running** |
| `03-acr-tags.png` | ACR → Repositories → `cicd-demo-app`, showing at least two build tags |

## Kubernetes

| File | Capture |
|---|---|
| `04-kubectl-get-all.png` | `kubectl -n cicd-demo get deployment,pods,svc -o wide` — pods `Running`, deployment `2/2`, `EXTERNAL-IP` present |
| `05-rollout-history.png` | `kubectl -n cicd-demo rollout history deployment/cicd-demo-app` — change-cause per revision |

## Application

| File | Capture |
|---|---|
| `06-browser-app.png` | Browser at `http://<public-ip>` showing image tag, build number, commit and pod name |
| `07-api-info.png` | `http://<public-ip>/api/v1/info` JSON response |

## Pipeline

| File | Capture |
|---|---|
| `08-jenkins-stage-view.png` | Jenkins job page, Stage View with all 8 stages green |
| `08b-jenkins-toolchain.png` | `docker compose exec jenkins cat /usr/local/share/toolchain.txt` — the agent's pinned tool versions |
| `09-gitleaks-log.png` | Console log of stage 2 — `no secrets detected in git history` |
| `10-test-results.png` | Jenkins test result trend / `Tests run: 29, Failures: 0` |
| `11-sonarcloud.png` | SonarCloud dashboard, Quality Gate **Passed**, coverage shown |
| `12-auto-trigger.png` | The job's **Git Polling Log** showing a change was detected, or — if you ran the Cloudflare tunnel — GitHub → Settings → Webhooks → Recent Deliveries with a green tick |

## Change demonstration

| File | Capture |
|---|---|
| `13-before.png` | Browser before the change — note the release message and build number |
| `14-commit-push.png` | Terminal showing `git commit` and `git push` |
| `15-auto-triggered.png` | Jenkins showing the next build started by the webhook, not manually |
| `16-after.png` | Browser after the rollout — changed message and incremented build number |
