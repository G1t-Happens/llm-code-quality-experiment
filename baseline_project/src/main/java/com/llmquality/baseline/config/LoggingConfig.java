package com.llmquality.baseline.config;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.encoder.PatternLayoutEncoder;
import ch.qos.logback.core.FileAppender;
import ch.qos.logback.core.rolling.TimeBasedRollingPolicy;
import ch.qos.logback.core.util.FileSize;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.io.File;


/**
 * Configuration class for setting up logging in the application.
 * It configures Logback with a file appender and a time-based rolling policy.
 * Logs will be stored in the "logs" directory under the application's working directory.
 * <p>
 * This configuration ensures logs are rotated daily, with a maximum of 30 days of history
 * and a total log size cap of 100MB.
 */
@Configuration
public class LoggingConfig {

    private static final org.slf4j.Logger LOG = LoggerFactory.getLogger(LoggingConfig.class);

    //Log Level - DEBUG, ERROR, INFO, WARN,...
    private static final Level LOG_LEVEL = Level.DEBUG;

    /**
     * Configures and returns a logger with file-based logging and rolling policies.
     *
     * @return Logger instance with custom logging configuration.
     */
    @Bean
    public Logger logger() {
        var loggerContext = (ch.qos.logback.classic.LoggerContext) LoggerFactory.getILoggerFactory();

        String logDirectoryPath = System.getProperty("user.dir") + File.separator + "logs";
        File logDirectory = new File(logDirectoryPath);
        if (!logDirectory.exists()) {
            boolean dirCreated = logDirectory.mkdirs();
            if (!dirCreated) {
                LOG.warn("Log directory could not be created: {}", logDirectoryPath);
            }
        }

        PatternLayoutEncoder encoder = new PatternLayoutEncoder();
        encoder.setContext(loggerContext);
        encoder.setPattern("%d{yyyy-MM-dd HH:mm:ss,UTC} - %msg%n");
        encoder.start();

        FileAppender<ch.qos.logback.classic.spi.ILoggingEvent> fileAppender = new FileAppender<>();
        fileAppender.setContext(loggerContext);
        fileAppender.setFile(logDirectoryPath + File.separator + "application.log");
        fileAppender.setEncoder(encoder);
        fileAppender.start();

        TimeBasedRollingPolicy<ch.qos.logback.classic.spi.ILoggingEvent> rollingPolicy = new TimeBasedRollingPolicy<>();
        rollingPolicy.setContext(loggerContext);
        rollingPolicy.setFileNamePattern(logDirectoryPath + File.separator + "application-%d{yyyy-MM-dd}.log");
        rollingPolicy.setMaxHistory(30);
        rollingPolicy.setTotalSizeCap(FileSize.valueOf("100MB"));
        rollingPolicy.setParent(fileAppender);
        rollingPolicy.start();

        Logger logger = (Logger) LoggerFactory.getLogger("com.llmquality.baseline");
        logger.addAppender(fileAppender);
        logger.setLevel(LOG_LEVEL);

        return logger;
    }
}