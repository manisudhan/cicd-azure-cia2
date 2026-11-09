package com.example.cicd.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Externalised application settings.
 *
 * <p>Every value can be overridden by an environment variable, which is how the
 * Kubernetes {@code ConfigMap} injects build and release metadata into the running
 * container (for example {@code APP_RELEASE_MESSAGE} or {@code APP_IMAGE_TAG}).</p>
 *
 * @param releaseMessage headline shown on the landing page; change this to prove a
 *                       code change travelled through the pipeline
 * @param imageTag       tag of the container image the pipeline deployed
 * @param buildNumber    Jenkins build number that produced the image
 * @param commitSha      Git commit the image was built from
 * @param environment    logical environment name, e.g. {@code dev} or {@code production}
 */
@ConfigurationProperties(prefix = "app")
public record AppProperties(
        String releaseMessage,
        String imageTag,
        String buildNumber,
        String commitSha,
        String environment) {

    private static final String UNKNOWN = "local";

    public AppProperties {
        releaseMessage = blankToDefault(releaseMessage, "Deployed to Azure Kubernetes Service by Jenkins");
        imageTag = blankToDefault(imageTag, UNKNOWN);
        buildNumber = blankToDefault(buildNumber, UNKNOWN);
        commitSha = blankToDefault(commitSha, UNKNOWN);
        environment = blankToDefault(environment, UNKNOWN);
    }

    private static String blankToDefault(String value, String fallback) {
        return (value == null || value.isBlank()) ? fallback : value;
    }

    /** @return the commit SHA shortened to the 7 characters normally shown by Git */
    public String shortCommitSha() {
        return commitSha.length() > 7 ? commitSha.substring(0, 7) : commitSha;
    }
}
