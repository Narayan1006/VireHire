package com.verehire.job;

import com.verehire.auth.AuthenticatedUser;
import com.verehire.exception.ApiException;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Controller for ranking job creation and status polling.
 *
 * Matches the API contracts expected by the React frontend:
 *   POST /api/rank                → 202 Accepted + job_id
 *   GET  /api/rank/{job_id}/status → job progress / completion status
 */
@RestController
@RequestMapping("/api/rank")
@Tag(name = "Ranking Pipeline", description = "Trigger candidate ranking and poll job status")
public class JobController {

    private final JobService jobService;

    public JobController(JobService jobService) {
        this.jobService = jobService;
    }

    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @Operation(summary = "Submit job description and CSV file for AI ranking")
    public ResponseEntity<Map<String, Object>> triggerRank(
        @AuthenticationPrincipal AuthenticatedUser user,
        @RequestParam("job_description") String jobDescription,
        @RequestParam("csv_file") MultipartFile file
    ) {
        if (jobDescription == null || jobDescription.isBlank()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "job_description is required and cannot be empty.");
        }

        if (file == null || file.isEmpty()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "file (CSV) is required.");
        }

        String filename = file.getOriginalFilename();
        if (filename == null || !filename.toLowerCase().endsWith(".csv")) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Only .csv files are supported.");
        }

        byte[] bytes;
        try {
            bytes = file.getBytes();
        } catch (Exception e) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Failed to read uploaded CSV file.");
        }

        String jobId = jobService.createAndTriggerJob(user.userId(), jobDescription, bytes, filename);

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("job_id", jobId);
        body.put("status", "processing");
        body.put("message", "Ranking job started. Poll GET /api/rank/" + jobId + "/status for progress.");
        body.put("estimated_time_seconds", 30);

        return ResponseEntity.status(HttpStatus.ACCEPTED).body(body);
    }

    @GetMapping("/{jobId}/status")
    @Operation(summary = "Poll progress status for a ranking job")
    public ResponseEntity<Map<String, Object>> getStatus(
        @AuthenticationPrincipal AuthenticatedUser user,
        @PathVariable("jobId") String jobId
    ) {
        JobEntity job = jobService.getJobForUser(jobId, user.userId());

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("job_id", job.getJobId());
        body.put("status", job.getStatus().name().toLowerCase());
        body.put("created_at", job.getCreatedAt().toString());

        if (job.getStatus() == JobStatus.COMPLETED) {
            body.put("message", "Pipeline complete. Candidates are ready.");
            body.put("total_candidates", job.getTotalCandidates());
        } else if (job.getStatus() == JobStatus.FAILED) {
            body.put("message", "Pipeline failed: " + (job.getErrorMessage() != null ? job.getErrorMessage() : "Unknown error"));
            body.put("error", job.getErrorMessage());
        } else {
            body.put("message", "Pipeline is executing AI layers...");
        }

        return ResponseEntity.ok(body);
    }
}
