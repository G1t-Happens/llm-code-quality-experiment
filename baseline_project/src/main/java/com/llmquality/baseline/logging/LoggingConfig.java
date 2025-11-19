package com.llmquality.baseline.logging;

import ch.qos.logback.classic.AsyncAppender;
import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.LoggerContext;
import ch.qos.logback.classic.encoder.PatternLayoutEncoder;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.ConsoleAppender;
import ch.qos.logback.core.rolling.RollingFileAppender;
import ch.qos.logback.core.rolling.SizeAndTimeBasedRollingPolicy;
import ch.qos.logback.core.util.FileSize;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;
import java.util.Objects;
import java.util.TimeZone;


/**
 * Configures programmatic Logback logging for the application.
 * <p>
 * Features:
 * <ul>
 *     <li>Profile-aware log levels (dev = DEBUG, others = INFO by default)</li>
 *     <li>Asynchronous file logging with size/time-based rolling</li>
 * <li>Optional synchronous console logging</li>
 *     <li>Fully configurable via Spring Boot properties</li>
 * </ul>
 * This replaces XML configuration and initializes Logback at startup.
 */
@Configuration
public class LoggingConfig {

    private static final org.slf4j.Logger LOG = LoggerFactory.getLogger(LoggingConfig.class);

    private static final String DEFAULT_LOG_DIR = "logs";
    private static final String DEFAULT_LOG_PATTERN = "%d{yyyy-MM-dd HH:mm:ss} [%thread] %-5level %logger{36} - %msg%n";
    private static final String DEFAULT_ROLLING_PATTERN = "application-%d{yyyy-MM-dd}.%i.log";
    private static final String DEFAULT_MAX_FILE_SIZE = "10MB";
    private static final String DEFAULT_TOTAL_SIZE_CAP = "100MB";

    @Value("${logging.file.path:/home/dbe/projects/llm-code-quality-experiment/baseline_project/logs}")
    private String logDirectoryPath;

    @Value("${logging.file.name:application:errors.log}")
    private String logFileName;

    @Value("${logging.level.root:#{null}}")
    private String rootLogLevel;

    @Value("#{${logging.level:{:}}}")
    private Map<String, String> loggerLevels;

    @Value("${logging.console.enabled:#{null}}")
    private Boolean consoleEnabled;

    @Value("${logging.pattern:" + DEFAULT_LOG_PATTERN + "}")
    private String logPattern;

    @Value("${logging.rolling.fileNamePattern:" + DEFAULT_ROLLING_PATTERN + "}")
    private String rollingFileNamePattern;

    @Value("${logging.rolling.maxFileSize:10MB}")
    private String maxFileSizeStr;

    @Value("${logging.rolling.maxHistory:30}")
    private int maxHistory;

    @Value("${logging.rolling.totalSizeCap:100MB}")
    private String totalSizeCapStr;

    private final Environment environment;
    private LoggerContext loggerContext;
    private volatile boolean initialized = false;

    public LoggingConfig(Environment environment) {
        this.environment = environment;
    }

    @PostConstruct
    public synchronized void initializeLogging() {
        if (initialized) return;
        initialized = true;

        try {
            loggerContext = (LoggerContext) LoggerFactory.getILoggerFactory();
            System.setProperty("user.timezone", "UTC");
            TimeZone.setDefault(TimeZone.getTimeZone("UTC"));

            Path logDir = createLogDirectory(logDirectoryPath);

            String[] activeProfiles = environment.getActiveProfiles();
            String profile = activeProfiles.length > 0 ? activeProfiles[0] : "dev";

            Level level;
            boolean console;
            if (rootLogLevel != null) {
                level = Level.toLevel(rootLogLevel, Level.INFO);
            } else if ("dev".equals(profile)) {
                level = Level.DEBUG;
            } else {
                level = Level.INFO;
            }

            console = Objects.requireNonNullElseGet(consoleEnabled, () -> "dev".equals(profile));

            RollingFileAppender<ILoggingEvent> rollingFileAppender = createRollingFileAppender(logDir);

            AsyncAppender asyncFileAppender = new AsyncAppender();
            asyncFileAppender.setContext(loggerContext);
            asyncFileAppender.setName("ASYNC_FILE");
            asyncFileAppender.addAppender(rollingFileAppender);
            asyncFileAppender.start();

            ConsoleAppender<ILoggingEvent> consoleAppender = null;
            if (console) {
                consoleAppender = createConsoleAppender();
            }

            configureRootLogger(asyncFileAppender, consoleAppender, level);

            configurePackageSpecificLoggers();

            LOG.info("Logging initialized successfully. Profile: {}. Log directory: {}", profile, logDir.toAbsolutePath());

        } catch (Exception e) {
            LOG.error("Failed to initialize logging", e);
        }
    }

    @PreDestroy
    public void shutdownLogging() {
        if (loggerContext != null) {
            loggerContext.stop();
        }
    }

    private Path createLogDirectory(String path) {
        Objects.requireNonNull(path, "Log directory path must not be null");
        try {
            Path logPath = Paths.get(path);
            if (!Files.exists(logPath)) Files.createDirectories(logPath);
            return logPath;
        } catch (Exception e) {
            LOG.error("Failed to create log directory '{}'. Falling back to '{}'.", path, DEFAULT_LOG_DIR, e);
            try {
                Path fallback = Paths.get(DEFAULT_LOG_DIR);
                Files.createDirectories(fallback);
                return fallback;
            } catch (Exception ex) {
                LOG.error("Fallback directory '{}' failed. Using current dir.", DEFAULT_LOG_DIR, ex);
                return Paths.get(".");
            }
        }
    }

    private PatternLayoutEncoder createEncoder(String pattern) {
        if (pattern == null || pattern.isEmpty()) {
            pattern = DEFAULT_LOG_PATTERN;
        }
        PatternLayoutEncoder encoder = new PatternLayoutEncoder();
        encoder.setContext(loggerContext);
        encoder.setPattern(pattern);
        encoder.start();
        return encoder;
    }

    private RollingFileAppender<ILoggingEvent> createRollingFileAppender(Path logDir) {
        PatternLayoutEncoder encoder = createEncoder(logPattern);

        RollingFileAppender<ILoggingEvent> rollingFileAppender = new RollingFileAppender<>();
        rollingFileAppender.setContext(loggerContext);
        rollingFileAppender.setName("ROLLING_FILE");
        rollingFileAppender.setFile(logDir.resolve(logFileName).toString());
        rollingFileAppender.setEncoder(encoder);

        SizeAndTimeBasedRollingPolicy<ILoggingEvent> rollingPolicy = new SizeAndTimeBasedRollingPolicy<>();
        rollingPolicy.setContext(loggerContext);
        rollingPolicy.setParent(rollingFileAppender);

        if (rollingFileNamePattern == null || rollingFileNamePattern.isEmpty()) {
            rollingFileNamePattern = DEFAULT_ROLLING_PATTERN;
        }
        rollingPolicy.setFileNamePattern(logDir + "/" + rollingFileNamePattern);

        FileSize maxFileSize;
        try {
            maxFileSize = FileSize.valueOf(maxFileSizeStr);
        } catch (Exception e) {
            LOG.warn("Invalid maxFileSize '{}', using default {}", maxFileSizeStr, DEFAULT_MAX_FILE_SIZE);
            maxFileSize = FileSize.valueOf(DEFAULT_MAX_FILE_SIZE);
        }
        rollingPolicy.setMaxFileSize(maxFileSize);

        rollingPolicy.setMaxHistory(maxHistory);

        FileSize totalSizeCap;
        try {
            totalSizeCap = FileSize.valueOf(totalSizeCapStr);
        } catch (Exception e) {
            LOG.warn("Invalid totalSizeCap '{}', using default {}", totalSizeCapStr, DEFAULT_TOTAL_SIZE_CAP);
            totalSizeCap = FileSize.valueOf(DEFAULT_TOTAL_SIZE_CAP);
        }
        rollingPolicy.setTotalSizeCap(totalSizeCap);

        rollingPolicy.start();
        rollingFileAppender.setRollingPolicy(rollingPolicy);
        rollingFileAppender.start();

        return rollingFileAppender;
    }


    private ConsoleAppender<ILoggingEvent> createConsoleAppender() {
        PatternLayoutEncoder encoder = createEncoder(logPattern);
        ConsoleAppender<ILoggingEvent> consoleAppender = new ConsoleAppender<>();
        consoleAppender.setContext(loggerContext);
        consoleAppender.setName("CONSOLE");
        consoleAppender.setEncoder(encoder);
        consoleAppender.start();
        return consoleAppender;
    }

    private void configureRootLogger(AsyncAppender asyncFileAppender,
                                     ConsoleAppender<ILoggingEvent> consoleAppender,
                                     Level level) {

        Logger rootLogger = loggerContext.getLogger(org.slf4j.Logger.ROOT_LOGGER_NAME);
        rootLogger.detachAndStopAllAppenders();

        rootLogger.addAppender(asyncFileAppender);

        if (consoleAppender != null) {
            rootLogger.addAppender(consoleAppender);
        }

        rootLogger.setLevel(level);
        rootLogger.setAdditive(false);
    }

    private void configurePackageSpecificLoggers() {
        for (Map.Entry<String, String> entry : loggerLevels.entrySet()) {
            String loggerName = entry.getKey();
            if ("root".equalsIgnoreCase(loggerName)) {
                continue; // Root is already configured
            }
            Level lvl = Level.toLevel(entry.getValue(), Level.INFO);
            loggerContext.getLogger(loggerName).setLevel(lvl);
        }
    }
}
