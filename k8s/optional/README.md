# Optional manifests

These are **not** applied by the pipeline. `k8s/render.sh` only renders
`k8s/*.yaml`, so anything in this folder is deliberately out of the default
deploy set.

## 04-hpa.yaml - HorizontalPodAutoscaler

An HPA **takes ownership of the replica count**. Once one exists, it decides how
many pods run, and it will silently undo any manual change: scale the Deployment
to 4 by hand and the HPA will pull it back to its `minReplicas` within a few
minutes, because CPU is nowhere near the 70% target.

That is correct behaviour - it is the whole point of an autoscaler - but it
makes a manual scaling demonstration confusing, because the GUI or `kubectl`
appears to "not work".

It is kept here because it is still part of the design and shows how autoscaling
would be configured. Apply it only when you actually want autoscaling:

    kubectl apply -f k8s/optional/04-hpa.yaml

and remove it again when you want to control the replica count yourself:

    kubectl -n cicd-demo delete hpa cicd-demo-app
