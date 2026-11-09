package com.example.cicd.service;

import java.time.LocalTime;
import org.springframework.stereotype.Service;

/**
 * Small piece of business logic so the pipeline has real code to compile,
 * unit-test, measure coverage on and analyse with SonarQube Cloud.
 */
@Service
public class GreetingService {

    private static final String DEFAULT_NAME = "World";
    private static final int MAX_NAME_LENGTH = 40;

    /**
     * Builds a greeting for the supplied name.
     *
     * @param name name to greet; may be {@code null} or blank
     * @return greeting such as {@code "Hello, Sanjay!"}
     * @throws IllegalArgumentException if the name is longer than 40 characters
     */
    public String greet(String name) {
        String cleaned = normalise(name);
        return "Hello, " + cleaned + "!";
    }

    /**
     * Returns a greeting appropriate to the time of day.
     *
     * @param time time to classify, must not be {@code null}
     * @return one of {@code Good morning}, {@code Good afternoon},
     *         {@code Good evening} or {@code Good night}
     */
    public String timeOfDayGreeting(LocalTime time) {
        if (time == null) {
            throw new IllegalArgumentException("time must not be null");
        }
        int hour = time.getHour();
        if (hour < 5) {
            return "Good night";
        }
        if (hour < 12) {
            return "Good morning";
        }
        if (hour < 17) {
            return "Good afternoon";
        }
        if (hour < 21) {
            return "Good evening";
        }
        return "Good night";
    }

    private String normalise(String name) {
        if (name == null || name.isBlank()) {
            return DEFAULT_NAME;
        }
        String trimmed = name.strip();
        if (trimmed.length() > MAX_NAME_LENGTH) {
            throw new IllegalArgumentException(
                    "name must be at most " + MAX_NAME_LENGTH + " characters");
        }
        return Character.toUpperCase(trimmed.charAt(0)) + trimmed.substring(1);
    }
}
