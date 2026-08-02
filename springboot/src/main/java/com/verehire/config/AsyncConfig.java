package com.verehire.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.concurrent.Executor;

/**
 * Thread pool configuration for @Async background task processing.
 *
 * Used by JobService.runPipeline() when calling the Python AI Service.
 */
@Configuration
@EnableAsync
public class AsyncConfig {

    @Bean(name = "pipelineTaskExecutor")
    public Executor pipelineTaskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(5);
        executor.setMaxPoolSize(10);
        executor.setQueueCapacity(50);
        executor.setThreadNamePrefix("ai-pipeline-");
        executor.initialize();
        return executor;
    }
}
