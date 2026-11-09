package com.example.cicd.config;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

class AppPropertiesTest {

    @Test
    @DisplayName("blank values fall back to sensible local defaults")
    void blankValuesFallBackToDefaults() {
        AppProperties properties = new AppProperties(" ", null, "", "   ", null);

        assertThat(properties.releaseMessage())
                .isEqualTo("Deployed to Azure Kubernetes Service by Jenkins");
        assertThat(properties.imageTag()).isEqualTo("local");
        assertThat(properties.buildNumber()).isEqualTo("local");
        assertThat(properties.commitSha()).isEqualTo("local");
        assertThat(properties.environment()).isEqualTo("local");
    }

    @Test
    @DisplayName("supplied values are preserved")
    void suppliedValuesArePreserved() {
        AppProperties properties =
                new AppProperties("Release 7", "build-7", "7", "abcdef1234567", "production");

        assertThat(properties.releaseMessage()).isEqualTo("Release 7");
        assertThat(properties.imageTag()).isEqualTo("build-7");
        assertThat(properties.buildNumber()).isEqualTo("7");
        assertThat(properties.environment()).isEqualTo("production");
    }

    @Test
    @DisplayName("shortCommitSha() truncates a full SHA to seven characters")
    void shortCommitShaTruncatesLongSha() {
        AppProperties properties =
                new AppProperties("m", "t", "1", "0123456789abcdef", "dev");

        assertThat(properties.shortCommitSha()).isEqualTo("0123456");
    }

    @Test
    @DisplayName("shortCommitSha() leaves a short SHA untouched")
    void shortCommitShaKeepsShortValue() {
        AppProperties properties = new AppProperties("m", "t", "1", "abc123", "dev");

        assertThat(properties.shortCommitSha()).isEqualTo("abc123");
    }
}
