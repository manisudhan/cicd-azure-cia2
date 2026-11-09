package com.example.cicd.service;

import java.net.InetAddress;
import java.net.UnknownHostException;
import org.springframework.stereotype.Component;

/**
 * Resolves the name of the machine serving a request.
 *
 * <p>Inside Kubernetes the container hostname equals the pod name, which makes it easy
 * to show in the browser that several replicas are load-balanced behind one Service.</p>
 */
@Component
public class HostResolver {

    private static final String FALLBACK = "unknown-host";

    /** @return the pod or host name, or {@code unknown-host} if it cannot be resolved */
    public String hostname() {
        String fromEnv = System.getenv("HOSTNAME");
        if (fromEnv != null && !fromEnv.isBlank()) {
            return fromEnv;
        }
        try {
            return InetAddress.getLocalHost().getHostName();
        } catch (UnknownHostException e) {
            return FALLBACK;
        }
    }
}
