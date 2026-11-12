#!/usr/bin/env python
"""One-page viva survival sheet."""
import sys
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, PageBreak, PageTemplate,
                                Paragraph, Preformatted, Spacer, Table, TableStyle)

OUT = sys.argv[1] if len(sys.argv) > 1 else "cheatsheet.pdf"
INK = colors.HexColor("#111827")
ACCENT = colors.HexColor("#1d4ed8")
MUTED = colors.HexColor("#4b5563")
RULE = colors.HexColor("#d1d5db")
CODEBG = colors.HexColor("#f3f4f6")
OKBG = colors.HexColor("#ecfdf5")

ss = getSampleStyleSheet()
S = {
    "h0": ParagraphStyle("h0", parent=ss["Title"], fontName="Helvetica-Bold",
                         fontSize=17, leading=21, textColor=INK, spaceAfter=2, alignment=0),
    "sub": ParagraphStyle("sub", parent=ss["Normal"], fontSize=9, leading=12,
                          textColor=MUTED, spaceAfter=8),
    "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontName="Helvetica-Bold",
                         fontSize=11.5, leading=14, textColor=ACCENT,
                         spaceBefore=10, spaceAfter=4),
    "p": ParagraphStyle("p", parent=ss["BodyText"], fontSize=8.8, leading=12.2,
                        textColor=INK, spaceAfter=4),
    "code": ParagraphStyle("code", parent=ss["Code"], fontName="Courier",
                           fontSize=7.6, leading=9.8, textColor=INK,
                           backColor=CODEBG, borderColor=RULE, borderWidth=0.5,
                           borderPadding=5, spaceBefore=3, spaceAfter=5),
    "ok": ParagraphStyle("ok", parent=ss["BodyText"], fontSize=8.8, leading=12.2,
                         textColor=INK, backColor=OKBG,
                         borderColor=colors.HexColor("#6ee7b7"), borderWidth=0.6,
                         borderPadding=6, spaceBefore=4, spaceAfter=7),
    "cell": ParagraphStyle("cell", parent=ss["BodyText"], fontSize=8.2, leading=11,
                           textColor=INK, spaceAfter=0),
    "cellh": ParagraphStyle("cellh", parent=ss["BodyText"], fontSize=8.2, leading=11,
                            fontName="Helvetica-Bold", textColor=colors.white, spaceAfter=0),
}


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def mk(flow, blocks):
    for b in blocks:
        k = b[0]
        if k == "h1":
            flow.append(Paragraph(esc(b[1]), S["h1"]))
        elif k == "p":
            flow.append(Paragraph(b[1], S["p"]))
        elif k == "ok":
            flow.append(Paragraph(b[1], S["ok"]))
        elif k == "code":
            flow.append(Preformatted(b[1].strip("\n"), S["code"]))
        elif k == "pb":
            flow.append(PageBreak())
        elif k == "table":
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
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            flow.append(t)
            flow.append(Spacer(1, 5))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(14 * mm, 8 * mm, "CIA-2 viva survival sheet")
    canvas.drawRightString(A4[0] - 14 * mm, 8 * mm, "Page %d" % doc.page)
    canvas.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
                      topMargin=13 * mm, bottomMargin=13 * mm,
                      title="CIA-2 viva survival sheet")
doc.addPageTemplates([PageTemplate(id="m",
                                   frames=[Frame(doc.leftMargin, doc.bottomMargin,
                                                 doc.width, doc.height, id="f")],
                                   onPage=footer)])
W = 182
F = []
F.append(Paragraph("Viva survival sheet", S["h0"]))
F.append(Paragraph("If you only read one page before the viva, read this one.", S["sub"]))

mk(F, [
    ("h1", "1. The six commands that answer most questions"),
    ("p", "Run these in a terminal, or in the Azure portal: "
          "<b>aks-cicd-cia2 &rarr; Run command</b> (left menu, under Settings). "
          "Everything lives in the namespace <font face='Courier'>cicd-demo</font>."),
    ("code", """
kubectl -n cicd-demo get deployment,pods,svc      # what is running
kubectl -n cicd-demo describe pod <pod>           # why is it unhappy (read Events)
kubectl -n cicd-demo logs <pod>                   # what the app printed
kubectl -n cicd-demo scale deployment/cicd-demo-app --replicas=3
kubectl -n cicd-demo rollout history deployment/cicd-demo-app
kubectl -n cicd-demo rollout undo deployment/cicd-demo-app
"""),
    ("ok", "<b>If you remember nothing else:</b> <font face='Courier'>get</font> shows you "
           "what exists, <font face='Courier'>describe</font> tells you why it is "
           "misbehaving, <font face='Courier'>logs</font> shows what the app said. Almost "
           "every \"look at X\" question is one of those three."),

    ("h1", "2. If she asks you to CHANGE something"),
    ("table", [
        ["She says", "You type"],
        ["Add another pod / scale up", "kubectl -n cicd-demo scale deployment/cicd-demo-app --replicas=3"],
        ["Go back to the previous version", "kubectl -n cicd-demo rollout undo deployment/cicd-demo-app"],
        ["Change a setting the app reads", "kubectl -n cicd-demo edit configmap cicd-demo-app-config<br/>then: kubectl -n cicd-demo rollout restart deployment/cicd-demo-app"],
        ["Change anything in the pod spec", "kubectl -n cicd-demo edit deployment/cicd-demo-app"],
        ["Restart the app", "kubectl -n cicd-demo rollout restart deployment/cicd-demo-app"],
        ["Deploy a different image", "kubectl -n cicd-demo set image deployment/cicd-demo-app app=acrcicdcia2.azurecr.io/cicd-demo-app:8-95e0d05"],
        ["Add a node to the cluster", "az aks scale -g rg-cicd-cia2 -n aks-cicd-cia2 --node-count 2"],
    ], [52, 130]),
    ("p", "<b>Watch what happens afterwards</b> - that is half the marks: "
          "<font face='Courier'>kubectl -n cicd-demo get pods -w</font> "
          "(Ctrl+C to stop)."),

    ("h1", "3. The one idea that explains everything"),
    ("p", "Kubernetes is a <b>thermostat, not a script</b>. You never tell it what to do. You "
          "tell it what should be true - \"two copies of this image should be running\" - and a "
          "controller loops forever: read the desired state, look at reality, fix the difference."),
    ("p", "That single sentence answers a huge range of questions. Why did the pod come back "
          "when I deleted it? The ReplicaSet saw 1 where it wanted 2. Why did my manual change "
          "get undone? Something else owns that number. What happens if a node dies? The pods "
          "are rescheduled, because the desired state still says they should exist."),
    ("p", "<b>spec</b> = what you want. <b>status</b> = what you have. The whole system is the "
          "loop closing the gap between those two."),

    ("h1", "4. When you genuinely do not know"),
    ("p", "Do not freeze and do not guess. Say what you would <i>do</i>. This is a real "
          "engineering answer and it scores better than a wrong fact:"),
    ("ok", "\"I am not certain off the top of my head, but I would find out by running "
           "<font face='Courier'>kubectl describe</font> on it and reading the Events, because "
           "that is where Kubernetes reports why it could not do what was asked.\""),
    ("p", "Then actually run it. Reading output calmly in front of the examiner is a better "
          "demonstration of competence than reciting something memorised."),

    ("pb",),

    ("h1", "5. Things that LOOK broken but are not"),
    ("table", [
        ["Symptom", "What is really happening"],
        ["Pod name changed after a redeploy", "Pods are disposable. Every new version creates new pods with new names. The Service keeps the stable address - that is what it is for"],
        ["A manual scale got reverted", "An HPA owned the replica count. It has been removed from this cluster, so scaling now sticks"],
        ["Service shows EXTERNAL-IP pending", "Azure takes 2-5 minutes to create the load balancer. Wait, do not re-apply"],
        ["Pod says Pending", "It does not fit on the node. describe pod, read Events: \"Insufficient cpu\". Fix: fewer replicas, or add a node"],
        ["Pod says ImagePullBackOff", "It cannot pull the image. Usually the AcrPull permission or a typo in the image name"],
        ["Changed the ConfigMap, nothing happened", "Environment variables are read once at container start. Needs a rollout restart"],
        ["Builds 2-5 are red in Jenkins", "They ran before SonarCloud was configured. The Quality Gate correctly refused to pass. Builds 8 and 11 are the green ones"],
        ["14 extra pods in kube-system", "Kubernetes' own components - DNS, metrics, networking. AKS installs them; you did not"],
    ], [48, 134]),

    ("h1", "6. Where everything lives"),
    ("table", [
        ["Thing", "Where"],
        ["The running app", "http://cicd-demo-cia2.centralindia.cloudapp.azure.com"],
        ["Jenkins", "http://localhost:8090 (user admin)"],
        ["Pods in the portal", "aks-cicd-cia2 &rarr; Kubernetes resources &rarr; Workloads &rarr; namespace cicd-demo"],
        ["Run kubectl in the portal", "aks-cicd-cia2 &rarr; Run command (left menu, under Settings)"],
        ["Images", "acrcicdcia2 &rarr; Repositories &rarr; cicd-demo-app"],
        ["Code", "github.com/manisudhan/cicd-azure-cia2"],
        ["Code quality", "sonarcloud.io &rarr; manisudhan_cicd-azure-cia2"],
        ["The full explanation", "docs/CICD-Study-Guide.pdf in the repo"],
    ], [42, 140]),

    ("h1", "7. Numbers worth knowing cold"),
    ("table", [
        ["Fact", "Value"],
        ["Pipeline stages", "8"],
        ["Unit tests", "29, all passing"],
        ["Code coverage", "95.7% instruction, 88.5% branch"],
        ["Replicas", "2"],
        ["Image tag format", "&lt;build&gt;-&lt;commit&gt;, e.g. 11-ac268ea"],
        ["Why not 'latest'", "kubectl apply would report \"unchanged\" and nothing would redeploy"],
        ["Rolling update", "maxSurge 1, maxUnavailable 0 - new pod Ready before an old one goes"],
        ["Node", "1 x Standard_B2s, 2 vCPU, 4 GiB"],
        ["Cost", "about 2 USD per day"],
        ["The two gates", "Gitleaks (secrets) and SonarQube Cloud (quality) - both FAIL the build"],
    ], [52, 130]),

    ("h1", "8. The 30-second demo, if you get to choose"),
    ("p", "Open <font face='Courier'>http://cicd-demo-cia2.centralindia.cloudapp.azure.com</font> in a browser. In a terminal, "
          "delete a pod. Refresh the browser - still up. Show the new pod."),
    ("code", """
kubectl -n cicd-demo get pods
kubectl -n cicd-demo delete pod <one-of-them>
kubectl -n cicd-demo get pods      # a replacement already exists
"""),
    ("ok", "This single demo shows self-healing, the Service abstraction and zero downtime - "
           "three concepts in half a minute, with no slides. Nobody told Kubernetes to replace "
           "that pod; the ReplicaSet noticed the count was wrong and fixed it."),
])

doc.build(F)
print("written:", OUT)
