package com.llmquality.baseline.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;


/**
 * Configuration class for password encoding.
 * <p>
 * Provides a {@link PasswordEncoder} bean configured to use BCrypt hashing algorithm
 * for securely encoding passwords.
 * </p>
 */
@Configuration
public class EncryptionConfig {

    /**
     * Bean for {@link PasswordEncoder} using BCrypt hashing algorithm.
     *
     * @return a {@link PasswordEncoder} instance
     */
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
