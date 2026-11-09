package com.example.cicd.controller;

import com.example.cicd.config.AppProperties;
import com.example.cicd.model.BuildInfo;
import com.example.cicd.service.GreetingService;
import com.example.cicd.service.HostResolver;
import java.time.LocalTime;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

/**
 * Serves the HTML landing page that is opened in a browser to prove the
 * deployment on Azure Kubernetes Service is reachable.
 */
@Controller
public class HomeController {

    private final GreetingService greetingService;
    private final HostResolver hostResolver;
    private final AppProperties appProperties;
    private final String applicationVersion;

    public HomeController(GreetingService greetingService,
                          HostResolver hostResolver,
                          AppProperties appProperties,
                          @Value("${app.version:1.0.0}") String applicationVersion) {
        this.greetingService = greetingService;
        this.hostResolver = hostResolver;
        this.appProperties = appProperties;
        this.applicationVersion = applicationVersion;
    }

    @GetMapping("/")
    public String index(Model model) {
        BuildInfo buildInfo = new BuildInfo(
                applicationVersion,
                appProperties.imageTag(),
                appProperties.buildNumber(),
                appProperties.shortCommitSha(),
                appProperties.environment(),
                hostResolver.hostname());

        model.addAttribute("greeting", greetingService.timeOfDayGreeting(LocalTime.now()));
        model.addAttribute("releaseMessage", appProperties.releaseMessage());
        model.addAttribute("buildInfo", buildInfo);
        return "index";
    }
}
