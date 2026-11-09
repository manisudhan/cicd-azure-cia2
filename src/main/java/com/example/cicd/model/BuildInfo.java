package com.example.cicd.model;

/**
 * Build and release metadata surfaced on the landing page and the {@code /api/v1/info}
 * endpoint. The pipeline injects these values so it is obvious which build is live.
 *
 * @param applicationVersion Maven project version
 * @param imageTag           container image tag deployed by the pipeline
 * @param buildNumber        Jenkins build number
 * @param commitSha          short Git commit SHA
 * @param environment        logical environment name
 * @param servedBy           pod or host name serving the request
 */
public record BuildInfo(
        String applicationVersion,
        String imageTag,
        String buildNumber,
        String commitSha,
        String environment,
        String servedBy) {
}
