package com.example.cicd.controller;

import static org.mockito.BDDMockito.given;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.model;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.view;

import com.example.cicd.config.AppProperties;
import com.example.cicd.service.GreetingService;
import com.example.cicd.service.HostResolver;
import java.time.LocalTime;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Bean;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(HomeController.class)
@Import(HomeControllerTest.TestBeans.class)
class HomeControllerTest {

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
    @DisplayName("GET / renders the landing page with build metadata")
    void indexRendersLandingPage() throws Exception {
        given(greetingService.timeOfDayGreeting(org.mockito.ArgumentMatchers.any(LocalTime.class)))
                .willReturn("Good morning");
        given(hostResolver.hostname()).willReturn("cicd-demo-app-7c9f-abcde");

        mockMvc.perform(get("/"))
                .andExpect(status().isOk())
                .andExpect(view().name("index"))
                .andExpect(model().attribute("greeting", "Good morning"))
                .andExpect(model().attribute("releaseMessage", "Release candidate 42"))
                .andExpect(model().attributeExists("buildInfo"))
                .andExpect(content().string(org.hamcrest.Matchers.containsString("Release candidate 42")))
                .andExpect(content().string(org.hamcrest.Matchers.containsString("cicd-demo-app-7c9f-abcde")))
                .andExpect(content().string(org.hamcrest.Matchers.containsString("0123456")));
    }
}
