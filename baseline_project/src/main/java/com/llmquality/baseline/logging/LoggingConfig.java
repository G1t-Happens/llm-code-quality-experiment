package com.llmquality.baseline.logging;

import ch.qos.logback.classic.AsyncAppender;
import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.encoder.PatternLayoutEncoder;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.rolling.RollingFileAppender;
import ch.qos.logback.core.rolling.SizeAndTimeBasedRollingPolicy;
import ch.qos.logback.core.util.FileSize;
import jakarta.annotation.PreDestroy;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;


/**
 * Configuration class for setting up logging using Logback.
 * <p>
 * This class configures a rolling file appender for the application logs, ensuring logs are written to files
 * with automatic rotation based on file size and time. It uses asynchronous logging to improve performance.
 * The logging configuration can be customized through application properties such as the log file path,
 * log file name, and the root log level.
 * </p>
 *
 * <p>
 * By default:
 * <ul>
 *     <li>Logs are stored in the 'logs' directory.</li>
 *     <li>The log file is named 'application.log'.</li>
 *     <li>The root logging level is set to 'DEBUG'.</li>
 * </ul>
 * These defaults can be overridden by specifying properties in the application configuration.
 * </p>
 *
 * <p>
 * The class also ensures proper cleanup of resources by stopping the logger context when the application is shutting down.
 * </p>
 *
 * @see org.slf4j.LoggerFactory
 * @see ch.qos.logback.classic.LoggerContext
 */
@Configuration
public class LoggingConfig {

    private static final org.slf4j.Logger LOG = LoggerFactory.getLogger(LoggingConfig.class);

    private static final String DEFAULT_LOG_DIR = "logs";

    private static final String DEFAULT_LOG_FILE = "application.log";

    private final String logDirectoryPath;

    private final String logFileName;

    private final String rootLogLevel;

    private ch.qos.logback.classic.LoggerContext loggerContext;

    public LoggingConfig(
            @Value("${logging.file.path:#{systemProperties['user.dir'] + '/logs'}}") String logDirectoryPath,
            @Value("${logging.file.name:" + DEFAULT_LOG_FILE + "}") String logFileName,
            @Value("${logging.level.root:DEBUG}") String rootLogLevel) {
        this.logDirectoryPath = logDirectoryPath;
        this.logFileName = logFileName;
        this.rootLogLevel = rootLogLevel;
    }

    @Bean
    public Logger logger() {
        loggerContext = (ch.qos.logback.classic.LoggerContext) LoggerFactory.getILoggerFactory();
        Path logDir = initializeLogDirectory(logDirectoryPath);

        PatternLayoutEncoder encoder = new PatternLayoutEncoder();
        encoder.setContext(loggerContext);
        encoder.setPattern("%d{yyyy-MM-dd HH:mm:ss,UTC} [%thread] %-5level %logger{36} - %msg%n");
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
        asyncAppender.setContext(loggerContext);
        asyncAppender.addAppender(rollingFileAppender);
        asyncAppender.start();

        Logger logger = (Logger) LoggerFactory.getLogger("com.llmquality.baseline");
        logger.setLevel(Level.toLevel(rootLogLevel, Level.DEBUG));
        logger.addAppender(asyncAppender);
        logger.setAdditive(false);

        return logger;
    }

    @PreDestroy
    public void shutdownLogging() {
        if (loggerContext != null) {
            loggerContext.stop();
        }
    }

    private Path initializeLogDirectory(String path) {
        try {
            Path logPath = Paths.get(path);
            if (!Files.exists(logPath)) {
                Files.createDirectories(logPath);
            }
            return logPath;
        } catch (Exception e) {
            LOG.error("Failed to initialize log directory '{}'. Using fallback '{}'", path, DEFAULT_LOG_DIR, e);
            try {
                Path fallback = Paths.get(DEFAULT_LOG_DIR);
                Files.createDirectories(fallback);
                return fallback;
            } catch (Exception ex) {
                LOG.error("Fallback log directory '{}' could not be created. Using current dir.", DEFAULT_LOG_DIR, ex);
                return Paths.get(".");
            }
        }
    }
}
