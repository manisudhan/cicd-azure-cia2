package com.example.cicd.controller;

import static org.mockito.BDDMockito.given;
import static org.mockito.BDDMockito.willThrow;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.example.cicd.config.AppProperties;
import com.example.cicd.service.GreetingService;
import com.example.cicd.service.HostResolver;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(GreetingApiController.class)
@Import(GreetingApiControllerTest.TestBeans.class)
class GreetingApiControllerTest {

    @TestConfiguration
    static class TestBeans {
        @Bean
        AppProperties appProperties() {
            return new AppProperties(
                    "Release candidate 42", "build-42", "42", "0123456789abcdef", "production");
        }
    }

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private GreetingService greetingService;

    @MockitoBean
    private HostResolver hostResolver;

    @Test
    @DisplayName("GET /api/v1/greeting returns the greeting and the serving pod")
    void greetingReturnsJson() throws Exception {
        given(greetingService.greet("devops")).willReturn("Hello, Devops!");
        given(hostResolver.hostname()).willReturn("cicd-demo-app-7c9f-abcde");

        mockMvc.perform(get("/api/v1/greeting").param("name", "devops"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.message").value("Hello, Devops!"))
                .andExpect(jsonPath("$.servedBy").value("cicd-demo-app-7c9f-abcde"))
                .andExpect(jsonPath("$.timestamp").exists());
    }

    @Test
    @DisplayName("GET /api/v1/greeting works without a name parameter")
    void greetingWorksWithoutName() throws Exception {
        given(greetingService.greet(null)).willReturn("Hello, World!");
        given(hostResolver.hostname()).willReturn("pod-1");

        mockMvc.perform(get("/api/v1/greeting"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.message").value("Hello, World!"));
    }

    @Test
    @DisplayName("GET /api/v1/greeting returns 400 for invalid input")
    void greetingRejectsInvalidInput() throws Exception {
        willThrow(new IllegalArgumentException("name must be at most 40 characters"))
                .given(greetingService).greet("x".repeat(41));

        mockMvc.perform(get("/api/v1/greeting").param("name", "x".repeat(41)))
                .andExpect(status().isBadRequest());
    }

    @Test
    @DisplayName("GET /api/v1/info exposes the deployed build metadata")
    void infoReturnsBuildMetadata() throws Exception {
        given(hostResolver.hostname()).willReturn("pod-2");

        mockMvc.perform(get("/api/v1/info"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.imageTag").value("build-42"))
                .andExpect(jsonPath("$.buildNumber").value("42"))
                .andExpect(jsonPath("$.commitSha").value("0123456"))
                .andExpect(jsonPath("$.environment").value("production"))
                .andExpect(jsonPath("$.servedBy").value("pod-2"));
    }
}
