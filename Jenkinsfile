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
 *      6. Push to ACR    publish to Azure Container Registry
 *      7. Deploy to AKS  Ansible renders the manifests and rolls out
 *      8. Verify         rollout status + HTTP smoke test on the public IP
 *
 * Jenkins credentials required (Manage Jenkins > Credentials):
 *   azure-sp               Username/Password -> service principal appId / password
 *   azure-tenant-id        Secret text       -> Entra ID tenant id
 *   azure-subscription-id  Secret text       -> Azure subscription id
 *   sonarcloud-token       Secret text       -> SonarQube Cloud token
 */

pipeline {
    agent any

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
        K8S_NAMESPACE     = 'cicd-demo'

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
                    env.IMAGE_TAG  = "${env.BUILD_NUMBER}-${env.COMMIT_SHA}"
                    env.FULL_IMAGE = "${env.ACR_LOGIN_SERVER}/${env.IMAGE_NAME}:${env.IMAGE_TAG}"
                }
                sh 'chmod +x mvnw k8s/render.sh'
                echo "Build #${env.BUILD_NUMBER} | commit ${env.COMMIT_SHA} by ${env.GIT_AUTHOR} | image tag ${env.IMAGE_TAG}"
                echo "Commit message: ${env.COMMIT_MSG}"
            }
        }

        stage('2. Secret Scan (Gitleaks)') {
            steps {
                // Scans the whole repository history, so a credential that was committed
                // and later deleted is still caught. Any finding fails the build before
                // an image is ever published.
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
                        -t ${ACR_LOGIN_SERVER}/${IMAGE_NAME}:latest \
                        .
                    docker images ${ACR_LOGIN_SERVER}/${IMAGE_NAME}
                '''
            }
        }

        stage('6. Push to Azure Container Registry') {
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
                        docker push ${ACR_LOGIN_SERVER}/${IMAGE_NAME}:latest

                        echo "--- tags now in ${ACR_NAME} ---"
                        az acr repository show-tags --name ${ACR_NAME} \
                            --repository ${IMAGE_NAME} --orderby time_desc --top 5 --output table
                    '''
                }
            }
        }

        stage('7. Deploy to AKS') {
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

                        az aks get-credentials \
                            --resource-group ${AZ_RESOURCE_GROUP} \
                            --name ${AKS_CLUSTER} \
                            --admin --overwrite-existing

                        # Ansible performs the deployment: it renders the manifests with
                        # this build's image tag and applies them to the cluster.
                        ansible-playbook ansible/deploy-app.yml \
                            -i ansible/inventory.ini \
                            -e "image=${FULL_IMAGE}" \
                            -e "image_tag=${IMAGE_TAG}" \
                            -e "build_number=${BUILD_NUMBER}" \
                            -e "commit_sha=${COMMIT_SHA}" \
                            -e "k8s_namespace=${K8S_NAMESPACE}"
                    '''
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
                sh '''
                    set -e
                    echo "--- rollout status ---"
                    kubectl -n ${K8S_NAMESPACE} rollout status deployment/${APP_NAME} --timeout=300s

                    echo "--- cluster state ---"
                    kubectl -n ${K8S_NAMESPACE} get deployment,pods,svc -o wide

                    echo "--- waiting for the LoadBalancer public IP ---"
                    PUBLIC_IP=""
                    for i in $(seq 1 30); do
                        PUBLIC_IP=$(kubectl -n ${K8S_NAMESPACE} get svc ${APP_NAME} \
                            -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)
                        if [ -n "$PUBLIC_IP" ]; then break; fi
                        sleep 10
                    done
                    if [ -z "$PUBLIC_IP" ]; then
                        echo "LoadBalancer IP was not assigned in time"
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
            }
        }
    }

    post {
        success {
            echo "Pipeline succeeded. Image ${env.FULL_IMAGE} is running on AKS."
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
