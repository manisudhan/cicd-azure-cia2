package com.example.cicd.service;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

class HostResolverTest {

    private final HostResolver resolver = new HostResolver();

    @Test
    @DisplayName("hostname() always returns a non-blank identifier")
    void hostnameIsNeverBlank() {
        assertThat(resolver.hostname()).isNotBlank();
    }
}
