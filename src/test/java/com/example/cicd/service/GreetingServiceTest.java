package com.example.cicd.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.LocalTime;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

class GreetingServiceTest {

    private final GreetingService service = new GreetingService();

    @Test
    @DisplayName("greet() capitalises the supplied name")
    void greetCapitalisesName() {
        assertThat(service.greet("sanjay")).isEqualTo("Hello, Sanjay!");
    }

    @Test
    @DisplayName("greet() trims surrounding whitespace")
    void greetTrimsWhitespace() {
        assertThat(service.greet("   devops   ")).isEqualTo("Hello, Devops!");
    }

    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {"   ", "\t"})
    @DisplayName("greet() falls back to World for missing input")
    void greetFallsBackToWorld(String input) {
        assertThat(service.greet(input)).isEqualTo("Hello, World!");
    }

    @Test
    @DisplayName("greet() rejects names longer than 40 characters")
    void greetRejectsOverlyLongName() {
        String tooLong = "a".repeat(41);
        assertThatThrownBy(() -> service.greet(tooLong))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("at most 40 characters");
    }

    @ParameterizedTest
    @CsvSource({
            "00:30, Good night",
            "04:59, Good night",
            "05:00, Good morning",
            "11:59, Good morning",
            "12:00, Good afternoon",
            "16:59, Good afternoon",
            "17:00, Good evening",
            "20:59, Good evening",
            "21:00, Good night",
            "23:59, Good night"
    })
    @DisplayName("timeOfDayGreeting() maps each part of the day correctly")
    void timeOfDayGreetingCoversAllBranches(String time, String expected) {
        assertThat(service.timeOfDayGreeting(LocalTime.parse(time))).isEqualTo(expected);
    }

    @Test
    @DisplayName("timeOfDayGreeting() rejects a null time")
    void timeOfDayGreetingRejectsNull() {
        assertThatThrownBy(() -> service.timeOfDayGreeting(null))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("time must not be null");
    }
}
