#!/usr/bin/env python
"""Generates the CI/CD study guide PDF."""
import sys
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageBreak,
                                PageTemplate, Paragraph, Preformatted, Spacer,
                                Table, TableStyle)

OUT = sys.argv[1] if len(sys.argv) > 1 else "study-guide.pdf"

INK = colors.HexColor("#111827")
ACCENT = colors.HexColor("#1d4ed8")
MUTED = colors.HexColor("#4b5563")
RULE = colors.HexColor("#d1d5db")
CODEBG = colors.HexColor("#f3f4f6")
NOTEBG = colors.HexColor("#eff6ff")
WARNBG = colors.HexColor("#fef3c7")

ss = getSampleStyleSheet()
S = {
    "title": ParagraphStyle("title", parent=ss["Title"], fontName="Helvetica-Bold",
                            fontSize=26, leading=31, textColor=INK, spaceAfter=4),
    "subtitle": ParagraphStyle("subtitle", parent=ss["Normal"], fontSize=12.5, leading=17,
                               alignment=TA_CENTER, textColor=MUTED),
    "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontName="Helvetica-Bold",
                         fontSize=17, leading=21, textColor=ACCENT,
                         spaceBefore=16, spaceAfter=7),
    "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold",
                         fontSize=12.8, leading=16, textColor=INK,
                         spaceBefore=12, spaceAfter=5),
    "h3": ParagraphStyle("h3", parent=ss["Heading3"], fontName="Helvetica-BoldOblique",
                         fontSize=10.8, leading=14, textColor=INK,
                         spaceBefore=9, spaceAfter=3),
    "p": ParagraphStyle("p", parent=ss["BodyText"], fontSize=9.7, leading=14,
                        textColor=INK, alignment=TA_JUSTIFY, spaceAfter=6),
    "bullet": ParagraphStyle("bullet", parent=ss["BodyText"], fontSize=9.7, leading=13.6,
                             textColor=INK, leftIndent=13, bulletIndent=3, spaceAfter=3.5),
    "code": ParagraphStyle("code", parent=ss["Code"], fontName="Courier",
                           fontSize=7.9, leading=10.2, textColor=INK,
                           backColor=CODEBG, borderColor=RULE, borderWidth=0.5,
                           borderPadding=6, leftIndent=0, spaceBefore=4, spaceAfter=7),
    "note": ParagraphStyle("note", parent=ss["BodyText"], fontSize=9.4, leading=13.3,
                           textColor=INK, backColor=NOTEBG, borderColor=colors.HexColor("#93c5fd"),
                           borderWidth=0.6, borderPadding=7, spaceBefore=5, spaceAfter=8),
    "warn": ParagraphStyle("warn", parent=ss["BodyText"], fontSize=9.4, leading=13.3,
                           textColor=INK, backColor=WARNBG, borderColor=colors.HexColor("#fbbf24"),
                           borderWidth=0.6, borderPadding=7, spaceBefore=5, spaceAfter=8),
    "cell": ParagraphStyle("cell", parent=ss["BodyText"], fontSize=8.5, leading=11.6,
                           textColor=INK, spaceAfter=0),
    "cellh": ParagraphStyle("cellh", parent=ss["BodyText"], fontSize=8.5, leading=11.6,
                            fontName="Helvetica-Bold", textColor=colors.white, spaceAfter=0),
    "qa": ParagraphStyle("qa", parent=ss["BodyText"], fontName="Helvetica-Bold",
                         fontSize=9.7, leading=13.4, textColor=ACCENT, spaceBefore=8, spaceAfter=2),
}


def esc(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def mk(flow, blocks):
    for b in blocks:
        kind = b[0]
        if kind == "h1":
            flow.append(Paragraph(esc(b[1]), S["h1"]))
        elif kind == "h2":
            flow.append(Paragraph(esc(b[1]), S["h2"]))
        elif kind == "h3":
            flow.append(Paragraph(esc(b[1]), S["h3"]))
        elif kind == "p":
            flow.append(Paragraph(b[1], S["p"]))
        elif kind == "note":
            flow.append(Paragraph(b[1], S["note"]))
        elif kind == "warn":
            flow.append(Paragraph(b[1], S["warn"]))
        elif kind == "code":
            flow.append(Preformatted(b[1].strip("\n"), S["code"]))
        elif kind == "bullets":
            for item in b[1]:
                flow.append(Paragraph(item, S["bullet"], bulletText="\u2022"))
            flow.append(Spacer(1, 3))
        elif kind == "numbers":
            for i, item in enumerate(b[1], 1):
                flow.append(Paragraph(item, S["bullet"], bulletText="%d." % i))
            flow.append(Spacer(1, 3))
        elif kind == "qa":
            flow.append(Paragraph("Q. " + b[1], S["qa"]))
            flow.append(Paragraph(b[2], S["p"]))
        elif kind == "table":
            rows, widths = b[1], b[2]
            data = [[Paragraph(c, S["cellh"]) for c in rows[0]]]
            for r in rows[1:]:
                data.append([Paragraph(c, S["cell"]) for c in r])
            t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1, hAlign="LEFT")
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                ("GRID", (0, 0), (-1, -1), 0.4, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            flow.append(t)
            flow.append(Spacer(1, 8))
        elif kind == "pb":
            flow.append(PageBreak())
        elif kind == "sp":
            flow.append(Spacer(1, b[1]))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 15 * mm, A4[0] - 18 * mm, 15 * mm)
    canvas.setFont("Helvetica", 7.6)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 10.5 * mm,
                      "CIA-2  |  End-to-End Cloud CI/CD Pipeline on Microsoft Azure  |  Study Guide")
    canvas.drawRightString(A4[0] - 18 * mm, 10.5 * mm, "Page %d" % doc.page)
    canvas.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4,
                      leftMargin=18 * mm, rightMargin=18 * mm,
                      topMargin=17 * mm, bottomMargin=20 * mm,
                      title="CI/CD Pipeline on Azure - Study Guide",
                      author="CIA-2 DevOps Assignment")
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="n")
doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=footer)])

W = 174  # usable width in mm
F = []

# ===========================================================================
# COVER
# ===========================================================================
F.append(Spacer(1, 38 * mm))
F.append(Paragraph("End-to-End Cloud CI/CD Pipeline", S["title"]))
F.append(Paragraph("on Microsoft Azure", S["title"]))
F.append(Spacer(1, 7 * mm))
F.append(Paragraph("Complete Study &amp; Revision Guide", S["subtitle"]))
F.append(Paragraph("Java web application &bull; Jenkins &bull; Gitleaks &bull; SonarQube Cloud "
                   "&bull; Docker &bull; ACR &bull; AKS &bull; Ansible", S["subtitle"]))
F.append(Spacer(1, 14 * mm))
mk(F, [("table", [
    ["Item", "Value"],
    ["Repository", "github.com/manisudhan/cicd-azure-cia2"],
    ["Live endpoint", "http://20.219.204.192"],
    ["SonarCloud project", "manisudhan_cicd-azure-cia2"],
    ["Azure resource group", "rg-cicd-cia2 (centralindia)"],
    ["Container registry", "acrcicdcia2.azurecr.io"],
    ["Kubernetes cluster", "aks-cicd-cia2 (1 x Standard_B2s, Kubernetes 1.36)"],
    ["Jenkins", "http://localhost:8090 (Docker container cicd-jenkins)"],
], [42, 132])])
F.append(Spacer(1, 10 * mm))
mk(F, [("note", "<b>How to use this guide.</b> Parts 1 and 2 give you the story and the "
                "justifications - that is what most viva questions are really testing. Part 3 is the "
                "rebuild procedure. Parts 4 to 6 are the reference detail. <b>Part 7 is the most "
                "important part for a live viva</b>: it is a set of recipes for the \"change something "
                "right now\" questions, such as adding a pod or editing the pod spec. Part 10 is a "
                "question bank.")])

mk(F, [("pb",)])

# ===========================================================================
# CONTENTS
# ===========================================================================
mk(F, [
    ("h1", "Contents"),
    ("table", [
        ["Part", "Title", "What it covers"],
        ["1", "The Problem and the Solution", "What was broken, the architecture, the end-to-end flow"],
        ["2", "Why Each Tool", "Justification for every choice, and the alternatives rejected"],
        ["3", "Building It From Scratch", "The manual procedure, in order, with commands"],
        ["4", "Jenkins In Detail", "Image, plugins, credentials, the job, and exactly when it triggers"],
        ["5", "The Pipeline, Stage By Stage", "All 8 stages: purpose, code, failure modes"],
        ["6", "Kubernetes Deep Dive", "Every manifest and every field, explained"],
        ["7", "Live Operations Recipes", "The \"do this now\" questions: add a pod, change the spec, roll back"],
        ["8", "Security", "What is protected, how, and the honest limitations"],
        ["9", "Problems Actually Hit", "Real failures from this build and their root causes"],
        ["10", "Question Bank", "~45 likely viva questions with answers"],
        ["A", "Command Cheat Sheet", "Everything you might need to type under pressure"],
        ["B", "File Inventory", "What each file in the repository is for"],
        ["C", "Numbers To Memorise", "The handful of facts worth knowing cold"],
    ], [14, 62, 98]),
])

mk(F, [("pb",)])

# ===========================================================================
# PART 1
# ===========================================================================
mk(F, [
    ("h1", "Part 1 - The Problem and the Solution"),

    ("h2", "1.1 The problem, stated properly"),
    ("p", "A team builds a Java web application by hand. A developer compiles it locally, runs the "
          "tests when they remember to, builds a Docker image with an ad-hoc tag, and copies it to a "
          "server. If you are asked \"what was wrong with the old process?\", do not answer \"it was "
          "manual\". Name the four specific failures:"),
    ("numbers", [
        "<b>Not reproducible.</b> The artifact depends on whichever JDK, Maven version and local "
        "configuration that developer happened to have. \"It works on my machine\" cannot be disproved.",
        "<b>Error-prone.</b> Any step can be skipped. Tests get bypassed under deadline pressure and "
        "an untested build reaches users.",
        "<b>Serialising.</b> One person owns the deploy, so releases queue behind that person's "
        "availability.",
        "<b>Untraceable.</b> With tags like <font face='Courier'>latest</font> or "
        "<font face='Courier'>v2-final</font>, nobody can say which commit is running, which makes "
        "rollback guesswork.",
    ]),
    ("p", "Every design decision later in this project answers one of those four. That mapping is the "
          "single most useful thing to have in your head."),

    ("h2", "1.2 Architecture"),
    ("code", """
  Developer
     | git push
     v
  GitHub (public repo)  <----- polled every 2 min -----+
                                                       |
                                              Jenkins (local Docker)
                                                       |
     +-------------------------------------------------+
     |  Declarative pipeline, 8 stages
     v
  1 Checkout        git metadata -> IMAGE_TAG = <build>-<commit>
  2 Gitleaks        secret scan over FULL git history     [security gate]
  3 Maven           compile, 29 unit tests, JaCoCo coverage
  4 SonarQube Cloud static analysis + Quality Gate wait   [quality gate]
  5 Docker build    multi-stage image, tagged <build>-<commit>
  6 Push to ACR     acrcicdcia2.azurecr.io
  7 Deploy          Ansible renders manifests, kubectl apply
  8 Verify          rollout status + HTTP smoke test on the public IP
     |
     +--> Azure Container Registry --(AcrPull via managed identity)--> AKS
                                                                        |
                                                   Azure Load Balancer (public IP)
                                                                        |
                                                                     Browser
"""),
    ("p", "<b>Trust boundaries.</b> GitHub and SonarQube Cloud are external SaaS. ACR and AKS live "
          "inside one Azure resource group. Jenkins runs on the developer's own machine and "
          "authenticates to Azure with a service principal scoped to that resource group only."),

    ("h2", "1.3 The whole flow in one paragraph"),
    ("p", "A developer pushes to <font face='Courier'>main</font>. Within two minutes Jenkins notices "
          "the new commit by polling, and starts a build. It scans the entire git history for "
          "credentials, compiles the code, runs the unit tests, measures coverage, sends the result to "
          "SonarQube Cloud and waits for the Quality Gate verdict. If all of that passes it builds a "
          "container image tagged with the build number and the commit SHA, pushes it to Azure "
          "Container Registry, then has Ansible render the Kubernetes manifests for that exact image "
          "and apply them to AKS. Kubernetes performs a rolling update in which a new pod must pass "
          "its readiness probe before an old one is removed. Finally the pipeline waits for the Azure "
          "Load Balancer's public IP and makes an HTTP request to it, asserting that the live "
          "application reports the image tag this very build produced. Nobody touched anything."),

    ("note", "<b>The sentence that wins marks.</b> \"The pipeline does not just deploy - it proves the "
             "deployment. Stage 8 queries the live endpoint and fails the build if the running "
             "application does not report this build's image tag. Without that, a green pipeline only "
             "means <i>kubectl apply</i> succeeded, which it does even when the pods then crash-loop.\""),
])

mk(F, [("pb",)])

# ===========================================================================
# PART 2
# ===========================================================================
mk(F, [
    ("h1", "Part 2 - Why Each Tool"),
    ("p", "Expect \"why did you use X?\" for every single tool. A good answer has three parts: what "
          "problem it solves, why it beat the alternative, and what it costs you."),

    ("h2", "2.1 Git and GitHub"),
    ("p", "Source-code management, required by the brief. The repository is <b>public</b> for three "
          "concrete reasons: the brief asks for instructor-accessible code; SonarQube Cloud is free "
          "only for public projects; and GitHub webhooks and polling both work without extra "
          "credentials. The cost is that nothing secret can ever live in the repository - which is "
          "exactly why Gitleaks is in the pipeline."),

    ("h2", "2.2 Maven, via the Maven Wrapper"),
    ("p", "Maven is the standard Java build tool: a declarative "
          "<font face='Courier'>pom.xml</font> describes dependencies and the build lifecycle, so the "
          "build is the same everywhere. The important detail is the <b>wrapper</b> "
          "(<font face='Courier'>./mvnw</font>), which is committed to the repository and pins Maven "
          "3.9.9. The build agent therefore needs no Maven installed at all. That directly removes "
          "failure 1 (not reproducible): there is no \"which Maven version is on the server?\" question."),
    ("h3", "Lifecycle phases you should be able to name"),
    ("table", [
        ["Phase", "What it does"],
        ["validate", "Checks the project is correct and all information is available"],
        ["compile", "Compiles source into target/classes"],
        ["test", "Runs unit tests with Surefire; does not package"],
        ["package", "Builds the JAR/WAR into target/"],
        ["verify", "Runs checks on the package - this is where the JaCoCo report is generated"],
        ["install", "Copies the artifact into the local ~/.m2 repository"],
        ["deploy", "Publishes the artifact to a remote repository"],
    ], [26, 148]),
    ("p", "The pipeline runs <font face='Courier'>clean verify</font>, not "
          "<font face='Courier'>package</font>. Why? Because the JaCoCo report is bound to the "
          "<font face='Courier'>verify</font> phase, and SonarQube needs that report for coverage. "
          "Running <font face='Courier'>package</font> would silently give Sonar zero coverage."),

    ("h2", "2.3 JUnit 5 and JaCoCo"),
    ("p", "JUnit 5 with AssertJ for assertions and MockMvc for the HTTP layer. 29 tests cover the "
          "service logic, the configuration binding and both controllers without starting a real "
          "server. JaCoCo instruments the bytecode at test time and produces the XML report that "
          "SonarQube consumes."),
    ("table", [
        ["Counter", "Covered", "Missed", "Coverage"],
        ["Instruction", "290", "13", "95.7%"],
        ["Branch", "23", "3", "88.5%"],
        ["Line", "70", "5", "93.3%"],
        ["Method", "18", "1", "94.7%"],
        ["Class", "8", "0", "100%"],
    ], [40, 32, 32, 40]),

    ("h2", "2.4 Gitleaks - the security gate"),
    ("p", "<b>The problem it solves.</b> Automating a pipeline means artifacts get published faster. "
          "If a developer commits an API key, automation publishes that key faster too. A secret that "
          "reaches a registry or a public repository must be treated as compromised and rotated - you "
          "cannot un-publish it."),
    ("p", "<b>Why Gitleaks specifically.</b> It scans the full git <i>history</i>, not just the "
          "working tree. That matters enormously: the usual pattern is that someone commits a "
          "credential, notices, deletes it in the next commit, and believes the problem is gone. The "
          "secret is still in the object database and still recoverable by anyone who clones the "
          "repository. <font face='Courier'>gitleaks git .</font> walks every commit, so it finds it. "
          "It is also a single static binary with roughly 170 built-in rules, which makes it trivial "
          "to put in a container image."),
    ("p", "<b>Why it is stage 2, right after checkout.</b> It costs about a second and it must run "
          "before anything is published. Putting it after the Docker build would mean a leaked "
          "credential could already be inside an image layer."),
    ("p", "<b>What was added.</b> Six custom rules for the credential types this project actually "
          "handles, because the default rule set does not know about them:"),
    ("bullets", [
        "<font face='Courier'>azure-storage-connection-string</font> - connection strings containing AccountKey",
        "<font face='Courier'>azure-service-principal-secret</font> - clientSecret / appSecret values",
        "<font face='Courier'>kubeconfig-embedded-client-key</font> - base64 client keys in a kubeconfig",
        "<font face='Courier'>acr-admin-password</font> - registry admin passwords",
        "<font face='Courier'>sonar-token</font> - sq[apu]_ prefixed tokens",
        "<font face='Courier'>jenkins-api-token</font> - Jenkins user API tokens",
    ]),
    ("p", "<b>The allowlist.</b> Narrow and documented: this config file itself (it contains the "
          "detection patterns), the Maven wrapper scripts, build output, screenshots, and obvious "
          "placeholder patterns such as <font face='Courier'>CHANGE-ME</font>. The principle is to "
          "allowlist specific known-safe paths rather than weaken a rule."),
    ("note", "<b>Prove the gate is not a no-op.</b> A planted fake Sonar token and a fake Azure client "
             "secret produced <font face='Courier'>leaks found: 3</font>; a clean tree reports "
             "<font face='Courier'>no leaks found</font>. If you are asked \"how do you know it "
             "works?\", that is the answer: it was tested in both directions. A security control you "
             "have only ever seen pass is a control you have not tested."),

    ("h2", "2.5 SonarQube Cloud - the quality gate"),
    ("p", "<b>The problem it solves.</b> Same asymmetry as Gitleaks. Shipping faster is only an "
          "improvement if what you ship is not worse. Static analysis finds bugs, vulnerabilities and "
          "code smells that tests do not: a null dereference on an untested branch, a resource that is "
          "never closed, a hard-coded credential pattern, a cognitive-complexity hotspot."),
    ("p", "<b>Why it is a gate rather than a report.</b> This is the key point. The pipeline runs it "
          "with <font face='Courier'>-Dsonar.qualitygate.wait=true</font>, which blocks the build "
          "until SonarQube Cloud has finished computing the Quality Gate, and fails the build if the "
          "gate is red. A dashboard that nobody looks at changes nothing; a gate that fails the build "
          "cannot be ignored. <i>\"The difference between a gate and a dashboard is whether it can "
          "stop you.\"</i>"),
    ("p", "<b>What the Quality Gate checks</b> (the default \"Sonar way\", applied to new code): no "
          "new blocker/critical issues, no new security hotspots unreviewed, coverage on new code at "
          "or above 80 percent, duplicated lines on new code below 3 percent. This project reports "
          "95.7 percent instruction coverage, comfortably above the threshold."),
    ("p", "<b>Why the Cloud version rather than self-hosted.</b> Self-hosted SonarQube needs about 3 GB "
          "RAM, its own database, patching and backups - operational burden with no educational "
          "return here. SonarQube Cloud is free for public repositories and removes all of it. The "
          "trade-off: your code is analysed by a third party, and you depend on their availability."),
    ("warn", "<b>The trap.</b> SonarQube Cloud enables <b>Automatic Analysis</b> by default on "
             "GitHub-imported projects, and Automatic Analysis is mutually exclusive with CI-based "
             "analysis. If it is left on, the pipeline's analysis is rejected with \"You are running CI "
             "analysis while Automatic Analysis is enabled\". Fix: project -> Administration -> "
             "Analysis Method -> turn Automatic Analysis off. It can also be done through the API: "
             "<font face='Courier'>POST /api/autoscan/activation</font> with "
             "<font face='Courier'>enable=false</font>."),

    ("h2", "2.6 Docker, and why multi-stage"),
    ("p", "Containerisation makes the artifact self-contained: the image carries the JRE, the "
          "application and nothing else, so it runs identically on a laptop and on AKS. That is the "
          "direct answer to failure 1."),
    ("p", "<b>Multi-stage build.</b> Stage 1 uses "
          "<font face='Courier'>maven:3.9.9-eclipse-temurin-21</font> and carries the full JDK plus "
          "Maven - roughly 600 MB of tooling. Stage 2 starts again from "
          "<font face='Courier'>eclipse-temurin:21-jre-alpine</font> and copies in only the built "
          "JAR. The published image is around 190 MB instead of 600 MB. Two benefits: faster pulls, "
          "and a much smaller attack surface, because a compiler and a build tool that are not in the "
          "image cannot carry a CVE or be used by an attacker."),
    ("p", "<b>Why dependencies are a separate layer.</b> The Dockerfile copies "
          "<font face='Courier'>pom.xml</font> and runs "
          "<font face='Courier'>mvn dependency:go-offline</font> <i>before</i> copying "
          "<font face='Courier'>src</font>. Docker caches layers, so a source-only change reuses the "
          "cached dependency layer instead of re-downloading the whole repository. Order your "
          "Dockerfile from least-frequently-changing to most-frequently-changing."),
    ("p", "<b>Why tests are skipped inside the Dockerfile.</b> They already ran in stage 3, where "
          "Jenkins can collect the JUnit XML and publish the trend chart. Running them again inside "
          "the image build would double the time and hide the results."),

    ("h2", "2.7 Azure Container Registry"),
    ("p", "A private registry in the same cloud as the cluster. The decisive feature is that AKS can "
          "authenticate to it with the cluster's <b>managed identity</b> - "
          "<font face='Courier'>az aks update --attach-acr</font> grants the kubelet identity the "
          "<font face='Courier'>AcrPull</font> role. That means <b>no registry password exists "
          "anywhere</b>: not in Kubernetes as an imagePullSecret, not in Jenkins, not in a manifest. "
          "That is a genuine security improvement over Docker Hub with a stored credential."),

    ("h2", "2.8 Azure Kubernetes Service"),
    ("p", "A managed Kubernetes control plane. Why Kubernetes rather than just running a container on "
          "a VM: declarative desired state, self-healing (a crashed container is restarted, a failed "
          "pod rescheduled), rolling updates with health gating, and horizontal scaling. Why AKS "
          "rather than self-managed Kubernetes: the control plane is free on the Free tier and "
          "Microsoft operates it, the Azure Load Balancer integration turns "
          "<font face='Courier'>type: LoadBalancer</font> into a real public IP automatically, and "
          "<font face='Courier'>metrics-server</font> is installed by default so the "
          "HorizontalPodAutoscaler works out of the box."),

    ("h2", "2.9 Jenkins, and why not GitHub Actions"),
    ("p", "Jenkins was chosen deliberately over the easier option. A self-hosted controller shows the "
          "whole DevOps stack instead of hiding it behind a managed runner: you have to provision the "
          "agent, install the toolchain, manage credentials and secure the server. That is also what "
          "gives Ansible real work to do. And the <font face='Courier'>Jenkinsfile</font> lives in the "
          "repository, so the pipeline is version-controlled alongside the code and changes to it go "
          "through review like any other change."),
    ("p", "<b>Why it runs in a local Docker container rather than on an Azure VM.</b> A VM for the "
          "controller cost roughly US$38/month (the B2s instance, a second static public IP and a "
          "second managed disk) for something only needed while someone is actively working. Moving it "
          "into a container removed that entirely and cut the Azure bill from about US$4.50/day to "
          "about US$2.05/day with no loss of pipeline function. The cost of that decision: GitHub "
          "cannot reach <font face='Courier'>localhost</font>, so the automatic trigger is SCM polling "
          "rather than a webhook."),
    ("table", [
        ["Option", "Advantage", "Why not chosen"],
        ["GitHub Actions", "No server at all, free minutes", "Hides the build infrastructure; leaves no real role for Ansible"],
        ["Azure DevOps Pipelines", "Azure-native", "Free tier needs a parallelism grant that can take days"],
        ["Jenkins on an Azure VM", "Real public webhook endpoint", "About US$38/month for a controller used a few hours a day"],
        ["Jenkins in local Docker", "Free, reproducible via Dockerfile", "No inbound webhook; polling instead (chosen)"],
    ], [40, 54, 80]),

    ("h2", "2.10 Ansible"),
    ("p", "Configuration management and deployment automation, agentless - it needs only SSH, or "
          "nothing at all when it runs against localhost. Two playbooks:"),
    ("bullets", [
        "<b><font face='Courier'>deploy-app.yml</font> - used by the pipeline.</b> Stage 7 calls it. It "
        "verifies kubectl can reach the cluster, renders the manifests for this build's image tag, "
        "applies them, waits for the rollout and reports the endpoint. This is deployment automation.",
        "<b><font face='Courier'>jenkins-setup.yml</font> - the alternative topology.</b> Turns a bare "
        "Ubuntu VM into an identical build server: Java, Jenkins, Docker, kubectl, Azure CLI, Gitleaks, "
        "Ansible. Kept because it documents the cloud-hosted option; not used because Jenkins runs "
        "locally. This is configuration management.",
    ]),
    ("p", "<b>Why Ansible rather than a shell script.</b> Idempotence. An Ansible task describes the "
          "desired state (\"this package is present\", \"this service is started\"), so re-running the "
          "playbook after a change does only the work that is still needed. A shell script describes "
          "actions and generally cannot be re-run safely."),
])

mk(F, [("pb",)])

# ===========================================================================
# PART 3
# ===========================================================================
mk(F, [
    ("h1", "Part 3 - Building It From Scratch"),
    ("p", "The manual procedure, in dependency order. Roughly 60-90 minutes, most of it waiting for "
          "Azure."),

    ("h2", "Step 0 - Prerequisites"),
    ("table", [
        ["Tool", "Check", "Why it is needed"],
        ["Git", "git --version", "Source control; also used by Gitleaks"],
        ["Docker Desktop", "docker info", "Runs Jenkins, and builds the application image"],
        ["Azure CLI", "az version", "Creates and talks to Azure resources"],
        ["GitHub CLI", "gh --version", "Creating and pushing the repository (optional)"],
        ["Java 21", "java -version", "Only to run the app outside Docker"],
    ], [34, 44, 96]),
    ("p", "Maven is <b>not</b> required: the wrapper is committed. Ansible is <b>not</b> required "
          "locally: it is inside the Jenkins image. Docker Desktop must use the <b>WSL 2 backend</b>, "
          "because the Jenkins container mounts the host Docker socket."),

    ("h2", "Step 1 - Repository"),
    ("code", """
gh auth login
gh repo create cicd-azure-cia2 --public --source=. --remote=origin --push
"""),
    ("p", "Public, so SonarQube Cloud analysis is free and the instructor can read it."),

    ("h2", "Step 2 - Azure infrastructure"),
    ("code", """
az login
bash infra/azure-setup.sh
"""),
    ("p", "The script does five things, and the order matters:"),
    ("numbers", [
        "<b>Resource group</b> <font face='Courier'>rg-cicd-cia2</font>. One group means one cost "
        "boundary and one-command teardown.",
        "<b>Register resource providers.</b> A new or newly renewed subscription has namespaces such "
        "as <font face='Courier'>Microsoft.ContainerRegistry</font> unregistered, and resource "
        "creation then fails with <font face='Courier'>MissingSubscriptionRegistration</font> - a "
        "message that looks nothing like the real cause.",
        "<b>Container registry</b> <font face='Courier'>acrcicdcia2</font>, Basic SKU. The name must "
        "be globally unique across all of Azure.",
        "<b>AKS cluster</b> <font face='Courier'>aks-cicd-cia2</font>: 1 node, "
        "<font face='Courier'>Standard_B2s</font>, Free tier control plane, "
        "<font face='Courier'>--attach-acr</font> to grant AcrPull, "
        "<font face='Courier'>--node-osdisk-size 32</font> because the 128 GB Premium SSD default "
        "costs about US$20/month and is billed even while the cluster is stopped.",
        "<b>Service principal</b> <font face='Courier'>sp-cicd-cia2</font> with three role "
        "assignments: Contributor on the resource group, AcrPush on the registry, and Azure "
        "Kubernetes Service Cluster Admin on the cluster.",
    ]),
    ("warn", "The service principal password is displayed <b>once</b>. The script also writes it to "
             "<font face='Courier'>sp-credentials.json</font>, which is git-ignored, so that the "
             "credential-loading script can read it without anything being retyped."),

    ("h2", "Step 3 - Start Jenkins"),
    ("code", """
docker compose up -d --build
"""),
    ("p", "The first build takes about five minutes: it installs the Docker CLI, Azure CLI, kubectl, "
          "Gitleaks and Ansible into the image and pre-installs the plugins listed in "
          "<font face='Courier'>jenkins/plugins.txt</font>. Jenkins is then on "
          "<font face='Courier'>http://localhost:8090</font>. Port 8090 rather than 8080 because a "
          "separately installed native Jenkins may already hold 8080."),
    ("p", "The setup wizard is skipped entirely: "
          "<font face='Courier'>-Djenkins.install.runSetupWizard=false</font> plus "
          "<font face='Courier'>jenkins/init.groovy.d/01-security.groovy</font>, which creates the "
          "admin user from <font face='Courier'>JENKINS_ADMIN_USER</font> and "
          "<font face='Courier'>JENKINS_ADMIN_PASSWORD</font> supplied by the git-ignored "
          "<font face='Courier'>.env</font> file."),

    ("h2", "Step 4 - SonarQube Cloud"),
    ("numbers", [
        "Sign in at sonarcloud.io <b>with GitHub</b>.",
        "Create a free organisation and import the repository.",
        "<b>Turn Automatic Analysis off</b> (Administration -> Analysis Method). This is the step "
        "people miss.",
        "Note the organisation key and project key.",
        "Generate a token: avatar -> My Account -> Security.",
        "Put the two keys into the <font face='Courier'>Jenkinsfile</font> "
        "(<font face='Courier'>SONAR_ORG</font>, <font face='Courier'>SONAR_PROJECT_KEY</font>), "
        "commit and push.",
    ]),

    ("h2", "Step 5 - Credentials into Jenkins"),
    ("code", """
SONAR_TOKEN=<token> bash infra/jenkins-azure-credentials.sh
"""),
    ("p", "Reads <font face='Courier'>sp-credentials.json</font> and creates all four credentials "
          "through the Jenkins script console, so nothing is typed into a web form. Or do it by hand: "
          "Manage Jenkins -> Credentials -> System -> Global credentials."),

    ("h2", "Step 6 - The job"),
    ("code", """
bash infra/jenkins-bootstrap.sh --build
"""),
    ("p", "Creates the job from <font face='Courier'>jenkins/job-config.xml</font> via the REST API "
          "and starts a build. By hand: New Item -> Pipeline -> Build Triggers: Poll SCM -> Pipeline "
          "script from SCM -> Git -> repository URL -> branch "
          "<font face='Courier'>*/main</font> -> Script Path "
          "<font face='Courier'>Jenkinsfile</font>."),

    ("h2", "Step 7 - Prove a change flows through"),
    ("code", """
# edit the release message
sed -i 's/APP_RELEASE_MESSAGE: .*/APP_RELEASE_MESSAGE: "Release 2"/' k8s/01-configmap.yaml
git commit -am "Demo: change the release message"
git push
# within 2 minutes Jenkins starts a build by itself; then refresh the browser
"""),

    ("h2", "Step 8 - Protect the credits"),
    ("code", """
bash infra/azure-pause.sh     # ~0.35 USD/day instead of ~2.05
bash infra/azure-resume.sh    # bring it back
bash infra/azure-teardown.sh  # delete everything
"""),
])

mk(F, [("pb",)])

# ===========================================================================
# PART 4
# ===========================================================================
mk(F, [
    ("h1", "Part 4 - Jenkins In Detail"),

    ("h2", "4.1 What is in the image, and why"),
    ("p", "<font face='Courier'>jenkins/Dockerfile</font> extends "
          "<font face='Courier'>jenkins/jenkins:2.516.3-lts-jdk21</font> and adds every tool the "
          "<font face='Courier'>Jenkinsfile</font> shells out to. The point is that the build agent is "
          "<b>defined as code</b>: there is no \"someone installed kubectl on the server once\" step "
          "that cannot be reproduced."),
    ("table", [
        ["Tool", "Which stage needs it"],
        ["docker CLI", "Stage 5 builds the image. Only the CLI - the daemon is the host's, reached through the mounted socket"],
        ["az (Azure CLI)", "Stages 6 and 7: authenticate, az acr login, az aks get-credentials"],
        ["kubectl", "Stages 7 and 8: apply manifests, rollout status, smoke test"],
        ["gitleaks", "Stage 2 secret scanning"],
        ["ansible", "Stage 7 deployment automation"],
        ["envsubst (gettext-base)", "k8s/render.sh substitutes the image tag into the manifests"],
        ["git, python3, jq", "Checkout metadata and small parsing tasks"],
    ], [34, 140]),
    ("note", "<b>No Docker-in-Docker.</b> The container mounts "
             "<font face='Courier'>/var/run/docker.sock</font> and uses the <i>host's</i> daemon. "
             "There is no nested daemon and no <font face='Courier'>--privileged</font>. The cost is "
             "that the container runs as root to open that socket, which is root-equivalent on the "
             "host - listed honestly as a limitation in Part 8."),

    ("h2", "4.2 Plugins, and what each is for"),
    ("table", [
        ["Plugin", "Purpose"],
        ["workflow-aggregator", "The Pipeline suite - without it a Jenkinsfile cannot run at all"],
        ["pipeline-stage-view", "The stage-by-stage graphical view; this is what you screenshot"],
        ["git", "Cloning the repository and SCM polling"],
        ["github", "GitHub integration and the /github-webhook/ endpoint"],
        ["credentials-binding", "Provides withCredentials, which injects secrets as env vars and masks them in logs"],
        ["plain-credentials", "The Secret text credential type"],
        ["junit", "Parses target/surefire-reports/*.xml into the test trend chart"],
        ["timestamper", "Timestamps on every console line - very useful when diagnosing a slow stage"],
        ["ws-cleanup", "Workspace cleanup between builds"],
    ], [44, 130]),

    ("h2", "4.3 Credentials - the four, and how they are used"),
    ("table", [
        ["ID", "Kind", "Contents", "Used by"],
        ["azure-sp", "Username/Password", "Service principal appId and password", "Stages 6 and 7, for az login"],
        ["azure-tenant-id", "Secret text", "Entra ID tenant GUID", "Stages 6 and 7, az login --tenant"],
        ["azure-subscription-id", "Secret text", "Subscription GUID", "Stages 6 and 7, az account set"],
        ["sonarcloud-token", "Secret text", "SonarQube Cloud analysis token", "Stage 4, -Dsonar.token"],
    ], [38, 32, 52, 52]),
    ("p", "They are injected only inside a <font face='Courier'>withCredentials</font> block, which "
          "binds them to environment variables for the duration of that block and <b>masks them in the "
          "console log</b> - you see <font face='Courier'>-Dsonar.token=****</font> and a line saying "
          "\"Masking supported pattern matches of $SONAR_TOKEN\". Outside the block the variables do "
          "not exist."),
    ("h3", "Why a service principal and not a password or a personal account"),
    ("p", "A service principal is a non-human identity for an application. It can be scoped narrowly, "
          "revoked without affecting a person, and rotated independently. This one has exactly three "
          "role assignments and nothing subscription-wide."),

    ("h2", "4.4 When does the pipeline trigger? (read this twice)"),
    ("p", "Three ways a build starts. Be precise about which one you are demonstrating."),
    ("table", [
        ["Trigger", "Declared as", "When it fires"],
        ["SCM polling", "pollSCM('H/2 * * * *')", "Jenkins asks GitHub every ~2 min whether main has a new commit; if yes, it builds. This is the primary automatic trigger here"],
        ["GitHub webhook", "githubPush()", "GitHub POSTs to /github-webhook/ the instant you push. Needs Jenkins reachable from the internet - it is not, on localhost, unless you run a tunnel"],
        ["Manual", "Build / Build with Parameters", "A human clicks, or something POSTs to the REST API"],
    ], [34, 46, 94]),
    ("h3", "Reading the cron field"),
    ("p", "Jenkins cron has five fields: minute, hour, day-of-month, month, day-of-week. "
          "<font face='Courier'>H/2 * * * *</font> means \"every 2 minutes\". The "
          "<font face='Courier'>H</font> is Jenkins-specific and stands for <b>hash</b>: instead of "
          "every job firing exactly on the minute, Jenkins spreads load by hashing the job name to "
          "pick an offset. <font face='Courier'>H/2</font> is therefore \"every two minutes, at a "
          "consistent but arbitrary offset\". Writing <font face='Courier'>*/2</font> would make every "
          "job on the controller poll simultaneously."),
    ("h3", "Why polling rather than a webhook here"),
    ("p", "Jenkins is on <font face='Courier'>localhost</font>, which GitHub cannot reach - inbound "
          "connections to a laptop are not routable. Polling works because it is <b>outbound</b>: "
          "Jenkins asks GitHub, not the other way round. This still satisfies \"the pipeline runs "
          "automatically\", because no human clicks Build. The cost is up to two minutes of latency "
          "and a small amount of wasted polling traffic. A webhook is instant and quieter, which is "
          "why production systems prefer it."),
    ("note", "If you want an instant webhook for a demo, expose Jenkins with a free tunnel: "
             "<font face='Courier'>cloudflared tunnel --url http://localhost:8090</font>, then set the "
             "webhook Payload URL to <font face='Courier'>https://&lt;id&gt;.trycloudflare.com/github-webhook/</font>. "
             "The URL changes each restart."),

    ("h2", "4.5 Pipeline options, and what each prevents"),
    ("table", [
        ["Option", "Effect"],
        ["timestamps()", "Prefixes every console line with a timestamp"],
        ["buildDiscarder(logRotator(numToKeepStr: '20'))", "Keeps only the last 20 builds, so the disk does not fill"],
        ["timeout(time: 30, unit: 'MINUTES')", "Aborts a hung build instead of occupying the executor forever"],
        ["disableConcurrentBuilds()", "Queues builds instead of running two at once. Essential here: two builds deploying to the same namespace would race"],
    ], [66, 108]),

    ("h2", "4.6 Parameters"),
    ("table", [
        ["Parameter", "Values", "Effect"],
        ["DEPLOY_TARGET", "azure (default), local", "azure pushes to ACR and deploys to AKS. local deploys to Docker Desktop Kubernetes and skips stage 6. Stages 1-5 are identical"],
        ["RUN_SONAR", "true (default), false", "Untick to prove the rest of the pipeline before SonarCloud is configured"],
    ], [32, 36, 106]),
    ("p", "<b>Why azure is the default.</b> A build started by SCM polling uses the defaults. If the "
          "default were <font face='Courier'>local</font>, a plain "
          "<font face='Courier'>git push</font> would deploy to the laptop rather than to Azure, and "
          "the \"change reaches the public endpoint automatically\" demonstration would not work."),
])

mk(F, [("pb",)])

# ===========================================================================
# PART 5
# ===========================================================================
mk(F, [
    ("h1", "Part 5 - The Pipeline, Stage By Stage"),
    ("p", "For each stage: what it does, why it exists, and what makes it fail. Stages run in order "
          "and the build stops at the first failure, so a defect never reaches the cluster."),

    ("h2", "Stage 1 - Checkout"),
    ("p", "Clones the commit, then reads the short SHA, author and subject with "
          "<font face='Courier'>git rev-parse</font> and "
          "<font face='Courier'>git log -1</font>, and derives the single most important variable in "
          "the pipeline:"),
    ("code", """
env.IMAGE_TAG  = "${env.BUILD_NUMBER}-${env.COMMIT_SHA}"      // e.g. 8-95e0d05
env.FULL_IMAGE = "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}"
"""),
    ("p", "<b>Why that tag format.</b> The build number orders releases; the commit SHA ties the image "
          "to exact source. Given a running pod you can name the commit and the Jenkins build that "
          "produced it. That is the answer to failure 4 (untraceable)."),
    ("warn", "<b>Why not <font face='Courier'>latest</font>?</b> Because the pod template would be "
             "byte-identical between builds, so <font face='Courier'>kubectl apply</font> reports "
             "\"unchanged\", Kubernetes does nothing, and the pipeline goes green while the old code "
             "keeps serving. This is the single most common broken-CD bug. A unique tag per build "
             "guarantees the pod spec changes, which guarantees a real rolling update."),

    ("h2", "Stage 2 - Secret Scan (Gitleaks)"),
    ("code", """
gitleaks git . --config .gitleaks.toml --redact \\
    --report-format sarif --report-path gitleaks-report.sarif \\
    --exit-code 1 --verbose
"""),
    ("bullets", [
        "<font face='Courier'>git .</font> - scan the whole history, not just the working tree",
        "<font face='Courier'>--redact</font> - do not print the secret itself into the build log, "
        "which would simply move the leak",
        "<font face='Courier'>--exit-code 1</font> - fail the build on any finding",
        "SARIF report archived as a build artifact for the audit trail",
    ]),
    ("p", "<b>Fails when:</b> any committed credential matches a rule, anywhere in history."),

    ("h2", "Stage 3 - Build and Unit Test (Maven)"),
    ("code", """
./mvnw -B -ntp clean verify
"""),
    ("p", "<font face='Courier'>-B</font> is batch mode (no interactive prompts, cleaner logs); "
          "<font face='Courier'>-ntp</font> suppresses transfer progress spam. The "
          "<font face='Courier'>post { always { ... } }</font> block publishes JUnit results and "
          "archives the JAR and the JaCoCo report <b>even when the stage fails</b> - which is exactly "
          "when you most want to see which test broke."),
    ("p", "<b>Fails when:</b> compilation fails, or any of the 29 tests fails."),

    ("h2", "Stage 4 - Code Quality (SonarQube Cloud)"),
    ("code", """
./mvnw -B -ntp sonar:sonar \\
    -Dsonar.host.url=https://sonarcloud.io \\
    -Dsonar.organization=manisudhan \\
    -Dsonar.projectKey=manisudhan_cicd-azure-cia2 \\
    -Dsonar.token=$SONAR_TOKEN \\
    -Dsonar.qualitygate.wait=true -Dsonar.qualitygate.timeout=300
"""),
    ("p", "Skipped when <font face='Courier'>RUN_SONAR</font> is false, via "
          "<font face='Courier'>when { expression { return params.RUN_SONAR } }</font>."),
    ("p", "<b>Fails when:</b> the Quality Gate is red; the token is wrong; or Automatic Analysis is "
          "still enabled on the project."),

    ("h2", "Stage 5 - Docker Build and Tag"),
    ("code", """
docker build \\
    --build-arg IMAGE_TAG=${IMAGE_TAG} --build-arg COMMIT_SHA=${COMMIT_SHA} \\
    --build-arg BUILD_NUMBER=${BUILD_NUMBER} \\
    -t ${FULL_IMAGE} -t ${LATEST_IMAGE} .
"""),
    ("p", "Two tags: the immutable <font face='Courier'>&lt;build&gt;-&lt;commit&gt;</font> used for "
          "deployment, and <font face='Courier'>latest</font> as a convenience pointer. The build args "
          "become OCI labels and environment variables inside the image, so the provenance travels "
          "with the artifact."),
    ("p", "<b>Fails when:</b> the Dockerfile is broken, or the Docker daemon is unreachable."),

    ("h2", "Stage 6 - Push to Azure Container Registry"),
    ("code", """
az login --service-principal -u $AZ_CLIENT_ID -p $AZ_CLIENT_SECRET -t $AZ_TENANT_ID
az account set --subscription $AZ_SUBSCRIPTION_ID
az acr login --name acrcicdcia2
docker push ${FULL_IMAGE}
docker push ${LATEST_IMAGE}
az acr repository show-tags --name acrcicdcia2 --repository cicd-demo-app \\
    --orderby time_desc --top 5 --output table
"""),
    ("p", "Only runs when <font face='Courier'>DEPLOY_TARGET == 'azure'</font>. The service principal "
          "holds <font face='Courier'>AcrPush</font>, not registry ownership. The final command prints "
          "the tag list as in-log evidence."),
    ("p", "<b>Fails when:</b> the SP lacks AcrPush, or the registry name does not match."),

    ("h2", "Stage 7 - Deploy to Kubernetes"),
    ("code", """
az aks get-credentials -g rg-cicd-cia2 -n aks-cicd-cia2 --admin --overwrite-existing
ansible-playbook ansible/deploy-app.yml -i ansible/inventory.ini \\
    -e deploy_target=azure -e image=${FULL_IMAGE} -e image_tag=${IMAGE_TAG} \\
    -e build_number=${BUILD_NUMBER} -e commit_sha=${COMMIT_SHA} \\
    -e k8s_namespace=cicd-demo
"""),
    ("p", "The playbook checks connectivity, runs "
          "<font face='Courier'>k8s/render.sh</font> (which uses "
          "<font face='Courier'>envsubst</font> on a named allow-list of variables, so nothing else in "
          "the YAML is touched), applies the rendered manifests, waits for the rollout and reports the "
          "endpoint. The rendered YAML is archived as a build artifact - so you can always see exactly "
          "what was sent to the cluster."),
    ("p", "<b>Fails when:</b> the SP cannot fetch cluster credentials (needs the Cluster Admin role), "
          "or the rollout does not complete in 300 s."),

    ("h2", "Stage 8 - Verify Deployment"),
    ("code", """
kubectl -n cicd-demo rollout status deployment/cicd-demo-app --timeout=300s
kubectl -n cicd-demo get deployment,pods,svc -o wide
# wait for the LoadBalancer public IP, then:
curl -fsS http://$PUBLIC_IP/actuator/health
DEPLOYED=$(curl -fsS http://$PUBLIC_IP/api/v1/info)
echo "$DEPLOYED" | grep -q "${IMAGE_TAG}" || exit 1
"""),
    ("p", "<b>This is the stage that makes the pipeline trustworthy.</b> It does three escalating "
          "checks: the rollout completed (so new pods passed readiness); the service answers HTTP; and "
          "the running application reports <i>this build's</i> image tag. The last assertion makes a "
          "false success impossible - a green build cannot mean \"apply succeeded but the old version "
          "is serving\"."),
    ("p", "<b>Fails when:</b> pods crash-loop, no public IP is assigned within 5 minutes, or the live "
          "endpoint reports a different image tag."),

    ("h2", "post blocks - what runs regardless"),
    ("table", [
        ["Block", "Action"],
        ["success", "Logs the image and target cluster"],
        ["failure", "Dumps pod status and the deployment description - diagnostics captured at the moment of failure"],
        ["always", "az logout, so no Azure session is left behind in the container"],
    ], [26, 148]),

    ("h2", "Failure containment summary"),
    ("table", [
        ["Failure", "Caught by", "Consequence"],
        ["Committed API key", "Stage 2", "No image built or published"],
        ["Broken unit test", "Stage 3", "JUnit report shows which test"],
        ["New bug or coverage drop", "Stage 4", "Quality Gate red, build fails"],
        ["Bad Dockerfile", "Stage 5", "Nothing pushed"],
        ["Wrong Azure permissions", "Stage 6", "Cluster untouched, old version still serving"],
        ["Pod crashes on startup", "Stage 8", "rollout times out; maxUnavailable: 0 means the old ReplicaSet served throughout"],
    ], [50, 26, 98]),
])

mk(F, [("pb",)])

# ===========================================================================
# PART 6
# ===========================================================================
mk(F, [
    ("h1", "Part 6 - Kubernetes Deep Dive"),
    ("p", "Five manifests in <font face='Courier'>k8s/</font>. Be able to explain any field."),

    ("h2", "6.1 Core objects, in one table"),
    ("table", [
        ["Object", "What it is"],
        ["Pod", "The smallest deployable unit: one or more containers sharing a network namespace and storage. You rarely create one directly"],
        ["ReplicaSet", "Keeps N identical pods running. Created and managed by a Deployment - one per pod-template version"],
        ["Deployment", "Declares the desired pod template and replica count, and manages rolling updates by creating a new ReplicaSet and scaling the old one down"],
        ["Service", "A stable virtual IP and DNS name that load-balances across the pods matching its selector. Pods are ephemeral; Services are not"],
        ["ConfigMap", "Non-secret key/value configuration, injected as env vars or files"],
        ["Secret", "The same, for sensitive values. Base64-encoded, not encrypted at rest by default"],
        ["Namespace", "A logical partition of the cluster for isolation and quota"],
        ["HPA", "HorizontalPodAutoscaler - adjusts the replica count based on observed metrics"],
    ], [30, 144]),

    ("h2", "6.2 Namespace"),
    ("code", """
apiVersion: v1
kind: Namespace
metadata:
  name: cicd-demo
"""),
    ("p", "Isolates the workload from <font face='Courier'>kube-system</font>. Makes RBAC, quotas and "
          "a single-command cleanup possible."),

    ("h2", "6.3 ConfigMap"),
    ("code", """
data:
  APP_ENVIRONMENT: "production"
  APP_RELEASE_MESSAGE: "Release 2 - this change reached Azure automatically"
  APP_IMAGE_TAG: "${IMAGE_TAG}"        # injected by the pipeline
  APP_BUILD_NUMBER: "${BUILD_NUMBER}"
  APP_COMMIT_SHA: "${COMMIT_SHA}"
"""),
    ("p", "The build-provenance keys are what let the running application display which build it is - "
          "that is how the browser demonstration proves a redeployment happened. Real credentials would "
          "never go here; they belong in a Secret backed by Azure Key Vault."),

    ("h2", "6.4 Deployment - field by field"),
    ("code", """
spec:
  replicas: 2
  revisionHistoryLimit: 5
  selector:
    matchLabels:
      app.kubernetes.io/name: cicd-demo-app
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
"""),
    ("table", [
        ["Field", "Meaning and why this value"],
        ["replicas: 2", "Two pods, so one can be replaced while the other serves. With 1 replica and maxUnavailable 0 a rolling update cannot proceed"],
        ["revisionHistoryLimit: 5", "Keep 5 old ReplicaSets for rollback; more would waste etcd space"],
        ["selector.matchLabels", "How the Deployment finds its pods. Immutable after creation - changing it requires deleting the Deployment"],
        ["strategy: RollingUpdate", "Replace pods gradually. The alternative, Recreate, kills all pods first: simpler but causes downtime"],
        ["maxSurge: 1", "At most one extra pod above the desired count during an update"],
        ["maxUnavailable: 0", "Never drop below the desired count. This is what makes the update zero-downtime - a new pod must be Ready before an old one is removed"],
    ], [42, 132]),
    ("h3", "Probes - three of them, and they are not interchangeable"),
    ("code", """
startupProbe:    /actuator/health/readiness  periodSeconds 5   failureThreshold 30
readinessProbe:  /actuator/health/readiness  periodSeconds 10  failureThreshold 3
livenessProbe:   /actuator/health/liveness   periodSeconds 20  failureThreshold 3
"""),
    ("table", [
        ["Probe", "Question it answers", "What happens on failure"],
        ["startupProbe", "Has the app finished booting?", "Keeps restarting the clock. While it runs, the other two probes are disabled. 5 s x 30 = up to 150 s for the JVM to warm up"],
        ["readinessProbe", "Can it serve traffic right now?", "The pod is removed from the Service's endpoints. It is NOT restarted - useful for a temporary dependency outage"],
        ["livenessProbe", "Is it alive, or wedged?", "The container is restarted"],
    ], [30, 46, 98]),
    ("p", "<b>Why a startupProbe at all?</b> Without one you must set "
          "<font face='Courier'>initialDelaySeconds</font> on the liveness probe large enough for the "
          "slowest possible start, which delays detection of a genuine hang for the whole life of the "
          "pod. A startupProbe lets you be patient at boot and aggressive afterwards."),
    ("h3", "Resources - requests versus limits"),
    ("code", """
resources:
  requests: { cpu: "150m", memory: "320Mi" }
  limits:   { cpu: "500m", memory: "640Mi" }
"""),
    ("p", "<b>requests</b> is what the scheduler reserves - it decides which node the pod fits on, and "
          "it is guaranteed. <b>limits</b> is the ceiling. Exceeding the CPU limit causes throttling; "
          "exceeding the memory limit causes the container to be <b>OOM-killed</b>. "
          "<font face='Courier'>150m</font> means 150 millicores, i.e. 0.15 of a core. "
          "<font face='Courier'>Mi</font> is mebibytes (1024-based); "
          "<font face='Courier'>M</font> would be megabytes (1000-based)."),
    ("p", "These numbers are deliberately small: one <font face='Courier'>Standard_B2s</font> node has "
          "2 vCPU and 4 GiB, and the system pods need part of it. 2 x 150m leaves room. If pods go "
          "<font face='Courier'>Pending</font> with \"Insufficient cpu\", this is why."),
    ("h3", "securityContext - every field, and what it stops"),
    ("code", """
# pod level
runAsNonRoot: true
runAsUser: 10001
runAsGroup: 10001
fsGroup: 10001
seccompProfile: { type: RuntimeDefault }
# container level
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities: { drop: ["ALL"] }
"""),
    ("table", [
        ["Field", "What it prevents"],
        ["runAsNonRoot / runAsUser 10001", "A container escape lands as an unprivileged user, not root"],
        ["allowPrivilegeEscalation: false", "Blocks setuid binaries from gaining privileges inside the container"],
        ["readOnlyRootFilesystem: true", "An attacker cannot write a payload to disk. Requires an emptyDir at /tmp, because embedded Tomcat needs a writable temp directory"],
        ["capabilities drop ALL", "Removes Linux capabilities such as NET_RAW and CHOWN that the app never uses"],
        ["seccompProfile RuntimeDefault", "Restricts which syscalls the container may make"],
        ["fsGroup", "Mounted volumes are group-owned by 10001 so the non-root user can write to /tmp"],
    ], [52, 122]),

    ("h2", "6.5 Service - and the four types"),
    ("code", """
spec:
  type: LoadBalancer
  selector:
    app.kubernetes.io/name: cicd-demo-app
  ports:
    - name: http
      port: 80          # the Service's port
      targetPort: http  # the container's named port (8080)
"""),
    ("table", [
        ["Type", "Behaviour"],
        ["ClusterIP", "Default. Reachable only inside the cluster, at a virtual IP and a DNS name"],
        ["NodePort", "Opens the same high port (30000-32767) on every node, which forwards to the Service"],
        ["LoadBalancer", "Asks the cloud provider for a real load balancer and public IP. On AKS this creates an Azure Standard Load Balancer. Builds on NodePort underneath"],
        ["ExternalName", "A DNS CNAME to an external hostname; no proxying"],
    ], [30, 144]),
    ("p", "<b>Service DNS.</b> Inside the cluster the full name is "
          "<font face='Courier'>cicd-demo-app.cicd-demo.svc.cluster.local</font>, i.e. "
          "<font face='Courier'>&lt;service&gt;.&lt;namespace&gt;.svc.cluster.local</font>. From "
          "inside the same namespace, just <font face='Courier'>cicd-demo-app</font> resolves."),

    ("h2", "6.6 HorizontalPodAutoscaler"),
    ("code", """
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: cicd-demo-app }
  minReplicas: 2
  maxReplicas: 5
  metrics:
    - type: Resource
      resource:
        name: cpu
        target: { type: Utilization, averageUtilization: 70 }
"""),
    ("p", "Scales between 2 and 5 pods to keep average CPU near 70 percent of the <b>request</b> (not "
          "the limit). It needs <font face='Courier'>metrics-server</font>, which AKS installs by "
          "default. Note the interaction: the HPA owns the replica count once it is active, so editing "
          "<font face='Courier'>replicas</font> by hand is temporary - the HPA will correct it."),

    ("h2", "6.7 How the manifests get this build's image"),
    ("p", "The manifests are templates containing "
          "<font face='Courier'>${IMAGE}</font>, "
          "<font face='Courier'>${IMAGE_TAG}</font>, "
          "<font face='Courier'>${BUILD_NUMBER}</font> and "
          "<font face='Courier'>${COMMIT_SHA}</font>. "
          "<font face='Courier'>k8s/render.sh</font> substitutes them with "
          "<font face='Courier'>envsubst</font>, passing an explicit list of variable names so nothing "
          "else in the YAML can be touched, and writes the result to "
          "<font face='Courier'>k8s/rendered/</font>, which the pipeline archives."),
    ("p", "<b>Why not Helm or Kustomize?</b> Both are better at scale. For five manifests whose only "
          "variable parts are an image reference and four strings, <font face='Courier'>envsubst</font> "
          "is transparent - you can read the rendered file and see exactly what was applied - and adds "
          "no tool to install or release lifecycle to explain. Say that plainly if asked; it is a "
          "defensible trade-off rather than ignorance of Helm."),
])

mk(F, [("pb",)])

# ===========================================================================
# PART 7 - the money section
# ===========================================================================
mk(F, [
    ("h1", "Part 7 - Live Operations Recipes"),
    ("p", "These are the \"change something right now\" questions. Each recipe gives the command, what "
          "actually happens, and the thing worth saying while you type."),
    ("note", "First, always: point kubectl at the right cluster. "
             "<font face='Courier'>kubectl config get-contexts</font> shows which is current; "
             "<font face='Courier'>az aks get-credentials -g rg-cicd-cia2 -n aks-cicd-cia2 --admin "
             "--overwrite-existing</font> selects AKS."),

    ("h2", "7.1 Add one more pod (scale to 3)"),
    ("p", "Three ways. Know all three and when each is right."),
    ("h3", "(a) Imperative - instant, not persisted"),
    ("code", """
kubectl -n cicd-demo scale deployment/cicd-demo-app --replicas=3
kubectl -n cicd-demo get pods -w
"""),
    ("p", "The Deployment creates one more pod from the existing ReplicaSet. Fast and ideal for a live "
          "demo. <b>But</b> it is not in Git, so the next pipeline run re-applies "
          "<font face='Courier'>replicas: 2</font> and the extra pod disappears. Say that out loud - it "
          "shows you understand GitOps drift."),
    ("h3", "(b) Declarative - the correct way"),
    ("code", """
# edit k8s/02-deployment.yaml:  replicas: 2  ->  replicas: 3
git commit -am "Scale to 3 replicas"
git push
# polling triggers the pipeline, which applies it to AKS
"""),
    ("p", "Slower, but the cluster matches the repository and the change is reviewed and auditable."),
    ("h3", "(c) Let the HPA do it"),
    ("code", """
kubectl -n cicd-demo get hpa
kubectl -n cicd-demo describe hpa cicd-demo-app
"""),
    ("p", "The HPA already scales 2-5 on 70 percent CPU. If it is active, your manual "
          "<font face='Courier'>scale</font> will be overridden within a minute or two."),
    ("warn", "On a single <font face='Courier'>Standard_B2s</font> node, a third pod requesting 150m CPU "
             "may not fit alongside the system pods. If it stays "
             "<font face='Courier'>Pending</font>, run "
             "<font face='Courier'>kubectl -n cicd-demo describe pod &lt;name&gt;</font> and read the "
             "Events - it will say \"Insufficient cpu\". Fix by adding a node (7.8) or lowering the "
             "request."),

    ("h2", "7.2 Change the pod spec"),
    ("p", "\"Pod spec\" means anything under "
          "<font face='Courier'>spec.template.spec</font> in the Deployment. Any change there creates a "
          "<b>new ReplicaSet</b> and triggers a rolling update - that is the mechanism, and it is worth "
          "stating."),
    ("h3", "Live edit, for a demo"),
    ("code", """
kubectl -n cicd-demo edit deployment/cicd-demo-app
# opens the live object in an editor; save and the rollout starts immediately
kubectl -n cicd-demo rollout status deployment/cicd-demo-app
"""),
    ("h3", "Targeted change with patch"),
    ("code", """
# change the memory limit
kubectl -n cicd-demo patch deployment/cicd-demo-app --type=json -p '[{
  "op":    "replace",
  "path":  "/spec/template/spec/containers/0/resources/limits/memory",
  "value": "768Mi"
}]'
"""),
    ("h3", "Add or change an environment variable"),
    ("code", """
kubectl -n cicd-demo set env deployment/cicd-demo-app APP_ENVIRONMENT=staging
"""),
    ("p", "Note the subtlety: the app reads most settings from the ConfigMap via "
          "<font face='Courier'>envFrom</font>. Editing the ConfigMap alone does <b>not</b> restart the "
          "pods, so the change is not picked up until they restart:"),
    ("code", """
kubectl -n cicd-demo edit configmap cicd-demo-app-config
kubectl -n cicd-demo rollout restart deployment/cicd-demo-app
"""),
    ("p", "That is a classic question: \"you changed the ConfigMap, why did nothing happen?\" Because "
          "environment variables are injected at container start and never re-read. A ConfigMap mounted "
          "as a <i>volume</i> does update in place, but the application still has to notice."),

    ("h2", "7.3 Change the image"),
    ("code", """
kubectl -n cicd-demo set image deployment/cicd-demo-app \\
    app=acrcicdcia2.azurecr.io/cicd-demo-app:7-abc1234
kubectl -n cicd-demo rollout status deployment/cicd-demo-app
"""),
    ("p", "<font face='Courier'>app</font> is the container name, not the image name. "
          "<font face='Courier'>kubectl set image &lt;resource&gt; &lt;container&gt;=&lt;image&gt;</font>."),

    ("h2", "7.4 Roll back"),
    ("code", """
kubectl -n cicd-demo rollout history deployment/cicd-demo-app
kubectl -n cicd-demo rollout undo deployment/cicd-demo-app
kubectl -n cicd-demo rollout undo deployment/cicd-demo-app --to-revision=2
"""),
    ("p", "This is why <font face='Courier'>revisionHistoryLimit: 5</font> matters, and why the "
          "Deployment sets the <font face='Courier'>kubernetes.io/change-cause</font> annotation: the "
          "history shows \"Jenkins build 8 from commit 95e0d05\" per revision rather than a meaningless "
          "list of numbers."),
    ("p", "<b>Rollback is fast because the old image is still in ACR.</b> Immutable tags per build are "
          "what make that possible - with <font face='Courier'>latest</font> only, there is nothing to "
          "roll back <i>to</i>."),

    ("h2", "7.5 Pause and resume a rollout"),
    ("code", """
kubectl -n cicd-demo rollout pause deployment/cicd-demo-app
kubectl -n cicd-demo rollout resume deployment/cicd-demo-app
"""),
    ("p", "Pausing lets you batch several spec changes into one rollout instead of triggering one per "
          "edit."),

    ("h2", "7.6 Debug a pod that will not start"),
    ("code", """
kubectl -n cicd-demo get pods
kubectl -n cicd-demo describe pod <pod>          # Events at the bottom - read these first
kubectl -n cicd-demo logs <pod>
kubectl -n cicd-demo logs <pod> --previous       # logs from the crashed instance
kubectl -n cicd-demo exec -it <pod> -- sh        # shell inside (read-only FS, remember)
kubectl -n cicd-demo get events --sort-by=.lastTimestamp
"""),
    ("table", [
        ["Status", "Usual cause", "What to check"],
        ["ImagePullBackOff", "Cannot pull the image", "AcrPull missing: az aks update --attach-acr; or a typo in the image name"],
        ["CrashLoopBackOff", "Container starts then exits", "kubectl logs --previous; usually a config or startup error"],
        ["Pending", "Cannot be scheduled", "describe pod -> Events. Usually Insufficient cpu/memory"],
        ["CreateContainerConfigError", "Missing ConfigMap or Secret key", "Check the name referenced by envFrom exists"],
        ["0/1 Running", "Readiness probe failing", "describe pod; curl the probe path from inside"],
    ], [44, 44, 86]),

    ("h2", "7.7 Expose it differently"),
    ("code", """
# temporary access without touching the Service
kubectl -n cicd-demo port-forward svc/cicd-demo-app 8081:80
# change the Service type
kubectl -n cicd-demo patch svc cicd-demo-app -p '{"spec":{"type":"NodePort"}}'
"""),
    ("p", "<font face='Courier'>port-forward</font> targets the Service, so it survives a rolling "
          "update. It is per-user and local - not a substitute for a LoadBalancer."),

    ("h2", "7.8 Add a node / resize the cluster"),
    ("code", """
az aks scale -g rg-cicd-cia2 -n aks-cicd-cia2 --node-count 2
az aks nodepool list -g rg-cicd-cia2 --cluster-name aks-cicd-cia2 -o table
kubectl get nodes -o wide
"""),
    ("p", "Doubles the node cost. Distinguish clearly: <b>scaling pods</b> is "
          "<font face='Courier'>kubectl scale</font> / the HPA and is free if capacity exists; "
          "<b>scaling nodes</b> is <font face='Courier'>az aks scale</font> / the cluster autoscaler "
          "and costs money."),

    ("h2", "7.9 Node maintenance"),
    ("code", """
kubectl cordon <node>                              # stop new pods landing here
kubectl drain <node> --ignore-daemonsets --delete-emptydir-data
kubectl uncordon <node>
"""),

    ("h2", "7.10 Inspect the live configuration"),
    ("code", """
kubectl -n cicd-demo get deployment cicd-demo-app -o yaml
kubectl -n cicd-demo get deployment cicd-demo-app \\
    -o jsonpath='{.spec.template.spec.containers[0].image}'
kubectl -n cicd-demo get svc cicd-demo-app \\
    -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
kubectl -n cicd-demo top pods        # needs metrics-server
"""),

    ("h2", "7.11 Add a second container to the pod (sidecar)"),
    ("p", "If asked to add a sidecar, the point is that containers in a pod share the network namespace "
          "and can share volumes, so they talk over <font face='Courier'>localhost</font>:"),
    ("code", """
spec:
  template:
    spec:
      containers:
        - name: app
          image: ...
        - name: log-shipper          # second container
          image: busybox:1.36
          command: ["sh","-c","tail -f /var/log/app/app.log"]
          volumeMounts:
            - name: logs
              mountPath: /var/log/app
"""),

    ("h2", "7.12 Trigger the pipeline yourself"),
    ("code", """
# in the Jenkins UI: Build with Parameters -> choose DEPLOY_TARGET -> Build
# or from a terminal:
bash infra/jenkins-bootstrap.sh --build
DEPLOY_TARGET=local RUN_SONAR=false bash infra/jenkins-bootstrap.sh --build
"""),
])

mk(F, [("pb",)])

# ===========================================================================
# PART 8
# ===========================================================================
mk(F, [
    ("h1", "Part 8 - Security"),

    ("h2", "8.1 What this implementation actually does"),
    ("numbers", [
        "<b>Secret detection as a hard gate.</b> Gitleaks scans the full history on every build and "
        "fails it on any finding, with six custom rules for the credential types this project handles.",
        "<b>No credentials in Git.</b> <font face='Courier'>.gitignore</font> and "
        "<font face='Courier'>.dockerignore</font> both exclude "
        "<font face='Courier'>.env</font>, <font face='Courier'>*.pem</font>, "
        "<font face='Courier'>*.key</font>, <font face='Courier'>kubeconfig*</font> and "
        "<font face='Courier'>*-credentials.json</font>. Jenkins holds the four secrets and injects "
        "them only inside <font face='Courier'>withCredentials</font>, which masks them in logs.",
        "<b>Least privilege in Azure.</b> The service principal is scoped to one resource group, with "
        "AcrPush on the registry and Cluster Admin on the cluster - nothing subscription-wide. AKS "
        "pulls images with its own managed identity, so no registry password exists in the cluster.",
        "<b>Hardened container.</b> JRE-only image, non-root UID 10001, read-only root filesystem, no "
        "privilege escalation, all capabilities dropped, RuntimeDefault seccomp profile.",
        "<b>Static analysis as a gate.</b> The Quality Gate blocks the build on new vulnerabilities and "
        "security hotspots.",
        "<b>Provenance.</b> Every image carries OCI labels and env vars naming its commit and build, so "
        "anything running can be traced to source.",
        "<b>Supply-chain pinning.</b> Base images pinned to specific tags, Maven pinned by the wrapper, "
        "Gitleaks and kubectl pinned by version in the Dockerfile.",
    ]),

    ("h2", "8.2 Limitations - state these before you are asked"),
    ("p", "Volunteering limitations reads as competence. Being caught without them does not."),
    ("table", [
        ["#", "Limitation", "Production remedy"],
        ["1", "Jenkins on plain HTTP with a single local admin account", "TLS in front of it; an identity provider instead of a local account"],
        ["2", "The application endpoint is HTTP only", "Ingress controller with TLS, or Azure Front Door"],
        ["3", "The Jenkins container runs as root and mounts the host Docker socket - root on the socket is root on the host", "Rootless BuildKit, Buildah, or az acr build (server-side, no local daemon)"],
        ["4", "A long-lived service principal secret is stored in Jenkins", "OIDC workload-identity federation - no stored secret at all"],
        ["5", "AKS accessed with --admin local-account credentials, bypassing Entra ID RBAC", "Disable local accounts, use Entra ID with kubelogin, bind a narrow Role"],
        ["6", "No container image vulnerability scan", "A Trivy stage failing on HIGH/CRITICAL"],
        ["7", "No image signing or SBOM", "Cosign signatures and a Syft SBOM, enforced by admission policy"],
        ["8", "Single node, single Jenkins host - no high availability", "Multi-node pool across availability zones; Jenkins with agents"],
        ["9", "No NetworkPolicies - pods can talk to anything", "Azure or Calico network policy, default-deny egress"],
        ["10", "No staging environment or approval gate; main goes straight to the only environment", "Separate namespaces or clusters with a manual approval before production"],
        ["11", "Kubernetes Secrets are base64, not encrypted", "Azure Key Vault with the Secrets Store CSI driver"],
    ], [8, 86, 80]),
])

mk(F, [("pb",)])

# ===========================================================================
# PART 9
# ===========================================================================
mk(F, [
    ("h1", "Part 9 - Problems Actually Hit"),
    ("p", "These are real failures from building this, with their root causes. They make excellent "
          "\"challenges encountered\" material because they are specific and the diagnosis is the "
          "interesting part."),
    ("table", [
        ["Symptom", "Root cause", "Fix / lesson"],
        ["kubectl apply said \"unchanged\" and no new code deployed", "The manifest referenced a mutable latest tag, so the pod template was byte-identical", "Tag every image <build>-<commit>. The lesson: a green pipeline is not evidence of a deployment"],
        ["Pipeline green but the app was broken", "The pipeline verified that the API call succeeded, not the outcome", "Added stage 8: rollout status plus an assertion that the live endpoint reports this build's tag"],
        ["Container failed at startup with a read-only filesystem", "Embedded Tomcat needs a writable temp directory", "Mount an emptyDir at /tmp and keep the rest read-only"],
        ["Jenkins could not run docker build", "On Docker Desktop the socket is root:root mode 0660, and the jenkins user is neither", "Run the container as root; recorded as limitation 3 rather than hidden"],
        ["ACR creation failed claiming the name was taken", "The real error was MissingSubscriptionRegistration - providers unregistered on a new subscription. The script had suppressed stderr with 2>/dev/null and guessed", "Register providers; never replace a provider's error with a guess. A wrong error message sends you looking in the wrong place"],
        ["Role assignment failed with (MissingSubscription)", "Git Bash rewrote the scope /subscriptions/... into C:/Program Files/Git/subscriptions/...", "export MSYS_NO_PATHCONV=1 and MSYS2_ARG_CONV_EXCL='*'"],
        ["A script died claiming Python was missing, after a 10-minute wait", "command -v python3 succeeds on Windows even when python3 is the Microsoft Store alias stub that fails when run", "Test that the interpreter actually executes, not merely that it resolves"],
        ["Image build failed on curl: (6) Could not resolve host", "Transient DNS, right after other hosts had resolved fine", "--retry-all-errors; plain --retry does not retry a resolution failure"],
        ["Jenkins container would not start: port 8090/8080 in use", "A separately installed native Jenkins already held 8080", "Publish on a different host port; identify the holder with Get-NetTCPConnection"],
        ["Scripts failed from PowerShell with execvpe(/bin/bash)", "In PowerShell, bash resolves to the WSL shim, and the only distro had no /bin/bash", "Run shell scripts from Git Bash"],
        ["Shell scripts failed on Linux with bad interpreter", "Git on Windows checks files out with CRLF", ".gitattributes forcing eol=lf for *.sh, mvnw, Jenkinsfile and YAML"],
        ["SonarCloud rejected the pipeline's analysis", "Automatic Analysis was enabled and is mutually exclusive with CI analysis", "Turn it off in Administration -> Analysis Method"],
        ["First cost estimate was far too low", "The invisible costs were the Load Balancer and the default 128 GB Premium SSD disks, which bill even while compute is stopped", "Move Jenkins off Azure, 32 GB StandardSSD disk, pause between sessions"],
    ], [48, 62, 64]),
    ("note", "<b>The meta-lesson, worth saying in a viva.</b> Most of these were not coding errors. They "
             "were <i>diagnostic</i> errors: an error message that guessed instead of reporting, a "
             "check that tested existence instead of function, a pipeline that verified a call instead "
             "of an outcome. The fix in each case was to make the system tell the truth about itself."),
])

mk(F, [("pb",)])

# ===========================================================================
# PART 10
# ===========================================================================
mk(F, [
    ("h1", "Part 10 - Question Bank"),
    ("h2", "Concepts"),
    ("qa", "What is the difference between Continuous Integration, Continuous Delivery and Continuous Deployment?",
     "CI is merging and automatically building and testing every change, so integration problems surface "
     "immediately. Continuous Delivery means every change that passes is <i>releasable</i> - the "
     "artifact is built and verified, but a human decides when to push it. Continuous Deployment goes "
     "further and releases automatically with no human gate. This project is Continuous Deployment on "
     "main: a passing build deploys to AKS unattended."),
    ("qa", "What is a pipeline \"gate\"?",
     "A check that can stop the pipeline. Gitleaks and the SonarQube Quality Gate are gates: they fail "
     "the build. A report that is merely archived is not a gate. The distinction matters because only a "
     "gate changes behaviour."),
    ("qa", "Why containers rather than deploying a JAR to a VM?",
     "The image bundles the JRE and the application, so there is no \"which Java is on the server?\" "
     "question. Images are immutable and versioned, so rollback is pulling an older tag. And the same "
     "artifact runs on a laptop and in the cloud."),
    ("qa", "Why Kubernetes rather than just running the container?",
     "Declarative desired state, self-healing, health-gated rolling updates, horizontal scaling and a "
     "stable Service abstraction in front of ephemeral pods. Running a bare container gives you none of "
     "that."),
    ("qa", "What is declarative versus imperative?",
     "Imperative says what to do (<font face='Courier'>kubectl scale --replicas=3</font>); declarative "
     "says what should be true (<font face='Courier'>replicas: 3</font> in a file that is applied). "
     "Declarative is reproducible and reviewable, which is why the manifests are in Git and the "
     "imperative commands are only for demos."),

    ("h2", "Jenkins and triggering"),
    ("qa", "When exactly does your pipeline run?",
     "Three ways. SCM polling, <font face='Courier'>pollSCM('H/2 * * * *')</font>, is the primary "
     "automatic trigger: Jenkins asks GitHub every two minutes whether main has moved and builds if it "
     "has. <font face='Courier'>githubPush()</font> is also declared and would fire instantly on a push, "
     "but GitHub cannot reach localhost, so it only works behind a tunnel. And a human or the REST API "
     "can start one manually."),
    ("qa", "What does the H in H/2 mean?",
     "Hash. Jenkins hashes the job name to choose an offset within the interval, so jobs do not all poll "
     "at the same instant. <font face='Courier'>*/2</font> would synchronise every job on the controller."),
    ("qa", "Polling is wasteful - why not a webhook?",
     "A webhook is better and is declared in the Jenkinsfile. It needs an inbound connection, and Jenkins "
     "here runs on a laptop with no public address. Polling is outbound, so it works regardless. The "
     "trade-off is up to two minutes of latency."),
    ("qa", "What is a declarative Jenkinsfile and why keep it in the repository?",
     "A structured pipeline definition (<font face='Courier'>pipeline { stages { ... } }</font>) as "
     "opposed to free-form scripted Groovy. Keeping it in the repository means the pipeline is "
     "version-controlled with the code, reviewed like code, and a branch can change its own build."),
    ("qa", "How are secrets kept out of the console log?",
     "<font face='Courier'>withCredentials</font> binds them to environment variables for the block and "
     "masks matching strings in the output. The log shows "
     "<font face='Courier'>-Dsonar.token=****</font>."),
    ("qa", "Why disableConcurrentBuilds?",
     "Two builds deploying to the same namespace simultaneously would race: whichever finished last would "
     "win, possibly deploying the older commit."),

    ("h2", "Docker"),
    ("qa", "What is a multi-stage build and what did it save?",
     "Separate build and runtime stages, copying only the artifact forward. The published image is about "
     "190 MB instead of about 600 MB, and it contains no compiler or build tool, which shrinks the attack "
     "surface."),
    ("qa", "Why copy pom.xml and resolve dependencies before copying src?",
     "Docker caches layers. Dependencies change rarely, source changes constantly. Resolving dependencies "
     "in their own earlier layer means a source-only change reuses the cache instead of re-downloading "
     "the repository."),
    ("qa", "Why does the image run as UID 10001?",
     "So a container escape lands as an unprivileged user. The Kubernetes securityContext enforces the "
     "same thing with <font face='Courier'>runAsNonRoot</font>, defence in depth."),
    ("qa", "What is .dockerignore for?",
     "It keeps files out of the build context: smaller and faster uploads, and - more importantly - it "
     "prevents <font face='Courier'>.env</font>, keys and kubeconfigs from accidentally being copied "
     "into an image layer."),

    ("h2", "Kubernetes"),
    ("qa", "Walk me through what happens when you change the image tag.",
     "The Deployment's pod template changes, so the Deployment creates a new ReplicaSet and scales it up "
     "while scaling the old one down, respecting maxSurge 1 and maxUnavailable 0. Each new pod must pass "
     "its readiness probe before it receives traffic and before an old pod is removed, so there is no "
     "downtime. The old ReplicaSet is kept, scaled to zero, for rollback."),
    ("qa", "Difference between a readiness and a liveness probe?",
     "Readiness answers \"can it serve traffic now?\" - failure removes the pod from the Service "
     "endpoints but does not restart it. Liveness answers \"is it wedged?\" - failure restarts the "
     "container. Using liveness where you meant readiness causes restart loops during a transient "
     "dependency outage."),
    ("qa", "What does a startupProbe add?",
     "It gives a slow-starting application time to boot without making the liveness probe permanently "
     "lenient. While it runs, the other probes are suspended. Here 5 s x 30 allows up to 150 s for the "
     "JVM."),
    ("qa", "requests versus limits?",
     "requests is what the scheduler reserves and is guaranteed; limits is the ceiling. Exceeding the CPU "
     "limit throttles; exceeding the memory limit gets the container OOM-killed."),
    ("qa", "Why maxUnavailable: 0?",
     "It forbids dropping below the desired replica count during an update, so a new pod must be Ready "
     "before an old one goes. That is what makes the update zero-downtime."),
    ("qa", "How does the Service find its pods?",
     "By label selector - <font face='Courier'>app.kubernetes.io/name: cicd-demo-app</font> - not by pod "
     "name. Pods come and go; labels are stable."),
    ("qa", "What do the Service types do?",
     "ClusterIP is internal only. NodePort opens a high port on every node. LoadBalancer asks the cloud "
     "for a real load balancer and public IP, building on NodePort. ExternalName is a DNS alias."),
    ("qa", "Who creates the public IP?",
     "The Azure cloud-controller-manager, in response to <font face='Courier'>type: LoadBalancer</font>. "
     "It provisions an Azure Standard Load Balancer and a public IP in the AKS-managed "
     "<font face='Courier'>MC_*</font> resource group. It takes two to five minutes, which is why stage 8 "
     "polls for it."),
    ("qa", "Why is there a second resource group starting with MC_?",
     "AKS puts the cluster object in your group but the real compute, networking and load balancer in a "
     "managed cluster group it owns. You should not edit it by hand. Deleting your group removes both."),
    ("qa", "You changed the ConfigMap and nothing happened. Why?",
     "Environment variables are injected when the container starts and never re-read. You need "
     "<font face='Courier'>kubectl rollout restart deployment/cicd-demo-app</font>. A ConfigMap mounted "
     "as a volume does update in place, but the application must watch for it."),
    ("qa", "How do you roll back?",
     "<font face='Courier'>kubectl rollout undo deployment/cicd-demo-app</font>, optionally "
     "<font face='Courier'>--to-revision=N</font>. It works because old ReplicaSets are retained and the "
     "old images are still in ACR under immutable tags."),
    ("qa", "A pod is Pending. What do you do?",
     "<font face='Courier'>kubectl describe pod</font> and read the Events. On this one-node B2s cluster "
     "the usual answer is Insufficient cpu. Fix by adding a node or reducing the request."),
    ("qa", "A pod is in ImagePullBackOff. Why?",
     "The kubelet cannot pull the image. Most likely the AcrPull grant is missing - "
     "<font face='Courier'>az aks update --attach-acr acrcicdcia2</font> - or the image reference is "
     "wrong."),
    ("qa", "What is the difference between scaling pods and scaling nodes?",
     "<font face='Courier'>kubectl scale</font> or the HPA changes the number of pods and is free if the "
     "node has capacity. <font face='Courier'>az aks scale</font> changes the number of VMs and costs "
     "money. Pods cannot scale beyond what the nodes can hold."),

    ("h2", "Azure"),
    ("qa", "Why ACR rather than Docker Hub?",
     "It is in the same cloud and region as the cluster, it is private, and AKS authenticates with its "
     "managed identity through the AcrPull role - so no registry password exists in the cluster or in "
     "Jenkins."),
    ("qa", "What permissions does Jenkins have in Azure, and why those?",
     "Contributor scoped to the single resource group, AcrPush on the registry so it can push but not "
     "administer it, and Azure Kubernetes Service Cluster Admin on the cluster so it can fetch "
     "credentials. Nothing subscription-wide."),
    ("qa", "What does --attach-acr actually do?",
     "Grants the cluster's kubelet managed identity the AcrPull role on that registry, so image pulls are "
     "authenticated without a secret."),
    ("qa", "What does your infrastructure cost, and how do you control it?",
     "About US$0.085/hour, roughly US$2.05/day: the B2s node, the Standard Load Balancer, a static public "
     "IP, a 32 GB StandardSSD disk and ACR Basic. The AKS control plane is free on the Free tier, and "
     "Jenkins runs locally so costs nothing. <font face='Courier'>azure-pause.sh</font> stops the cluster "
     "and drops it to about US$0.35/day; teardown deletes the resource group."),

    ("h2", "Quality and security"),
    ("qa", "Why Gitleaks when .gitignore already excludes secrets?",
     "<font face='Courier'>.gitignore</font> is advisory and only helps for files nobody forces. It does "
     "nothing about a key pasted into a source file, and nothing about history. Gitleaks scans every "
     "commit and fails the build."),
    ("qa", "A secret was committed and then deleted. Is it safe?",
     "No. It is still in the git object database and recoverable by anyone who clones. It must be rotated, "
     "and the history rewritten if it is to be removed. This is exactly why the scan covers history "
     "rather than the working tree."),
    ("qa", "What does the Quality Gate check?",
     "On new code: no new blocker or critical issues, security hotspots reviewed, coverage at or above 80 "
     "percent, duplication below 3 percent. This project reports 95.7 percent instruction coverage."),
    ("qa", "What would you add next, given more time?",
     "A Trivy image scan failing on HIGH/CRITICAL; Cosign signing with an SBOM; a staging namespace with a "
     "manual approval before production; NetworkPolicies with default-deny egress; and replacing the "
     "service principal secret with OIDC workload-identity federation."),
])

mk(F, [("pb",)])

# ===========================================================================
# APPENDICES
# ===========================================================================
mk(F, [
    ("h1", "Appendix A - Command Cheat Sheet"),
    ("h2", "Kubernetes"),
    ("code", """
kubectl config get-contexts
az aks get-credentials -g rg-cicd-cia2 -n aks-cicd-cia2 --admin --overwrite-existing

kubectl -n cicd-demo get deployment,pods,svc -o wide
kubectl -n cicd-demo describe pod <pod>
kubectl -n cicd-demo logs <pod> [--previous] [-f]
kubectl -n cicd-demo exec -it <pod> -- sh
kubectl -n cicd-demo get events --sort-by=.lastTimestamp
kubectl -n cicd-demo top pods

kubectl -n cicd-demo scale deployment/cicd-demo-app --replicas=3
kubectl -n cicd-demo set image deployment/cicd-demo-app app=<registry>/<img>:<tag>
kubectl -n cicd-demo set env deployment/cicd-demo-app KEY=value
kubectl -n cicd-demo edit deployment/cicd-demo-app
kubectl -n cicd-demo rollout status   deployment/cicd-demo-app
kubectl -n cicd-demo rollout history  deployment/cicd-demo-app
kubectl -n cicd-demo rollout undo     deployment/cicd-demo-app [--to-revision=N]
kubectl -n cicd-demo rollout restart  deployment/cicd-demo-app
kubectl -n cicd-demo port-forward svc/cicd-demo-app 8081:80
"""),
    ("h2", "Azure"),
    ("code", """
az account show -o table
az resource list -o table
az group list -o table

az acr repository list --name acrcicdcia2 -o table
az acr repository show-tags --name acrcicdcia2 --repository cicd-demo-app \\
    --orderby time_desc -o table

az aks show -g rg-cicd-cia2 -n aks-cicd-cia2 \\
    --query "{state:provisioningState,power:powerState.code,k8s:kubernetesVersion}" -o json
az aks scale -g rg-cicd-cia2 -n aks-cicd-cia2 --node-count 2
az aks stop  -g rg-cicd-cia2 -n aks-cicd-cia2
az aks start -g rg-cicd-cia2 -n aks-cicd-cia2
az aks update -g rg-cicd-cia2 -n aks-cicd-cia2 --attach-acr acrcicdcia2

az role assignment list --assignee <appId> --all -o table
"""),
    ("h2", "Local, Maven, Docker, Jenkins"),
    ("code", """
./mvnw clean verify                 # 29 tests + JaCoCo -> target/site/jacoco/index.html
./mvnw spring-boot:run              # run on :8080
docker build -t cicd-demo-app:local .
docker run --rm -p 9090:8080 cicd-demo-app:local

docker compose up -d --build        # start Jenkins on :8090
docker compose logs -f jenkins
docker compose exec jenkins cat /usr/local/share/toolchain.txt
docker compose stop | down [-v]

bash infra/azure-setup.sh           # provision
bash infra/local-connect.sh         # point Jenkins at Docker Desktop Kubernetes
bash infra/jenkins-bootstrap.sh --build
bash infra/azure-pause.sh | azure-resume.sh | azure-teardown.sh

gitleaks git . --config .gitleaks.toml --redact --exit-code 1
"""),

    ("h1", "Appendix B - File Inventory"),
    ("table", [
        ["File", "Purpose"],
        ["Jenkinsfile", "The 8-stage declarative pipeline, with DEPLOY_TARGET and RUN_SONAR parameters"],
        ["docker-compose.yml", "Runs the Jenkins controller locally on port 8090"],
        ["jenkins/Dockerfile", "Jenkins image with docker CLI, az, kubectl, gitleaks, ansible, envsubst"],
        ["jenkins/plugins.txt", "Plugins pre-installed at image build time"],
        ["jenkins/init.groovy.d/01-security.groovy", "Creates the admin user; skips the setup wizard"],
        ["jenkins/job-config.xml", "The job definition, applied through the REST API"],
        ["pom.xml", "Maven build, JaCoCo, SonarQube configuration"],
        ["mvnw, .mvn/", "Maven wrapper - pins Maven 3.9.9, so no Maven install is needed"],
        ["Dockerfile", "Multi-stage application image, runs as UID 10001"],
        [".dockerignore", "Keeps the build context small and secret-free"],
        [".gitleaks.toml", "Secret-scanning rules plus a narrow documented allowlist"],
        [".gitattributes", "Forces LF endings so shell scripts run on Linux"],
        [".env.example", "Template for the git-ignored .env (Jenkins admin credentials)"],
        ["k8s/00..04-*.yaml", "Namespace, ConfigMap, Deployment, Service, HPA"],
        ["k8s/render.sh", "Substitutes this build's image tag with envsubst"],
        ["ansible/deploy-app.yml", "USED by stage 7: renders manifests, applies, waits, reports"],
        ["ansible/jenkins-setup.yml", "OPTIONAL: provisions an Azure VM Jenkins instead"],
        ["infra/azure-setup.sh", "Creates resource group, providers, ACR, AKS, service principal"],
        ["infra/azure-pause.sh / resume / teardown", "Cost control and cleanup"],
        ["infra/local-connect.sh", "Points Jenkins at Docker Desktop Kubernetes"],
        ["infra/jenkins-bootstrap.sh", "Creates/updates the job and can start a build"],
        ["infra/jenkins-azure-credentials.sh", "Loads all four credentials into Jenkins"],
        ["docs/SETUP.md / LOCAL.md / REPORT.md", "Azure runbook, local runbook, technical report"],
    ], [58, 116]),

    ("h1", "Appendix C - Numbers To Memorise"),
    ("table", [
        ["Fact", "Value"],
        ["Pipeline stages", "8"],
        ["Unit tests", "29, all passing"],
        ["Coverage", "95.7% instruction, 88.5% branch"],
        ["Replicas", "2 (HPA 2-5 at 70% CPU)"],
        ["Image tag format", "<build-number>-<commit-sha>, e.g. 8-95e0d05"],
        ["Rolling update", "maxSurge 1, maxUnavailable 0"],
        ["Container user", "UID 10001, non-root, read-only root filesystem"],
        ["Resource requests / limits", "150m / 500m CPU, 320Mi / 640Mi memory"],
        ["Polling interval", "H/2 * * * * (about every 2 minutes)"],
        ["Image size", "about 190 MB (JRE Alpine) vs about 600 MB with the JDK"],
        ["AKS node", "1 x Standard_B2s (2 vCPU, 4 GiB), 32 GB StandardSSD, Free tier control plane"],
        ["Cost", "about US$2.05/day running, about US$0.35/day paused"],
        ["Gitleaks rules", "~170 default + 6 custom"],
        ["Jenkins credentials", "4: azure-sp, azure-tenant-id, azure-subscription-id, sonarcloud-token"],
        ["Service", "LoadBalancer, port 80 -> targetPort 8080"],
    ], [60, 114]),
    ("sp", 8),
    ("note", "<b>If you remember only one thing:</b> every image is tagged "
             "<font face='Courier'>&lt;build&gt;-&lt;commit&gt;</font>, which is what makes rolling "
             "updates actually roll, rollback possible, and any running pod traceable to source. Almost "
             "every other design decision in this project follows from that one."),
])

doc.build(F)
print("written:", OUT)
