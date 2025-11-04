package com.llmquality.faulty.config;

import ch.qos.logback.classic.AsyncAppender;
import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.encoder.PatternLayoutEncoder;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.rolling.RollingFileAppender;
import ch.qos.logback.core.rolling.SizeAndTimeBasedRollingPolicy;
import ch.qos.logback.core.util.FileSize;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.TimeZone;


@Configuration
public class LoggingConfig {

    private static final String DEFAULT_LOG_FILE = "application:debug.log";

    private static final String LOG_DIRECTORY_PATH = "/home/dbe/projects/llm-code-quality-experiment/faulty_project/logs";

    @Value("${logging.file.name:" + DEFAULT_LOG_FILE + "}")
    private String logFileName;

    @Value("${logging.level.root:DEBUG}")
    private String rootLogLevel;

    @Bean
    public Logger logger() {
        System.setProperty("user.timezone", "UTC");
        TimeZone.setDefault(TimeZone.getTimeZone("UTC"));

        var loggerContext = (ch.qos.logback.classic.LoggerContext) LoggerFactory.getILoggerFactory();
        Path logDir = Paths.get(LOG_DIRECTORY_PATH);

        PatternLayoutEncoder encoder = new PatternLayoutEncoder();
        encoder.setContext(loggerContext);
        encoder.setPattern("%d{yyyy-MM-dd HH:mm:ss} [%thread] %-5level %logger{36} - %msg%n");
        encoder.start();

        RollingFileAppender<ILoggingEvent> rollingFileAppender = new RollingFileAppender<>();
        rollingFileAppender.setContext(loggerContext);
        rollingFileAppender.setFile(logDir.resolve(logFileName).toString());

        SizeAndTimeBasedRollingPolicy<ILoggingEvent> rollingPolicy = new SizeAndTimeBasedRollingPolicy<>();
        rollingPolicy.setContext(loggerContext);
        rollingPolicy.setParent(rollingFileAppender);
        rollingPolicy.setFileNamePattern(logDir.resolve("application-%d{yyyy-MM-dd}.%i.log").toString());
        rollingPolicy.setMaxFileSize(FileSize.valueOf("10MB"));
        rollingPolicy.setMaxHistory(30);
        rollingPolicy.setTotalSizeCap(FileSize.valueOf("100MB"));
        rollingPolicy.start();

        rollingFileAppender.setRollingPolicy(rollingPolicy);
        rollingFileAppender.setEncoder(encoder);
        rollingFileAppender.start();

        AsyncAppender asyncAppender = new AsyncAppender();
        asyncAppender.setQueueSize(1);
        asyncAppender.setContext(loggerContext);
        asyncAppender.addAppender(rollingFileAppender);
        asyncAppender.start();

        Logger logger = (Logger) LoggerFactory.getLogger(org.slf4j.Logger.ROOT_LOGGER_NAME);
        logger.setLevel(Level.toLevel(rootLogLevel, Level.DEBUG));
        logger.addAppender(asyncAppender);
        logger.setAdditive(false);

        return logger;
    }
}
