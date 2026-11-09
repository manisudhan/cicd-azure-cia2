package com.example.cicd;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.ApplicationContext;

/**
 * Smoke test: fails the pipeline early if the Spring context cannot start,
 * for example after a bad configuration change.
 */
@SpringBootTest
class CicdDemoApplicationTests {

    @Autowired
    private ApplicationContext context;

    @Test
    @DisplayName("Spring application context starts successfully")
    void contextLoads() {
        assertThat(context).isNotNull();
        assertThat(context.containsBean("greetingService")).isTrue();
    }
}
