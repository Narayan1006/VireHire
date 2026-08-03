package com.verehire.ai;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.verehire.exception.ApiException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;

import java.util.List;
import java.util.Map;

/**
 * HTTP client for communicating with the Python AI Service.
 *
 * Forwards the uploaded CSV bytes + job description as multipart/form-data
 * to Python POST /pipeline/rank, and parses the returned CandidateOutput JSON list.
 */
@Component
public class AiServiceClient {

    private static final Logger log = LoggerFactory.getLogger(AiServiceClient.class);

    private final RestClient restClient;
    private final ObjectMapper objectMapper;

    public AiServiceClient(
        @Value("${app.ai-service.url}") String baseUrl,
        @Value("${app.ai-service.timeout-minutes:30}") int timeoutMinutes,
        ObjectMapper objectMapper
    ) {
        this.objectMapper = objectMapper;

        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        int timeoutMs = timeoutMinutes * 60 * 1000;
        requestFactory.setConnectTimeout(10000);
        requestFactory.setReadTimeout(timeoutMs);

        this.restClient = RestClient.builder()
            .baseUrl(baseUrl)
            .requestFactory(requestFactory)
            .build();

        log.info("AiServiceClient initialized with baseUrl={}, readTimeout={}m", baseUrl, timeoutMinutes);
    }

    /**
     * Call Python POST /pipeline/rank with job description and CSV file bytes.
     *
     * @param jobDescription JD text
     * @param csvBytes raw CSV file bytes
     * @param filename original filename
     * @return List of parsed candidate output maps from Python JSON response
     */
    public List<Map<String, Object>> callPipeline(String jobDescription, byte[] csvBytes, String filename,
                                                  String provider, String githubToken, String groqApiKey, String ollamaBaseUrl) {
        log.info("Calling Python AI service: filename={}, bytes={}, jd_length={}", filename, csvBytes.length, jobDescription.length());

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("job_description", jobDescription);
        
        if (provider != null) body.add("provider", provider);
        if (githubToken != null) body.add("github_token", githubToken);
        if (groqApiKey != null) body.add("groq_api_key", groqApiKey);
        if (ollamaBaseUrl != null) body.add("ollama_base_url", ollamaBaseUrl);

        // Named ByteArrayResource so Spring sends correct filename parameter in multipart header
        ByteArrayResource fileResource = new ByteArrayResource(csvBytes) {
            @Override
            public String getFilename() {
                return filename != null ? filename : "candidates.csv";
            }
        };
        body.add("csv_file", fileResource);

        try {
            String rawJson = restClient.post()
                .uri("/pipeline/rank")
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(body)
                .retrieve()
                .body(String.class);

            if (rawJson == null || rawJson.isBlank()) {
                throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, "Empty response from Python AI Service.");
            }

            List<Map<String, Object>> candidates = objectMapper.readValue(rawJson, new TypeReference<>() {});
            log.info("Received {} candidate results from Python AI Service.", candidates.size());
            return candidates;

        } catch (ApiException e) {
            throw e;
        } catch (Exception e) {
            log.error("Failed to execute AI pipeline via Python service: {}", e.getMessage(), e);
            throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, "Python AI Service call failed: " + e.getMessage(), e);
        }
    }
}
