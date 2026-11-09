package com.example.cicd;

import com.example.cicd.config.AppProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

/**
 * Entry point of the demo Java web application.
 *
 * <p>The application is intentionally small: its purpose is to be built, tested,
 * containerised and deployed by the CI/CD pipeline defined in the {@code Jenkinsfile},
 * and to make a code change visible in a browser once the pipeline has run.</p>
 */
@SpringBootApplication
@EnableConfigurationProperties(AppProperties.class)
public class CicdDemoApplication {

    public static void main(String[] args) {
        SpringApplication.run(CicdDemoApplication.class, args);
    }
}
