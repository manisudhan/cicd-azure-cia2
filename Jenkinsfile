#!/usr/bin/env groovy

/*
 * End-to-end CI/CD pipeline for the Java web application.
 *
 *  GitHub push  ->  Jenkins (local, in Docker - see docker-compose.yml)
 *      1. Checkout       source code + git metadata
 *      2. Secret Scan    Gitleaks over the full git history      (security gate)
 *      3. Build & Test   Maven compile, unit tests, JaCoCo coverage
 *      4. Code Quality   SonarQube Cloud analysis + Quality Gate (quality gate)
 *      5. Docker Build   build and tag the container image
 *      6. Publish        push to Azure Container Registry (azure target only)
 *      7. Deploy         Ansible renders the manifests and rolls out
 *      8. Verify         rollout status + HTTP smoke test on the live endpoint
 *
 * DEPLOY_TARGET selects where stages 6-8 act:
 *
 *   local  - deploys to Docker Desktop's built-in Kubernetes. No Azure account
 *            needed. Docker Desktop's Kubernetes shares the Docker image store,
 *            so the image built in stage 5 is already available to the cluster
 *            (the Deployment uses imagePullPolicy: IfNotPresent) and stage 6 is
 *            skipped. Run infra/local-connect.sh once first.
 *
 *   azure  - pushes to Azure Container Registry and deploys to Azure Kubernetes
 *            Service. Needs the four credentials below.
 *
 * Jenkins credentials (Manage Jenkins > Credentials), azure target only:
 *   azure-sp               Username/Password -> service principal appId / password
 *   azure-tenant-id        Secret text       -> Entra ID tenant id
 *   azure-subscription-id  Secret text       -> Azure subscription id
 * Needed by both targets when RUN_SONAR is ticked:
 *   sonarcloud-token       Secret text       -> SonarQube Cloud token
 */

pipeline {
    agent any

    parameters {
        choice(
            name: 'DEPLOY_TARGET',
            choices: ['local', 'azure'],
            description: 'local = Docker Desktop Kubernetes (no Azure account needed). ' +
                         'azure = push to ACR and deploy to AKS.'
        )
        booleanParam(
            name: 'RUN_SONAR',
            defaultValue: true,
            description: 'Run the SonarQube Cloud analysis and wait for the Quality Gate. ' +
                         'Untick only to prove the rest of the pipeline before SonarCloud is configured.'
        )
    }

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    triggers {
        // Jenkins runs on localhost, which GitHub cannot reach directly, so SCM
        // polling is the primary automatic trigger: a push is picked up within
        // about two minutes with no manual action and no inbound network access.
        pollSCM('H/2 * * * *')
        // Also honour a real webhook if localhost is exposed through a tunnel
        // (see docs/SETUP.md step 6); harmless when no tunnel is running.
        githubPush()
    }

    environment {
        // ---- Azure resources (must match infra/azure-setup.sh) ----
        AZ_RESOURCE_GROUP = 'rg-cicd-cia2'
        ACR_NAME          = 'acrcicdcia2'
        ACR_LOGIN_SERVER  = 'acrcicdcia2.azurecr.io'
        AKS_CLUSTER       = 'aks-cicd-cia2'

        // ---- Kubernetes ----
        K8S_NAMESPACE     = 'cicd-demo'
        LOCAL_KUBE_CONTEXT = 'docker-desktop'

        // ---- Application / image ----
        IMAGE_NAME = 'cicd-demo-app'
        APP_NAME   = 'cicd-demo-app'

        // ---- SonarQube Cloud ----
        SONAR_HOST_URL    = 'https://sonarcloud.io'
        SONAR_ORG         = 'CHANGE-ME-ORG'
        SONAR_PROJECT_KEY = 'CHANGE-ME-ORG_cicd-demo-app'

        // Maven runs through the wrapper, so the agent needs no Maven installation.
        MAVEN      = './mvnw'
        MAVEN_OPTS = '-Xmx1024m'
    }

    stages {

        stage('1. Checkout') {
            steps {
                checkout scm
                script {
                    env.COMMIT_SHA = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                    env.COMMIT_MSG = sh(script: 'git log -1 --pretty=%s', returnStdout: true).trim()
                    env.GIT_AUTHOR = sh(script: 'git log -1 --pretty=%an', returnStdout: true).trim()

                    // Every image is tagged with the build number AND the commit it came
                    // from, so a running pod can always be traced back to source.
                    env.IMAGE_TAG = "${env.BUILD_NUMBER}-${env.COMMIT_SHA}"

                    // The local target has no registry: Docker Desktop's Kubernetes reads
                    // the same image store the build writes to, so the image needs no
                    // registry prefix.
                    env.FULL_IMAGE = (params.DEPLOY_TARGET == 'azure')
                            ? "${env.ACR_LOGIN_SERVER}/${env.IMAGE_NAME}:${env.IMAGE_TAG}"
                            : "${env.IMAGE_NAME}:${env.IMAGE_TAG}"
                    env.LATEST_IMAGE = (params.DEPLOY_TARGET == 'azure')
                            ? "${env.ACR_LOGIN_SERVER}/${env.IMAGE_NAME}:latest"
                            : "${env.IMAGE_NAME}:latest"
                }
                sh 'chmod +x mvnw k8s/render.sh'
                echo "Target: ${params.DEPLOY_TARGET} | build #${env.BUILD_NUMBER} | commit ${env.COMMIT_SHA} by ${env.GIT_AUTHOR}"
                echo "Image : ${env.FULL_IMAGE}"
                echo "Commit message: ${env.COMMIT_MSG}"
            }
        }

        stage('2. Secret Scan (Gitleaks)') {
            steps {
                // Scans the whole repository history, so a credential that was committed
                // and later deleted is still caught. Any finding fails the build before
                // an image is ever built or published.
                sh '''
                    set -e
                    gitleaks git . \
                        --config .gitleaks.toml \
                        --redact \
                        --report-format sarif \
                        --report-path gitleaks-report.sarif \
                        --exit-code 1 \
                        --verbose
                    echo "Gitleaks: no secrets detected in git history."
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'gitleaks-report.sarif',
                                     allowEmptyArchive: true, fingerprint: true
                }
            }
        }

        stage('3. Build & Unit Test (Maven)') {
            steps {
                // "verify" runs compile -> unit tests -> package -> JaCoCo report.
                sh '${MAVEN} -B -ntp clean verify'
            }
            post {
                always {
                    junit testResults: 'target/surefire-reports/*.xml', allowEmptyResults: false
                    archiveArtifacts artifacts: 'target/*.jar, target/site/jacoco/**',
                                     allowEmptyArchive: true, fingerprint: true
                }
            }
        }

        stage('4. Code Quality (SonarQube Cloud)') {
            when { expression { return params.RUN_SONAR } }
            steps {
                withCredentials([string(credentialsId: 'sonarcloud-token', variable: 'SONAR_TOKEN')]) {
                    // -Dsonar.qualitygate.wait=true blocks until SonarQube Cloud has
                    // computed the Quality Gate, so a failing gate fails the build.
                    sh '''
                        ${MAVEN} -B -ntp sonar:sonar \
                            -Dsonar.host.url=${SONAR_HOST_URL} \
                            -Dsonar.organization=${SONAR_ORG} \
                            -Dsonar.projectKey=${SONAR_PROJECT_KEY} \
                            -Dsonar.token=${SONAR_TOKEN} \
                            -Dsonar.qualitygate.wait=true \
                            -Dsonar.qualitygate.timeout=300
                    '''
                }
            }
        }

        stage('5. Docker Build & Tag') {
            steps {
                sh '''
                    set -e
                    docker build \
                        --build-arg IMAGE_TAG=${IMAGE_TAG} \
                        --build-arg COMMIT_SHA=${COMMIT_SHA} \
                        --build-arg BUILD_NUMBER=${BUILD_NUMBER} \
                        -t ${FULL_IMAGE} \
                        -t ${LATEST_IMAGE} \
                        .
                    docker image inspect ${FULL_IMAGE} \
                        --format 'Built {{.RepoTags}} ({{.Size}} bytes)'
                '''
            }
        }

        stage('6. Push to Azure Container Registry') {
            when { expression { return params.DEPLOY_TARGET == 'azure' } }
            steps {
                withCredentials([
                    usernamePassword(credentialsId: 'azure-sp',
                                     usernameVariable: 'AZ_CLIENT_ID',
                                     passwordVariable: 'AZ_CLIENT_SECRET'),
                    string(credentialsId: 'azure-tenant-id',       variable: 'AZ_TENANT_ID'),
                    string(credentialsId: 'azure-subscription-id', variable: 'AZ_SUBSCRIPTION_ID')
                ]) {
                    sh '''
                        set -e
                        az login --service-principal \
                            --username "$AZ_CLIENT_ID" \
                            --password "$AZ_CLIENT_SECRET" \
                            --tenant   "$AZ_TENANT_ID" > /dev/null
                        az account set --subscription "$AZ_SUBSCRIPTION_ID"

                        az acr login --name ${ACR_NAME}
                        docker push ${FULL_IMAGE}
                        docker push ${LATEST_IMAGE}

                        echo "--- tags now in ${ACR_NAME} ---"
                        az acr repository show-tags --name ${ACR_NAME} \
                            --repository ${IMAGE_NAME} --orderby time_desc --top 5 --output table
                    '''
                }
            }
        }

        stage('7. Deploy to Kubernetes') {
            steps {
                script {
                    if (params.DEPLOY_TARGET == 'azure') {
                        withCredentials([
                            usernamePassword(credentialsId: 'azure-sp',
                                             usernameVariable: 'AZ_CLIENT_ID',
                                             passwordVariable: 'AZ_CLIENT_SECRET'),
                            string(credentialsId: 'azure-tenant-id',       variable: 'AZ_TENANT_ID'),
                            string(credentialsId: 'azure-subscription-id', variable: 'AZ_SUBSCRIPTION_ID')
                        ]) {
                            sh '''
                                set -e
                                az login --service-principal \
                                    --username "$AZ_CLIENT_ID" \
                                    --password "$AZ_CLIENT_SECRET" \
                                    --tenant   "$AZ_TENANT_ID" > /dev/null
                                az account set --subscription "$AZ_SUBSCRIPTION_ID"

                                az aks get-credentials \
                                    --resource-group ${AZ_RESOURCE_GROUP} \
                                    --name ${AKS_CLUSTER} \
                                    --admin --overwrite-existing

                                ansible-playbook ansible/deploy-app.yml \
                                    -i ansible/inventory.ini \
                                    -e "deploy_target=azure" \
                                    -e "image=${FULL_IMAGE}" \
                                    -e "image_tag=${IMAGE_TAG}" \
                                    -e "build_number=${BUILD_NUMBER}" \
                                    -e "commit_sha=${COMMIT_SHA}" \
                                    -e "k8s_namespace=${K8S_NAMESPACE}"
                            '''
                        }
                    } else {
                        // The kubeconfig for Docker Desktop's cluster was installed into
                        // the container's $KUBECONFIG by infra/local-connect.sh.
                        sh '''
                            set -e
                            kubectl config use-context ${LOCAL_KUBE_CONTEXT}
                            kubectl cluster-info

                            ansible-playbook ansible/deploy-app.yml \
                                -i ansible/inventory.ini \
                                -e "deploy_target=local" \
                                -e "image=${FULL_IMAGE}" \
                                -e "image_tag=${IMAGE_TAG}" \
                                -e "build_number=${BUILD_NUMBER}" \
                                -e "commit_sha=${COMMIT_SHA}" \
                                -e "k8s_namespace=${K8S_NAMESPACE}"
                        '''
                    }
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'k8s/rendered/*.yaml', allowEmptyArchive: true
                }
            }
        }

        stage('8. Verify Deployment') {
            steps {
                // Common to both targets: the rollout only completes once new pods have
                // passed their readiness probe, which is already proof of health.
                sh '''
                    set -e
                    echo "--- rollout status ---"
                    kubectl -n ${K8S_NAMESPACE} rollout status deployment/${APP_NAME} --timeout=300s

                    echo "--- cluster state ---"
                    kubectl -n ${K8S_NAMESPACE} get deployment,pods,svc -o wide
                '''
                script {
                    if (params.DEPLOY_TARGET == 'azure') {
                        sh '''
                            set -e
                            echo "--- waiting for the Azure Load Balancer public IP ---"
                            PUBLIC_IP=""
                            for i in $(seq 1 30); do
                                PUBLIC_IP=$(kubectl -n ${K8S_NAMESPACE} get svc ${APP_NAME} \
                                    -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)
                                if [ -n "$PUBLIC_IP" ]; then break; fi
                                sleep 10
                            done
                            if [ -z "$PUBLIC_IP" ]; then
                                echo "No LoadBalancer IP was assigned in time"
                                exit 1
                            fi

                            echo "--- smoke test against http://$PUBLIC_IP ---"
                            curl -fsS --retry 10 --retry-delay 6 --retry-connrefused \
                                 "http://$PUBLIC_IP/actuator/health"
                            echo
                            DEPLOYED=$(curl -fsS "http://$PUBLIC_IP/api/v1/info")
                            echo "$DEPLOYED"

                            # Fail the build if the live endpoint is not serving THIS build.
                            if ! echo "$DEPLOYED" | grep -q "${IMAGE_TAG}"; then
                                echo "Deployed build does not report image tag ${IMAGE_TAG}"
                                exit 1
                            fi

                            echo "SUCCESS - build ${BUILD_NUMBER} is live at http://$PUBLIC_IP"
                        '''
                    } else {
                        sh '''
                            set -e
                            # Docker Desktop's kind-based Kubernetes has no working
                            # LoadBalancer controller (cloud-provider-kind cannot start its
                            # envoy container), so the Service EXTERNAL-IP stays <pending>.
                            # The smoke test therefore runs INSIDE the cluster against the
                            # Service's DNS name, which still proves that the Service routes
                            # traffic to a ready pod serving this exact build. The manifest
                            # keeps type: LoadBalancer because that is what AKS needs.
                            echo "--- in-cluster smoke test via the Service DNS name ---"
                            DEPLOYED=$(kubectl -n ${K8S_NAMESPACE} run smoke-${BUILD_NUMBER} \
                                --rm -i --restart=Never --timeout=180s \
                                --image=curlimages/curl:8.11.1 -- \
                                curl -fsS --max-time 15 --retry 5 --retry-delay 3 \
                                "http://${APP_NAME}.${K8S_NAMESPACE}.svc.cluster.local/api/v1/info")
                            echo "$DEPLOYED"

                            # Fail the build if the Service is not serving THIS build.
                            if ! echo "$DEPLOYED" | grep -q "${IMAGE_TAG}"; then
                                echo "Deployed build does not report image tag ${IMAGE_TAG}"
                                exit 1
                            fi

                            echo "SUCCESS - build ${BUILD_NUMBER} is serving inside the cluster."
                            echo "To open it in a browser, run on the host:"
                            echo "  kubectl port-forward -n ${K8S_NAMESPACE} svc/${APP_NAME} 8081:80"
                            echo "then browse http://localhost:8081"
                        '''
                    }
                }
            }
        }
    }

    post {
        success {
            echo "Pipeline succeeded. Image ${env.FULL_IMAGE} is running on the ${params.DEPLOY_TARGET} cluster."
        }
        failure {
            echo 'Pipeline failed. Collecting Kubernetes diagnostics.'
            sh '''
                kubectl -n ${K8S_NAMESPACE} get pods 2>/dev/null || true
                kubectl -n ${K8S_NAMESPACE} describe deployment/${APP_NAME} 2>/dev/null | tail -40 || true
            '''
        }
        always {
            sh 'az logout 2>/dev/null || true'
        }
    }
}
