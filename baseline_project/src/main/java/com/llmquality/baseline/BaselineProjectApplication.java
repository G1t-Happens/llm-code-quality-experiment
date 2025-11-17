package com.llmquality.baseline;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;


@EnableJpaAuditing
@SpringBootApplication
public class BaselineProjectApplication {
    public static void main(String[] args) {
        SpringApplication.run(BaselineProjectApplication.class, args);
    }
}
