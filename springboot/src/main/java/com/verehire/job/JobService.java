package com.verehire.job;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.verehire.ai.AiServiceClient;
import com.verehire.candidate.CandidateEntity;
import com.verehire.candidate.CandidateRepository;
import com.verehire.exception.ApiException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import com.verehire.config.AESEncryptionUtil;
import com.verehire.user.UserSettingsEntity;
import com.verehire.user.UserSettingsRepository;

/**
 * Service managing ranking jobs and pipeline execution.
 *
 * Spring Boot is the ONLY owner of database writes.
 *
 * Flow:
 *   1. createAndTriggerJob(): creates JobEntity (status=PROCESSING), calls @Async runPipelineAsync()
 *   2. runPipelineAsync(): calls AiServiceClient (blocking HTTP to Python), converts returned JSON to
 *      CandidateEntity objects, persists all candidates to Supabase PostgreSQL, sets status=COMPLETED.
 */
@Service
public class JobService {

    private static final Logger log = LoggerFactory.getLogger(JobService.class);

    private final JobRepository jobRepository;
    private final CandidateRepository candidateRepository;
    private final AiServiceClient aiServiceClient;
    private final ObjectMapper objectMapper;
    private final UserSettingsRepository userSettingsRepository;
    private final AESEncryptionUtil encryptionUtil;

    public JobService(
        JobRepository jobRepository,
        CandidateRepository candidateRepository,
        AiServiceClient aiServiceClient,
        ObjectMapper objectMapper,
        UserSettingsRepository userSettingsRepository,
        AESEncryptionUtil encryptionUtil
    ) {
        this.jobRepository = jobRepository;
        this.candidateRepository = candidateRepository;
        this.aiServiceClient = aiServiceClient;
        this.objectMapper = objectMapper;
        this.userSettingsRepository = userSettingsRepository;
        this.encryptionUtil = encryptionUtil;
    }

    /**
     * Create a new job in PROCESSING state and trigger async pipeline execution.
     *
     * @param userId owner recruiter ID
     * @param jobDescription JD text
     * @param csvBytes raw CSV bytes
     * @param filename original filename
     * @return short 8-char job hex ID
     */
    @Transactional
    public String createAndTriggerJob(UUID userId, String jobDescription, byte[] csvBytes, String filename) {
        String hexId = UUID.randomUUID().toString().replace("-", "").substring(0, 8);

        JobEntity job = JobEntity.builder()
            .jobId(hexId)
            .userId(userId)
            .jobDescription(jobDescription)
            .status(JobStatus.PROCESSING)
            .build();

        jobRepository.save(job);
        log.info("Job created: jobId={}, userId={}", hexId, userId);

        // Self-invocation of @Async method via Spring bean proxy is needed for @Async to intercept.
        // Spring handles proxy injection properly when called on the bean.
        triggerAsyncPipeline(hexId, userId, jobDescription, csvBytes, filename);

        return hexId;
    }

    @Async("pipelineTaskExecutor")
    public void triggerAsyncPipeline(String jobId, UUID userId, String jobDescription, byte[] csvBytes, String filename) {
        log.info("Starting background AI pipeline for jobId={}", jobId);
        try {
            UserSettingsEntity settings = userSettingsRepository.findByUserId(userId).orElse(null);
            String provider = settings != null ? settings.getAiProvider() : null;
            String githubToken = settings != null ? encryptionUtil.decrypt(settings.getGithubTokenEncrypted()) : null;
            String groqApiKey = settings != null ? encryptionUtil.decrypt(settings.getGroqApiKeyEncrypted()) : null;
            String ollamaBaseUrl = settings != null ? settings.getOllamaBaseUrl() : null;

            List<Map<String, Object>> candidateJsonList = aiServiceClient.callPipeline(
                jobDescription, csvBytes, filename, provider, githubToken, groqApiKey, ollamaBaseUrl
            );
            savePipelineResults(jobId, candidateJsonList);

        } catch (Exception e) {
            log.error("Pipeline failed for jobId={}: {}", jobId, e.getMessage(), e);
            markJobFailed(jobId, e.getMessage());
        }
    }

    @Transactional
    public void savePipelineResults(String jobId, List<Map<String, Object>> candidateJsonList) {
        JobEntity job = jobRepository.findByJobId(jobId)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Job not found: " + jobId));

        List<CandidateEntity> entities = new ArrayList<>();

        for (Map<String, Object> map : candidateJsonList) {
            CandidateEntity candidate = CandidateEntity.builder()
                .jobId(jobId)
                .candidateId(asString(map.get("id")))
                .name(asString(map.get("name")))
                .email(asString(map.get("email")))
                .role(asString(map.get("role")))
                .rank(asInt(map.get("rank"), 1))
                .percentile(asInt(map.get("percentile"), 0))
                .prScore(asInt(map.get("pr_score"), 0))
                .githubScore(asInt(map.get("github_score"), 0))
                .dsaScore(asInt(map.get("dsa_score"), 0))
                .verdict(asString(map.get("verdict")))
                .skills(toJsonString(map.get("skills")))
                .githubEvidence(toJsonString(map.get("github_evidence")))
                .leetcode(toJsonString(map.get("leetcode")))
                .codeforces(map.get("codeforces") != null ? toJsonString(map.get("codeforces")) : null)
                .timeline(toJsonString(map.get("timeline")))
                .riskFlags(toJsonString(map.get("risk_flags")))
                .summary(asString(map.get("summary")))
                .layer1Score(asDouble(map.get("layer1_score")))
                .layer2Score(asDouble(map.get("layer2_score")))
                .layer3Confidence(asDouble(map.get("layer3_confidence")))
                .build();

            entities.add(candidate);
        }

        candidateRepository.saveAll(entities);

        job.setStatus(JobStatus.COMPLETED);
        job.setTotalCandidates(entities.size());
        jobRepository.save(job);

        log.info("Saved {} candidates for jobId={}. Status set to COMPLETED.", entities.size(), jobId);
    }

    @Transactional
    public void markJobFailed(String jobId, String errorMessage) {
        jobRepository.findByJobId(jobId).ifPresent(job -> {
            job.setStatus(JobStatus.FAILED);
            job.setErrorMessage(errorMessage != null ? errorMessage : "Pipeline error occurred.");
            jobRepository.save(job);
            log.warn("JobId={} set to FAILED: {}", jobId, errorMessage);
        });
    }

    @Transactional(readOnly = true)
    public JobEntity getJobForUser(String jobId, UUID userId) {
        return jobRepository.findByJobIdAndUserId(jobId, userId)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Job not found or access denied: " + jobId));
    }

    private String asString(Object val) {
        return val != null ? val.toString() : "";
    }

    private int asInt(Object val, int fallback) {
        if (val instanceof Number num) return num.intValue();
        if (val != null) {
            try { return Integer.parseInt(val.toString()); } catch (Exception ignored) {}
        }
        return fallback;
    }

    private double asDouble(Object val) {
        if (val instanceof Number num) return num.doubleValue();
        if (val != null) {
            try { return Double.parseDouble(val.toString()); } catch (Exception ignored) {}
        }
        return 0.0;
    }

    private String toJsonString(Object val) {
        if (val == null) return "[]";
        if (val instanceof String str) return str;
        try {
            return objectMapper.writeValueAsString(val);
        } catch (Exception e) {
            return "[]";
        }
    }
}
