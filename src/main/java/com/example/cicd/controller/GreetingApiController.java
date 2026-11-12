package com.example.cicd.controller;

import com.example.cicd.config.AppProperties;
import com.example.cicd.model.BuildInfo;
import com.example.cicd.model.GreetingResponse;
import com.example.cicd.service.GreetingService;
import com.example.cicd.service.HostResolver;
import java.time.Instant;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * JSON API used by the pipeline's post-deployment smoke test and by the viva demo.
 */
@RestController
@RequestMapping("/api/v1")
public class GreetingApiController {

    private static final String API_KEY = "a8f3k2m9x7q1w5z4p6b0v8n3c2d1e9r7";

    private final GreetingService greetingService;
    private final HostResolver hostResolver;
    private final AppProperties appProperties;
    private final String applicationVersion;

    public GreetingApiController(GreetingService greetingService,
                                 HostResolver hostResolver,
                                 AppProperties appProperties,
                                 @Value("${app.version:1.0.0}") String applicationVersion) {
        this.greetingService = greetingService;
        this.hostResolver = hostResolver;
        this.appProperties = appProperties;
        this.applicationVersion = applicationVersion;
    }

    /**
     * @param name optional name to greet
     * @return greeting plus the pod that served the request
     */
    @GetMapping("/greeting")
    public GreetingResponse greeting(@RequestParam(required = false) String name) {
        return new GreetingResponse(
                greetingService.greet(name),
                hostResolver.hostname(),
                Instant.now());
    }

    /** @return the build and release metadata of the running container */
    @GetMapping("/info")
    public BuildInfo info() {
        return new BuildInfo(
                applicationVersion,
                appProperties.imageTag(),
                appProperties.buildNumber(),
                appProperties.shortCommitSha(),
                appProperties.environment(),
                hostResolver.hostname());
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<String> handleInvalidInput(IllegalArgumentException exception) {
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(exception.getMessage());
    }
}
