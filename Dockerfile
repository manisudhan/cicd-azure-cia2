# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 - build
# The image is self-contained: anyone can run "docker build ." without having
# Maven or a JDK installed. Dependencies are resolved in their own layer so
# that a source-only change does not re-download the whole repository.
# Tests are skipped here because the Jenkins pipeline already ran them in a
# dedicated stage, where it can publish the JUnit and JaCoCo reports.
# ---------------------------------------------------------------------------
FROM maven:3.9.9-eclipse-temurin-21 AS builder
WORKDIR /build

COPY pom.xml ./
RUN mvn -B -ntp dependency:go-offline

COPY src ./src
RUN mvn -B -ntp clean package -DskipTests

# ---------------------------------------------------------------------------
# Stage 2 - runtime
# A JRE-only Alpine base keeps the published image small (~190 MB instead of
# ~600 MB) and reduces the number of packages that can carry a CVE.
# ---------------------------------------------------------------------------
FROM eclipse-temurin:21-jre-alpine AS runtime

ARG IMAGE_TAG=local
ARG COMMIT_SHA=local
ARG BUILD_NUMBER=local

LABEL org.opencontainers.image.title="cicd-demo-app" \
      org.opencontainers.image.description="Java web application deployed by an Azure CI/CD pipeline" \
      org.opencontainers.image.version="${IMAGE_TAG}" \
      org.opencontainers.image.revision="${COMMIT_SHA}" \
      org.opencontainers.image.vendor="CIA-2 DevOps Assignment"

# Run as an unprivileged user: the Kubernetes securityContext also enforces this.
RUN addgroup -S -g 10001 appgroup \
 && adduser  -S -u 10001 -G appgroup -h /app appuser
WORKDIR /app

COPY --from=builder --chown=10001:10001 /build/target/cicd-demo-app.jar /app/app.jar

ENV APP_IMAGE_TAG=${IMAGE_TAG} \
    APP_COMMIT_SHA=${COMMIT_SHA} \
    APP_BUILD_NUMBER=${BUILD_NUMBER} \
    JAVA_OPTS="-XX:MaxRAMPercentage=75.0 -XX:+ExitOnOutOfMemoryError"

USER 10001:10001
EXPOSE 8080

# Useful for a local "docker run"; in Kubernetes the probes in deployment.yaml take over.
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:8080/actuator/health || exit 1

ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar /app/app.jar"]
