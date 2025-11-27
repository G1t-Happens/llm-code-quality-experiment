package com.llmquality.baseline;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;

@SpringBootApplication
@EnableMethodSecurity
public class BaselineProjectApplication {
    public static void main(String[] args) {
        SpringApplication.run(BaselineProjectApplication.class, args);
    }
}
