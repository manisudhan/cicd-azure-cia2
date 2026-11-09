package com.example.cicd.model;

import java.time.Instant;

/**
 * JSON payload returned by the greeting REST endpoint.
 *
 * @param message   greeting text
 * @param servedBy  hostname of the container that answered, i.e. the Kubernetes pod name
 * @param timestamp moment the response was produced, in UTC
 */
public record GreetingResponse(String message, String servedBy, Instant timestamp) {
}
