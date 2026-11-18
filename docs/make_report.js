const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  PageBreak, LevelFormat, convertInchesToTwip,
} = require("docx");

const OUT = process.argv[2] || "report.docx";
const W = 9026;                      // usable width on A4 with 1" margins (DXA)
const MONO = "Consolas";
const BODY = "Calibri";

const INK = "1A1A1A";
const ACCENT = "1D4ED8";
const CODEBG = "F2F2F2";
const PLACEBG = "FFF8E1";
const EVIDBG = "EAF3EA";

/* ---------------------------------------------------------------- helpers */

const p = (text, opts = {}) =>
  new Paragraph({
    spacing: { after: opts.after === undefined ? 120 : opts.after, line: 276 },
    alignment: opts.align,
    children: [new TextRun({ text, font: BODY, size: 21, color: INK, bold: opts.bold, italics: opts.italics })],
  });

/* rich paragraph: array of [text, {bold,italics,mono}] */
const rp = (parts, opts = {}) =>
  new Paragraph({
    spacing: { after: opts.after === undefined ? 120 : opts.after, line: 276 },
    children: parts.map(([t, o = {}]) =>
      new TextRun({
        text: t, font: o.mono ? MONO : BODY, size: o.mono ? 18 : 21,
        color: INK, bold: o.bold, italics: o.italics,
      })),
  });

const bullet = (text) =>
  new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 70, line: 276 },
    children: [new TextRun({ text, font: BODY, size: 21, color: INK })],
  });

const numbered = (text) =>
  new Paragraph({
    numbering: { reference: "numbers", level: 0 },
    spacing: { after: 70, line: 276 },
    children: [new TextRun({ text, font: BODY, size: 21, color: INK })],
  });

/* monospace evidence block, one Paragraph per line, shaded cell */
function block(lines, bg) {
  const rows = lines.map((l) =>
    new Paragraph({
      spacing: { after: 0, line: 230 },
      children: [new TextRun({ text: l === "" ? " " : l, font: MONO, size: 17, color: INK })],
    }));
  return new Table({
    columnWidths: [W],
    width: { size: W, type: WidthType.DXA },
    rows: [new TableRow({
      children: [new TableCell({
        width: { size: W, type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, fill: bg || CODEBG },
        margins: { top: 120, bottom: 120, left: 160, right: 160 },
        children: rows,
      })],
    })],
  });
}

const evidence = (lines) => block(lines, EVIDBG);

/* screenshot placeholder box */
function shot(id, title, how) {
  return new Table({
    columnWidths: [W],
    width: { size: W, type: WidthType.DXA },
    rows: [new TableRow({
      children: [new TableCell({
        width: { size: W, type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, fill: PLACEBG },
        margins: { top: 200, bottom: 200, left: 180, right: 180 },
        borders: {
          top: { style: BorderStyle.DASHED, size: 6, color: "C9A227" },
          bottom: { style: BorderStyle.DASHED, size: 6, color: "C9A227" },
          left: { style: BorderStyle.DASHED, size: 6, color: "C9A227" },
          right: { style: BorderStyle.DASHED, size: 6, color: "C9A227" },
        },
        children: [
          new Paragraph({
            spacing: { after: 60 },
            children: [new TextRun({ text: `[ PASTE SCREENSHOT ${id} HERE ]`, font: BODY, size: 21, bold: true, color: "8A6D00" })],
          }),
          new Paragraph({
            spacing: { after: 40 },
            children: [new TextRun({ text: title, font: BODY, size: 20, bold: true, color: INK })],
          }),
          new Paragraph({
            spacing: { after: 0 },
            children: [new TextRun({ text: how, font: BODY, size: 19, italics: true, color: "555555" })],
          }),
        ],
      })],
    })],
  });
}

const spacer = (h) => new Paragraph({ spacing: { after: h === undefined ? 160 : h }, children: [] });

/* table from rows; widths are fractions summing to 1 */
function table(header, rows, fractions) {
  const cols = fractions.map((f) => Math.round(W * f));
  const mkCell = (text, isHeader, width) =>
    new TableCell({
      width: { size: width, type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill: isHeader ? ACCENT : "FFFFFF" },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: [new Paragraph({
        spacing: { after: 0, line: 250 },
        children: [new TextRun({
          text, font: BODY, size: 19,
          bold: isHeader, color: isHeader ? "FFFFFF" : INK,
        })],
      })],
    });
  return new Table({
    columnWidths: cols,
    width: { size: W, type: WidthType.DXA },
    rows: [
      new TableRow({ tableHeader: true, children: header.map((h, i) => mkCell(h, true, cols[i])) }),
      ...rows.map((r) => new TableRow({ children: r.map((c, i) => mkCell(c, false, cols[i])) })),
    ],
  });
}

const h1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: t })] });
const h2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: t })] });

/* ------------------------------------------------------------------ body */

const kids = [];

/* --- title page --- */
kids.push(
  spacer(1800),
  new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { after: 120 },
    children: [new TextRun({ text: "Design and Implementation of an", font: BODY, size: 36, bold: true, color: INK })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { after: 120 },
    children: [new TextRun({ text: "End-to-End Cloud-Based CI/CD Pipeline", font: BODY, size: 36, bold: true, color: INK })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { after: 600 },
    children: [new TextRun({ text: "on Microsoft Azure", font: BODY, size: 30, color: ACCENT })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { after: 400 },
    children: [new TextRun({ text: "CIA-2  |  Technical Report", font: BODY, size: 24, color: "555555" })],
  }),
  spacer(400),
  table(
    ["Item", "Value"],
    [
      ["Student", "<your name and registration number>"],
      ["Course / Subject", "<course code and name>"],
      ["Date of submission", "<date>"],
      ["Cloud provider", "Microsoft Azure"],
      ["CI/CD platform", "Jenkins (declarative pipeline, containerised)"],
      ["Source repository", "github.com/manisudhan/cicd-azure-cia2"],
      ["Container registry", "acrcicdcia2.azurecr.io"],
      ["Kubernetes cluster", "aks-cicd-cia2 (AKS, Kubernetes 1.36)"],
      ["Application endpoint", "http://cicd-demo-cia2.centralindia.cloudapp.azure.com"],
      ["Code quality", "sonarcloud.io — project manisudhan_cicd-azure-cia2"],
    ],
    [0.3, 0.7]),
  new Paragraph({ children: [new PageBreak()] }),
);

/* --- 1 problem --- */
kids.push(
  h1("1. Problem Definition"),
  p("A development team builds and releases a Java web application manually. A developer compiles the code locally, runs the tests when they remember to, builds a container image with an ad-hoc tag, and copies it to a server by hand. The process is not merely inconvenient; it fails in four specific, separable ways."),
  numbered("Not reproducible. The artifact depends on whichever JDK, build-tool version and local configuration that particular developer happened to have installed. The claim “it works on my machine” cannot be disproved, because no two machines are known to be identical."),
  numbered("Error-prone. Every step is optional in practice. Under deadline pressure the test run is the first thing skipped, and an untested build reaches users without anything recording that it was untested."),
  numbered("Serialising. One person owns the deployment, so every release queues behind that person’s availability, and knowledge of the procedure stays with them."),
  numbered("Untraceable. With image tags such as latest or v2-final, nobody can state which commit is running in production. Rollback therefore becomes guesswork rather than a decision."),
  p("The objective of this work is to replace that process with an automated pipeline triggered by a push to the source repository, which builds the application, runs its tests, produces a uniquely identified container image, publishes it to a cloud registry, deploys it to a managed Kubernetes cluster, and then verifies that the new version is genuinely serving traffic."),
  rp([["Two quality gates were added beyond the stated requirement: ", {}], ["Gitleaks", { bold: true }], [" for secret detection and ", {}], ["SonarQube Cloud", { bold: true }], [" for static analysis. The reasoning is that an automated pipeline which ships defects or leaked credentials faster is not an improvement over a manual one. Automation multiplies whatever it is given, so the gates exist to ensure what is multiplied is correct.", {}]]),

  h2("1.1 Architecture"),
  block([
    "  Developer",
    "     | git push",
    "     v",
    "  GitHub (public repository)  <--- polled every 2 min ---+",
    "                                                         |",
    "                                            Jenkins (containerised)",
    "                                                         |",
    "     +---------------------------------------------------+",
    "     |  Declarative pipeline, 8 stages",
    "     v",
    "  1 Checkout       git metadata -> IMAGE_TAG = <build>-<commit>",
    "  2 Gitleaks       secret scan over FULL git history    [security gate]",
    "  3 Maven          compile, 29 unit tests, JaCoCo coverage",
    "  4 SonarQube      static analysis + Quality Gate wait  [quality gate]",
    "  5 Docker build   multi-stage image, tagged <build>-<commit>",
    "  6 Push to ACR    acrcicdcia2.azurecr.io",
    "  7 Deploy         Ansible renders manifests, kubectl apply",
    "  8 Verify         rollout status + HTTP smoke test on the endpoint",
    "     |",
    "     +--> Azure Container Registry --(AcrPull, managed identity)--> AKS",
    "                                                                    |",
    "                                            Azure Load Balancer (public IP)",
    "                                                                    |",
    "                                                                 Browser",
  ]),
  spacer(),
  p("Trust boundaries: GitHub and SonarQube Cloud are external SaaS platforms. The container registry and the Kubernetes cluster sit inside a single Azure resource group. Jenkins authenticates to Azure using a service principal scoped to that resource group alone.", { after: 60 }),
  spacer(),
  shot("1", "Architecture diagram (optional)",
    "If you drew your own diagram, paste it here and delete the text version above. Otherwise keep the text diagram, which is accurate."),
  new Paragraph({ children: [new PageBreak()] }),
);

/* --- 2 tools --- */
kids.push(
  h1("2. Tools Selected and Justification"),
  p("Each choice is recorded with the problem it solves and the alternative that was rejected, because a justification that names no alternative is not a justification."),
  table(
    ["Tool", "Role", "Why this one"],
    [
      ["Git / GitHub", "Source control, build trigger", "Required by the brief. A public repository satisfies instructor access, unlocks the free SonarQube Cloud tier, and supports both webhooks and polling."],
      ["Maven + wrapper", "Build and test", "Declarative pom.xml. The committed wrapper pins Maven 3.9.9, so the build agent needs no Maven installed — removing an entire class of version-drift failure."],
      ["JUnit 5 + JaCoCo", "Testing and coverage", "29 tests covering service logic, configuration binding and both controllers. JaCoCo produces the XML report SonarQube consumes."],
      ["Gitleaks", "Secret detection", "Scans the full git history rather than the working tree, so a credential committed and later deleted is still found. Single static binary, ~170 built-in rules."],
      ["SonarQube Cloud", "Static analysis", "Hosted, so no server to patch or back up. Free for public repositories. Enforces a Quality Gate the build waits on."],
      ["Docker (multi-stage)", "Containerisation", "Build stage carries the JDK and Maven; runtime stage carries only a JRE. Published image ~190 MB instead of ~600 MB, with a correspondingly smaller CVE surface."],
      ["Azure Container Registry", "Image storage", "Same region as the cluster. AKS authenticates with its managed identity, so no registry password exists anywhere in the system."],
      ["Azure Kubernetes Service", "Orchestration", "Managed control plane at no cost on the Free tier; integrated Load Balancer; metrics-server preinstalled so the autoscaler works out of the box."],
      ["Jenkins", "CI/CD engine", "Chosen over GitHub Actions deliberately: a self-hosted controller exposes the whole stack rather than hiding it, and the Jenkinsfile is version-controlled with the code."],
      ["Ansible", "Deployment automation", "Idempotent, agentless. deploy-app.yml renders the manifests for a specific build and performs the rollout."],
    ],
    [0.2, 0.2, 0.6]),
  spacer(),

  h2("2.1 Alternatives considered and rejected"),
  bullet("GitHub Actions — faster to set up and requires no controller, but hides the build infrastructure and leaves no meaningful role for configuration management."),
  bullet("Azure DevOps Pipelines — Azure-native, but the free tier requires a parallelism grant that can take several days to approve."),
  bullet("Jenkins on a dedicated Azure VM — the original design. It buys a publicly reachable webhook endpoint for roughly US$38/month; SCM polling achieves automatic triggering for nothing, so the containerised controller was preferred."),
  bullet("Helm or Kustomize — better at scale, but for five manifests whose only variable parts are an image reference and four strings, envsubst keeps the rendered output directly readable and adds no tooling."),
  bullet("Self-hosted SonarQube — full control, but needs roughly 3 GB RAM, a database, patching and backups, with no educational return in this context."),

  h2("2.2 Why the two extra gates matter"),
  rp([["A gate differs from a report in exactly one respect: ", {}], ["a gate can stop you", { bold: true }], [". Gitleaks runs with --exit-code 1 and SonarQube with -Dsonar.qualitygate.wait=true, so both fail the build rather than filing a finding somebody may read later. Gitleaks is placed at stage 2, immediately after checkout, because it costs about a second and must run before any artifact is published — a credential inside a pushed image layer cannot be recalled.", {}]]),
  new Paragraph({ children: [new PageBreak()] }),
);

/* --- 3 stages --- */
kids.push(
  h1("3. CI/CD Pipeline Stages and Their Purpose"),
  p("The pipeline is defined declaratively in the Jenkinsfile, which lives in the repository. Stages run in order and the build halts at the first failure, so a defect never reaches the cluster."),
  table(
    ["#", "Stage", "What it does and why"],
    [
      ["1", "Checkout", "Clones the commit and reads the short SHA, author and subject. Derives IMAGE_TAG = <build-number>-<commit-sha>, which is what makes every artifact traceable to source."],
      ["2", "Secret Scan (Gitleaks)", "Scans the entire git history with --exit-code 1 and a redacted SARIF report archived as a build artifact. Security gate."],
      ["3", "Build and Unit Test (Maven)", "clean verify: compile, 29 unit tests, package, JaCoCo report. verify rather than package, because the coverage report is bound to the verify phase and SonarQube needs it."],
      ["4", "Code Quality (SonarQube Cloud)", "sonar:sonar with qualitygate.wait=true, which blocks until the gate is computed and fails the build if it is red. Quality gate."],
      ["5", "Docker Build and Tag", "Multi-stage build, tagged <build>-<commit> and latest, with build metadata baked in as OCI labels and environment variables."],
      ["6", "Push to ACR", "Authenticates with the service principal, pushes both tags, then lists the newest tags in the log as evidence."],
      ["7", "Deploy to Kubernetes", "az aks get-credentials, then Ansible renders the manifests for this build's tag and applies them. The rendered YAML is archived, so exactly what was sent to the cluster is recorded."],
      ["8", "Verify Deployment", "rollout status, then an HTTP smoke test asserting that the live endpoint reports this build's image tag."],
    ],
    [0.05, 0.25, 0.7]),
  spacer(),

  h2("3.1 Why stage 8 is the one that matters"),
  rp([["Without stage 8, a green pipeline would mean only that ", {}], ["kubectl apply", { mono: true }], [" returned zero — which it does even when the new pods immediately crash-loop and the previous version continues to serve traffic. Stage 8 performs three escalating checks: the rollout completed, so new pods passed their readiness probe; the service answers over HTTP; and the running application reports ", {}], ["this build’s", { italics: true }], [" image tag. The final assertion makes a false success impossible.", {}]]),

  h2("3.2 How each class of failure is contained"),
  table(
    ["Failure", "Caught by", "Consequence"],
    [
      ["Credential committed to the repository", "Stage 2", "Build fails; no image is built or published"],
      ["Broken unit test", "Stage 3", "Build fails; the JUnit report names the test"],
      ["New bug, vulnerability or coverage drop", "Stage 4", "Quality Gate red; build fails"],
      ["Malformed Dockerfile", "Stage 5", "Build fails; nothing pushed"],
      ["Insufficient Azure permissions", "Stage 6", "Build fails; cluster untouched, old version still serving"],
      ["Application crashes on startup", "Stage 8", "rollout status times out; maxUnavailable: 0 means the previous ReplicaSet served throughout"],
    ],
    [0.4, 0.17, 0.43]),
  spacer(),
  shot("2", "Jenkins Stage View — all 8 stages green",
    "Jenkins > job cicd-demo-app > build 16 (or 8, 11, 12, 13 — any build with DEPLOY_TARGET=azure). Avoid builds 2–5, which failed before SonarCloud was configured."),
  new Paragraph({ children: [new PageBreak()] }),
);

/* --- 4 cloud --- */
kids.push(
  h1("4. Cloud Resources and Deployment Approach"),
  h2("4.1 Azure resources"),
  table(
    ["Resource", "Name", "Specification", "Role"],
    [
      ["Resource group", "rg-cicd-cia2", "Central India", "Cost and blast-radius boundary"],
      ["Container registry", "acrcicdcia2", "Basic SKU", "Stores the tagged images"],
      ["Kubernetes service", "aks-cicd-cia2", "Free tier control plane, 1 × Standard_B2s, 32 GB disk", "Runs the workload"],
      ["Load balancer + public IP", "created by the Service", "Standard", "Public application endpoint"],
      ["Service principal", "sp-cicd-cia2", "Contributor (group), AcrPush, AKS Cluster Admin", "Jenkins identity in Azure"],
    ],
    [0.22, 0.2, 0.33, 0.25]),
  spacer(),
  rp([["AKS is split across two resource groups. ", {}], ["rg-cicd-cia2", { mono: true }], [" holds the registry and the cluster object; AKS itself creates ", {}], ["MC_rg-cicd-cia2_aks-cicd-cia2_centralindia", { mono: true }], [" to hold the node VM, the virtual network, the network security group, the load balancer and the public IPs. The managed group should not be edited by hand, as AKS reconciles it.", {}]]),
  rp([["The Kubernetes control plane is not part of the deployment. Its API server address, ", {}], ["aks-cicd-c-rg-cicd-cia2-3b1883-msblynq8.hcp.centralindia.azmk8s.io", { mono: true }], [", resolves into Microsoft’s own subscription. On the Free tier that control plane costs nothing; only the worker node is billed.", {}]]),

  h2("4.2 Kubernetes deployment design"),
  bullet("Namespace cicd-demo, isolating the workload from kube-system."),
  bullet("ConfigMap carrying non-secret settings plus build provenance (APP_IMAGE_TAG, APP_BUILD_NUMBER, APP_COMMIT_SHA), which is what allows the running application to display which build it is."),
  bullet("Deployment with 2 replicas and a RollingUpdate strategy of maxSurge 1, maxUnavailable 0, so a new pod must pass its readiness probe before an old one is removed. Three probes: startupProbe allows up to 150 s for the JVM to warm up, readinessProbe gates traffic, livenessProbe restarts a wedged container."),
  bullet("Hardened securityContext: non-root UID 10001, readOnlyRootFilesystem with an emptyDir mounted at /tmp for the servlet container, allowPrivilegeEscalation false, all Linux capabilities dropped, RuntimeDefault seccomp profile."),
  bullet("Service of type LoadBalancer, port 80 to targetPort 8080, with an azure-dns-label-name annotation that gives a stable hostname instead of a bare IP address."),
  bullet("HorizontalPodAutoscaler scaling between 2 and 4 replicas on CPU utilisation, relying on the metrics-server AKS installs by default."),

  h2("4.3 Deployment strategy"),
  rp([["The manifests are templates: the image reference and build metadata are ${...} placeholders. k8s/render.sh substitutes an explicit, named allow-list of variables using envsubst, so nothing else in the YAML can be altered, and writes the result to k8s/rendered/, which the pipeline archives as evidence of exactly what was applied.", {}]]),
  rp([["Because every build produces a new image tag, the pod template differs on every deployment and Kubernetes always performs a genuine rolling update. This avoids the common failure in which a manifest references ", {}], ["latest", { mono: true }], [", ", {}], ["kubectl apply", { mono: true }], [" reports “unchanged”, and nothing is actually redeployed while the pipeline reports success.", {}]]),

  h2("4.4 Cost model"),
  table(
    ["Component", "Rate", "Monthly if left running"],
    [
      ["AKS control plane (Free tier)", "0", "0"],
      ["1 × Standard_B2s node", "US$0.0448/hr", "US$32.70"],
      ["Standard Load Balancer, 1 rule", "US$0.025/hr", "US$18.25"],
      ["Static public IP", "US$0.005/hr", "US$3.65"],
      ["32 GB StandardSSD node disk", "~US$0.003/hr", "~US$2.40"],
      ["Azure Container Registry, Basic", "~US$0.007/hr", "~US$5.00"],
      ["Total while running", "~US$0.085/hr", "~US$62 (~US$2.05/day)"],
      ["Total while paused", "~US$0.015/hr", "~US$11 (~US$0.35/day)"],
    ],
    [0.42, 0.25, 0.33]),
  spacer(),
  p("Cost control is part of the design rather than an afterthought: infra/azure-pause.sh stops the cluster between sessions, azure-resume.sh restores it, and azure-teardown.sh deletes the resource group entirely. The node disk was explicitly created at 32 GB rather than accepting the 128 GB Premium SSD default, which would have cost roughly US$20/month for storage the workload never uses and is billed even while the cluster is stopped."),
  spacer(),
  shot("3", "Azure portal — resource group rg-cicd-cia2",
    "Portal > Resource groups > rg-cicd-cia2 > Overview, showing the registry and the AKS cluster."),
  spacer(),
  shot("4", "Azure portal — AKS cluster overview",
    "Portal > aks-cicd-cia2 > Overview, showing provisioning status and Kubernetes version."),
  new Paragraph({ children: [new PageBreak()] }),
);

/* --- 5 results --- */
kids.push(
  h1("5. Results, Screenshots and Test Evidence"),
  p("The output below was captured directly from the running system. Screenshot placeholders follow each item."),

  h2("5.1 Unit tests and coverage"),
  evidence([
    "[INFO] Tests run: 29, Failures: 0, Errors: 0, Skipped: 0",
    "[INFO] BUILD SUCCESS",
  ]),
  spacer(80),
  table(
    ["JaCoCo counter", "Covered", "Missed", "Coverage"],
    [
      ["Instruction", "290", "13", "95.7%"],
      ["Branch", "23", "3", "88.5%"],
      ["Line", "70", "5", "93.3%"],
      ["Method", "18", "1", "94.7%"],
      ["Class", "8", "0", "100%"],
    ],
    [0.4, 0.2, 0.2, 0.2]),
  spacer(),
  shot("5", "Jenkins test results — 29 tests passing",
    "Jenkins > build 16 > Test Result, or the test trend graph on the job page."),
  spacer(),

  h2("5.2 Secret scanning"),
  p("The gate was verified in both directions, because a security control that has only ever been observed to pass has not been tested."),
  evidence([
    "clean repository:",
    "  INF 1 commits scanned.",
    "  INF no leaks found",
    "",
    "with a planted fake Sonar token and Azure client secret:",
    "  WRN leaks found: 3",
  ]),
  spacer(),
  shot("6", "Gitleaks stage output",
    "Jenkins > build 16 > Console Output, search for “gitleaks”. Gitleaks has no dashboard — the build log is the evidence."),
  spacer(),

  h2("5.3 Static analysis"),
  evidence([
    "[INFO] ------------- Check Quality Gate status",
    "[INFO] QUALITY GATE STATUS: PASSED",
    "        https://sonarcloud.io/dashboard?id=manisudhan_cicd-azure-cia2",
  ]),
  spacer(),
  shot("7", "SonarCloud dashboard — Quality Gate Passed",
    "sonarcloud.io > project manisudhan_cicd-azure-cia2. This is still live and needs no cluster."),
  new Paragraph({ children: [new PageBreak()] }),

  h2("5.4 Successful pipeline execution"),
  evidence([
    "Build 16  (DEPLOY_TARGET=azure, RUN_SONAR=true)        SUCCESS",
    "",
    "  Declarative: Checkout SCM                SUCCESS",
    "  1. Checkout                              SUCCESS",
    "  2. Secret Scan (Gitleaks)                SUCCESS",
    "  3. Build & Unit Test (Maven)             SUCCESS",
    "  4. Code Quality (SonarQube Cloud)        SUCCESS",
    "  5. Docker Build & Tag                    SUCCESS",
    "  6. Push to Azure Container Registry      SUCCESS",
    "  7. Deploy to Kubernetes                  SUCCESS",
    "  8. Verify Deployment                     SUCCESS",
    "",
    "SUCCESS - build 16 verified via",
    "  http://cicd-demo-cia2.centralindia.cloudapp.azure.com",
    "Pipeline succeeded. Image acrcicdcia2.azurecr.io/cicd-demo-app:16-aa6f42c",
    "  is running on the azure cluster.",
  ]),
  spacer(),

  h2("5.5 Image published to the registry"),
  p("One tag per pipeline run, each naming its build number and commit:"),
  evidence([
    "$ az acr repository show-tags --name acrcicdcia2 \\",
    "      --repository cicd-demo-app --orderby time_desc -o table",
    "",
    "  latest",
    "  16-aa6f42c",
    "  15-efdaf79",
    "  14-0e31c0d",
    "  13-3b731b1",
    "  12-de850a0",
    "  11-ac268ea",
    "  8-95e0d05",
    "",
    "Registry storage used: 168,725,567 bytes (161 MiB) for all images,",
    "because the layers below the application JAR are shared between them.",
  ]),
  spacer(),
  shot("8", "ACR repository tags",
    "Portal > acrcicdcia2 > Repositories > cicd-demo-app."),
  spacer(),

  h2("5.6 Kubernetes deployment"),
  evidence([
    "$ kubectl -n cicd-demo get deployment,pods,svc -o wide",
    "",
    "NAME                            READY  UP-TO-DATE  AVAILABLE",
    "deployment.apps/cicd-demo-app   2/2    2           2",
    "  IMAGE: acrcicdcia2.azurecr.io/cicd-demo-app:16-aa6f42c",
    "",
    "NAME                                 READY  STATUS    RESTARTS",
    "pod/cicd-demo-app-6d4746db74-7pqkk   1/1    Running   0",
    "pod/cicd-demo-app-6d4746db74-kg4vm   1/1    Running   0",
    "  NODE: aks-nodepool1-27233998-vmss000000",
    "",
    "NAME                    TYPE           EXTERNAL-IP      PORT(S)",
    "service/cicd-demo-app   LoadBalancer   20.219.204.192   80:32309/TCP",
  ]),
  spacer(80),
  p("Each Deployment revision is annotated with the pipeline run that produced it:"),
  evidence([
    "$ kubectl -n cicd-demo rollout history deployment/cicd-demo-app",
    "",
    "REVISION  CHANGE-CAUSE",
    "1         Jenkins build 8 from commit 95e0d05",
    "2         Jenkins build 11 from commit ac268ea",
  ]),
  spacer(),
  shot("9", "kubectl get deployment, pods and service",
    "Terminal output, or Portal > aks-cicd-cia2 > Kubernetes resources > Workloads with the namespace filter set to cicd-demo."),
  spacer(),

  h2("5.7 Application reachable in a browser"),
  evidence([
    "$ curl http://cicd-demo-cia2.centralindia.cloudapp.azure.com/api/v1/info",
    "",
    '{"applicationVersion":"1.0.0",',
    ' "imageTag":"16-aa6f42c",',
    ' "buildNumber":"16",',
    ' "commitSha":"aa6f42c",',
    ' "environment":"production",',
    ' "servedBy":"cicd-demo-app-6d4746db74-7pqkk"}',
    "",
    "$ curl .../actuator/health",
    '{"status":"UP","groups":["liveness","readiness"]}',
  ]),
  spacer(),
  shot("10", "Application running in a browser",
    "The landing page, showing image tag, Jenkins build number, commit and the pod serving the request."),
  new Paragraph({ children: [new PageBreak()] }),

  h2("5.8 Change and redeployment demonstration"),
  p("A change to the release message was committed and pushed. No further human action was taken."),
  numbered("The change was committed and pushed to GitHub."),
  numbered("SCM polling detected the new commit and started a build automatically — recorded by Jenkins as “Started by an SCM change”."),
  numbered("All eight stages ran, producing a new image tag."),
  numbered("The image was published to the registry alongside the previous tags."),
  numbered("AKS performed a rolling update; because maxUnavailable is 0, the service continued answering throughout."),
  numbered("Stage 8 asserted that the live endpoint reported the new image tag."),
  numbered("The changed message and the incremented build number were visible at the public endpoint."),
  spacer(),
  shot("11", "Build triggered automatically",
    "Jenkins build page showing the cause “Started by an SCM change”, or the job’s Git Polling Log."),
  spacer(),
  shot("12", "Before and after at the application endpoint",
    "Two browser screenshots of the landing page, showing the release message and build number changing."),
  spacer(),

  h2("5.9 Self-healing demonstration"),
  p("A pod was deleted deliberately. Nothing was instructed to replace it."),
  evidence([
    "BEFORE              bl7jg   Running  2d7h",
    "                    dtcg8   Running  2d7h",
    "",
    "$ kubectl -n cicd-demo delete pod cicd-demo-app-54bf9d7b68-bl7jg",
    "",
    "1 SECOND LATER      dtcg8   Running  2d7h",
    "                    kqrvm   Running  1s      <- created automatically",
    "",
    "website during it   HTTP 200, served by dtcg8",
    "27 SECONDS LATER    both pods 1/1 Running",
  ]),
  p("The ReplicaSet observed that one pod existed where two were desired and created a replacement. The Service continued routing to the surviving pod throughout, so no request failed.", { after: 200 }),

  h2("5.10 Autoscaling demonstration"),
  evidence([
    "$ kubectl -n cicd-demo get hpa",
    "NAME            TARGETS         MINPODS  MAXPODS  REPLICAS",
    "cicd-demo-app   cpu: 169%/70%   2        4        4",
    "",
    "Events:",
    "  Normal  SuccessfulRescale   New size: 4; reason: cpu resource",
    "          utilization (percentage of request) above target",
    "  Normal  SuccessfulRescale   New size: 3; reason: All metrics below target",
    "",
    "Observed sequence under synthetic load:",
    "  t+20s   cpu=169%  pods=4      scaled up within 60 s of load starting",
    "  t+100s  cpu=17%   pods=4      load removed",
    "  t+140s  cpu=17%   pods=3      first step down",
    "  t+240s  cpu=2%    pods=2      returned to the configured minimum",
  ]),
  spacer(),
  shot("13", "HPA scaling events",
    "Output of kubectl -n cicd-demo describe hpa cicd-demo-app, showing the SuccessfulRescale events."),
  new Paragraph({ children: [new PageBreak()] }),
);

/* --- 6 challenges --- */
kids.push(
  h1("6. Challenges Encountered and Solutions"),
  p("The following are genuine failures encountered while building the system, with their root causes. They are reported because the diagnosis is the instructive part."),
  table(
    ["Challenge", "Root cause", "Solution"],
    [
      ["kubectl apply reported “unchanged” and no new code was deployed", "The manifest referenced the mutable latest tag, so the pod template was byte-identical between builds", "Tag every image <build>-<commit>, guaranteeing a changed pod spec per build"],
      ["The pipeline reported success while the application was broken", "It verified that the API call succeeded, not the outcome", "Added stage 8: rollout status plus an assertion that the live endpoint reports this build's tag"],
      ["Container failed to start with a read-only root filesystem", "The embedded servlet container requires a writable temporary directory", "Mounted an emptyDir at /tmp and kept the remainder read-only"],
      ["Registry creation failed with a message claiming the name was taken", "The real error, MissingSubscriptionRegistration, had been suppressed by redirecting stderr, and the script then guessed a cause", "Register the required resource providers; never replace a provider's own error with a guess"],
      ["Role assignment failed with (MissingSubscription)", "Git Bash on Windows rewrote the scope /subscriptions/... into a Windows path", "Export MSYS_NO_PATHCONV=1 and MSYS2_ARG_CONV_EXCL"],
      ["A script failed claiming Python was missing, after a ten-minute wait", "command -v python3 succeeds on Windows even when python3 is a Store alias stub that fails when executed", "Test that the interpreter actually runs, not merely that it resolves"],
      ["Image build failed on a DNS resolution error", "Transient failure, immediately after other hosts had resolved correctly", "curl --retry-all-errors; a plain --retry does not retry resolution failures"],
      ["Jenkins container would not start: port already in use", "A separately installed native Jenkins already held port 8080", "Publish the container on a different host port"],
      ["Shell scripts failed on Linux with a bad interpreter error", "Git on Windows checks files out with CRLF line endings", ".gitattributes forcing eol=lf for shell scripts, the Jenkinsfile and YAML"],
      ["SonarQube Cloud rejected the pipeline's analysis", "Automatic Analysis was enabled and is mutually exclusive with CI-based analysis", "Disabled Automatic Analysis for the project"],
      ["The first cost estimate was substantially too low", "The invisible costs were the Load Balancer and the default 128 GB Premium SSD disks, which are billed even while compute is stopped", "Moved the CI controller off the cloud, used a 32 GB StandardSSD disk, and added pause/resume scripts"],
      ["Manual scaling appeared to do nothing", "A HorizontalPodAutoscaler owns the replica count and reverted every manual change within its sync interval", "Remove the HPA to scale manually, or adjust its bounds. Both behaviours are correct; they are mutually exclusive"],
      ["A fourth replica would not schedule", "One Standard_B2s node has 1900m allocatable CPU and the AKS system pods already request ~1350m", "Reduced the per-pod CPU request from 150m to 100m, leaving room for five replicas"],
      ["Stage 8 failed with HTTP 403 while the application was healthy", "A FortiGuard web filter on the network blocks plain-IP HTTP. The 403 came from the filter, not the application", "Added an Azure DNS label to the Service and smoke-tested the hostname, with an in-cluster fallback"],
    ],
    [0.3, 0.37, 0.33]),
  spacer(),
  rp([["A pattern runs through these. Most were not coding errors but ", {}], ["diagnostic", { italics: true }], [" errors: an error message that guessed instead of reporting, a check that tested existence instead of function, and a pipeline that verified a call instead of an outcome. In each case the fix was to make the system report the truth about itself.", {}]]),
  new Paragraph({ children: [new PageBreak()] }),
);

/* --- 7 security --- */
kids.push(
  h1("7. Security Considerations and Limitations"),
  h2("7.1 Measures implemented"),
  numbered("Secret detection as a hard gate. Gitleaks scans the full git history on every build and fails it on any finding, with six custom rules covering the credential types this project handles: Azure storage connection strings, service-principal secrets, kubeconfig client keys, registry admin passwords, SonarQube tokens and Jenkins API tokens."),
  numbered("No credentials in version control. .gitignore and .dockerignore both exclude .env, private keys, kubeconfig files and credential JSON. The four secrets live in the Jenkins credential store and are injected only inside withCredentials blocks, which mask them in the console log."),
  numbered("Least privilege in Azure. The service principal is scoped to one resource group, with AcrPush on the registry and Cluster Admin on the cluster — nothing subscription-wide. AKS pulls images using its own managed identity, so no registry password exists in the cluster."),
  numbered("Hardened container. A JRE-only base image, a non-root user, a read-only root filesystem, no privilege escalation, all Linux capabilities dropped and the default seccomp profile."),
  numbered("Static analysis as a gate. The Quality Gate blocks the build on new vulnerabilities and unreviewed security hotspots."),
  numbered("Provenance. Every image carries OCI labels and environment variables naming its commit and build number, so any running container can be traced to source."),
  numbered("Supply-chain pinning. Base images are pinned to specific tags, the build tool version is pinned by the committed wrapper, and the scanner versions are pinned in the agent image."),

  h2("7.2 Known limitations"),
  p("These are stated explicitly rather than omitted. Each is a real weakness of the implementation as submitted."),
  table(
    ["#", "Limitation", "Production remedy"],
    [
      ["1", "The CI server is served over plain HTTP with a single local administrator account", "Terminate TLS in front of it; use an identity provider rather than a local account"],
      ["2", "The application endpoint is HTTP only", "An ingress controller with TLS, or a managed front door service"],
      ["3", "The Jenkins container runs as root and mounts the host Docker socket, which is root-equivalent on the host", "A rootless image builder, or server-side builds in the registry"],
      ["4", "A long-lived service principal secret is stored in the CI credential store", "OIDC workload-identity federation, which stores no secret at all"],
      ["5", "Cluster access uses administrator credentials, bypassing directory-based RBAC", "Disable local accounts, integrate with the directory, and bind a narrowly scoped role"],
      ["6", "No container image vulnerability scanning", "A Trivy stage failing the build on HIGH or CRITICAL findings"],
      ["7", "No image signing or software bill of materials", "Cosign signatures and a Syft SBOM, enforced by an admission policy"],
      ["8", "Single node and a single CI host, so no high availability", "A multi-node pool across availability zones; a CI controller with separate agents"],
      ["9", "No NetworkPolicies, so pods may communicate freely", "Default-deny egress with explicit allow rules"],
      ["10", "No staging environment or approval gate; main deploys straight to the only environment", "Separate namespaces or clusters with a manual approval before production"],
      ["11", "Kubernetes Secrets are base64-encoded, not encrypted at rest by default", "An external key vault with the Secrets Store CSI driver"],
    ],
    [0.05, 0.47, 0.48]),
  new Paragraph({ children: [new PageBreak()] }),
);

/* --- 8 conclusion --- */
kids.push(
  h1("8. Conclusion"),
  p("The pipeline replaces a manual, unreproducible release process with eight automated stages that run on every push to the main branch. A developer’s only action is to push a commit; approximately five minutes later a uniquely identified, scanned, tested and statically analysed container image is running on Azure Kubernetes Service behind a public endpoint, and the pipeline has confirmed this by querying that endpoint."),
  p("The two additional gates are what make the automation safe rather than merely fast. Gitleaks ensures the increase in speed does not also accelerate credential leaks, and the SonarQube Cloud Quality Gate ensures it does not accelerate defects. Both fail the build rather than filing a report, which is the difference between a gate and a dashboard."),
  p("The design decisions that mattered most were small and specific. Tagging images <build>-<commit> rather than latest is what makes rolling updates actually roll and rollback possible. Setting maxUnavailable to 0 is what makes those updates zero-downtime. Asserting the deployed image tag at the live endpoint is what makes a green build trustworthy. Each addresses one of the four failures identified at the outset, and together they turn an opaque manual procedure into one that is reproducible, verified, parallelisable and traceable."),
  spacer(),

  h2("Appendix A — Repository structure"),
  table(
    ["Path", "Purpose"],
    [
      ["Jenkinsfile", "The 8-stage declarative pipeline"],
      ["pom.xml, mvnw, .mvn/", "Maven build with the committed wrapper, JaCoCo and SonarQube configuration"],
      ["Dockerfile, .dockerignore", "Multi-stage application image running as a non-root user"],
      [".gitleaks.toml", "Secret-scanning rules and a documented allowlist"],
      [".gitattributes", "Forces LF line endings so scripts run on Linux"],
      ["src/main, src/test", "Application source and 29 unit tests"],
      ["k8s/", "Namespace, ConfigMap, Deployment, Service, HPA, and render.sh"],
      ["ansible/", "deploy-app.yml (used by the pipeline) and jenkins-setup.yml (optional VM topology)"],
      ["infra/", "Provisioning, credential loading, pause, resume and teardown scripts"],
      ["jenkins/", "Dockerfile, plugin list, startup scripts and job definition for the CI controller"],
      ["docs/", "Setup runbook, study guide, link reference and this report"],
    ],
    [0.3, 0.7]),
  spacer(),

  h2("Appendix B — Key figures"),
  table(
    ["Metric", "Value"],
    [
      ["Pipeline stages", "8"],
      ["Unit tests", "29, all passing"],
      ["Instruction coverage", "95.7%"],
      ["Branch coverage", "88.5%"],
      ["Replicas", "2 (autoscaling 2–4 on 70% CPU)"],
      ["Image tag format", "<build-number>-<commit-sha>"],
      ["Rolling update policy", "maxSurge 1, maxUnavailable 0"],
      ["Container user", "UID 10001, non-root, read-only root filesystem"],
      ["Published image size", "~190 MB (JRE base) versus ~600 MB with the JDK"],
      ["Registry storage for all builds", "161 MiB, due to shared layers"],
      ["Node", "1 × Standard_B2s (2 vCPU, 4 GiB)"],
      ["Running cost", "~US$0.085/hour (~US$2.05/day)"],
      ["Secret-scanning rules", "~170 default plus 6 custom"],
    ],
    [0.45, 0.55]),
);

/* --------------------------------------------------------------- assemble */

const doc = new Document({
  creator: "CIA-2 DevOps Assignment",
  title: "End-to-End Cloud-Based CI/CD Pipeline on Microsoft Azure",
  styles: {
    default: {
      document: { run: { font: BODY, size: 21, color: INK } },
      title: { run: { font: BODY, size: 40, bold: true, color: INK }, paragraph: { spacing: { before: 0, after: 240 }, keepNext: true } },
      heading1: { run: { font: BODY, size: 28, bold: true, color: ACCENT }, paragraph: { spacing: { before: 280, after: 140 }, keepNext: true } },
      heading2: { run: { font: BODY, size: 23, bold: true, color: INK }, paragraph: { spacing: { before: 220, after: 100 }, keepNext: true } },
    },
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: convertInchesToTwip(0.3), hanging: convertInchesToTwip(0.18) } } } }] },
      { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: convertInchesToTwip(0.32), hanging: convertInchesToTwip(0.2) } } } }] },
    ],
  },
  sections: [{ properties: {}, children: kids }],
});

Packer.toBuffer(doc).then((b) => {
  fs.writeFileSync(OUT, b);
  console.log("written:", OUT, b.length, "bytes");
});
