package com.verehire.candidate;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.verehire.auth.AuthenticatedUser;
import com.verehire.job.JobEntity;
import com.verehire.job.JobRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.data.domain.Page;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.*;

/**
 * Controller for retrieving candidate results.
 *
 * GET /api/candidates      → Paginated list of candidates for a job
 * GET /api/candidates/{id} → Full profile detail for a single candidate
 */
@RestController
@RequestMapping("/api/candidates")
@Tag(name = "Candidates", description = "Query and view ranked candidate profiles")
public class CandidateController {

    private final CandidateService candidateService;
    private final JobRepository jobRepository;
    private final ObjectMapper objectMapper;

    public CandidateController(
        CandidateService candidateService,
        JobRepository jobRepository,
        ObjectMapper objectMapper
    ) {
        this.candidateService = candidateService;
        this.jobRepository = jobRepository;
        this.objectMapper = objectMapper;
    }

    @GetMapping
    @Operation(summary = "List candidates for a job (paginated, filterable)")
    public ResponseEntity<Map<String, Object>> listCandidates(
        @AuthenticationPrincipal AuthenticatedUser user,
        @RequestParam(value = "job_id", required = false) String jobId,
        @RequestParam(value = "verdict", required = false) String verdict,
        @RequestParam(value = "min_score", required = false) Integer minScore,
        @RequestParam(value = "page", defaultValue = "0") int page,
        @RequestParam(value = "limit", defaultValue = "20") int limit,
        @RequestParam(value = "offset", required = false) Integer offset
    ) {
        // If offset provided instead of page (frontend uses offset parameter)
        if (offset != null && offset > 0 && limit > 0) {
            page = offset / limit;
        }

        // If no job_id specified, use the user's latest job
        String targetJobId = jobId;
        if (targetJobId == null || targetJobId.isBlank()) {
            Optional<JobEntity> latest = jobRepository.findLatestByUserId(user.userId());
            if (latest.isEmpty()) {
                return ResponseEntity.ok(Map.of(
                    "candidates", List.of(),
                    "total", 0,
                    "limit", limit,
                    "offset", 0
                ));
            }
            targetJobId = latest.get().getJobId();
        }

        Page<CandidateEntity> pageResult = candidateService.getCandidates(
            user.userId(), targetJobId, verdict, minScore, page, limit
        );

        List<Map<String, Object>> candidateList = pageResult.getContent().stream()
            .map(this::toMap)
            .toList();

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("candidates", candidateList);
        body.put("total", pageResult.getTotalElements());
        body.put("limit", limit);
        body.put("offset", page * limit);
        body.put("job_id", targetJobId);

        return ResponseEntity.ok(body);
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get candidate detail profile by ID")
    public ResponseEntity<Map<String, Object>> getCandidateDetail(
        @AuthenticationPrincipal AuthenticatedUser user,
        @PathVariable("id") UUID id
    ) {
        CandidateEntity candidate = candidateService.getCandidateById(user.userId(), id);
        return ResponseEntity.ok(toMap(candidate));
    }

    /**
     * Map CandidateEntity to JSON Map matching CandidateOutput format expected by React frontend.
     */
    private Map<String, Object> toMap(CandidateEntity entity) {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("id", entity.getId().toString());
        map.put("candidate_id", entity.getCandidateId());
        map.put("job_id", entity.getJobId());
        map.put("name", entity.getName());
        map.put("email", entity.getEmail());
        map.put("role", entity.getRole());
        map.put("rank", entity.getRank());
        map.put("percentile", entity.getPercentile());
        map.put("pr_score", entity.getPrScore());
        map.put("github_score", entity.getGithubScore());
        map.put("dsa_score", entity.getDsaScore());
        map.put("verdict", entity.getVerdict());

        // Parse JSONB strings back to JSON objects/arrays for response
        map.put("skills", parseJson(entity.getSkills(), List.of()));
        map.put("github_evidence", parseJson(entity.getGithubEvidence(), Map.of()));
        map.put("leetcode", parseJson(entity.getLeetcode(), Map.of()));
        map.put("codeforces", entity.getCodeforces() != null ? parseJson(entity.getCodeforces(), null) : null);
        map.put("timeline", parseJson(entity.getTimeline(), List.of()));
        map.put("risk_flags", parseJson(entity.getRiskFlags(), List.of()));

        map.put("summary", entity.getSummary());
        map.put("layer1_score", entity.getLayer1Score());
        map.put("layer2_score", entity.getLayer2Score());
        map.put("layer3_confidence", entity.getLayer3Confidence());

        return map;
    }

    private Object parseJson(String json, Object fallback) {
        if (json == null || json.isBlank()) return fallback;
        try {
            return objectMapper.readValue(json, Object.class);
        } catch (Exception e) {
            return fallback;
        }
    }
}
