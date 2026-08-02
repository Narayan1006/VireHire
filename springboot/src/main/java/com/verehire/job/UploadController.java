package com.verehire.job;

import com.verehire.auth.AuthenticatedUser;
import com.verehire.exception.ApiException;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Upload endpoint — validates CSV before triggering the pipeline.
 *
 * POST /api/upload → Validate CSV + trigger ranking job, return job_id
 *
 * Note: The original Python /api/upload and /api/rank are merged here.
 * The React frontend currently calls POST /api/rank directly with multipart.
 * This controller provides an alias if needed.
 */
@RestController
@RequestMapping("/api/upload")
@Tag(name = "Upload", description = "CSV upload and validation endpoint")
public class UploadController {

    private final JobService jobService;

    public UploadController(JobService jobService) {
        this.jobService = jobService;
    }

    @PostMapping(consumes = "multipart/form-data")
    @Operation(summary = "Upload candidate CSV + job description, trigger ranking")
    public ResponseEntity<Map<String, Object>> upload(
        @AuthenticationPrincipal AuthenticatedUser user,
        @RequestParam("job_description") String jobDescription,
        @RequestParam("csv_file") MultipartFile file
    ) {
        if (jobDescription == null || jobDescription.isBlank()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "job_description is required.");
        }
        if (file == null || file.isEmpty()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "CSV file is required.");
        }

        String filename = file.getOriginalFilename();
        if (filename == null || !filename.toLowerCase().endsWith(".csv")) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Only .csv files are supported.");
        }

        if (file.getSize() > 55 * 1024 * 1024) { // 55 MB guard
            throw new ApiException(HttpStatus.BAD_REQUEST, "File exceeds 55 MB limit.");
        }

        byte[] bytes;
        try {
            bytes = file.getBytes();
        } catch (Exception e) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Failed to read uploaded file.");
        }

        // Validate CSV has at least a header row
        String content = new String(bytes, java.nio.charset.StandardCharsets.UTF_8);
        String[] lines = content.split("\n");
        if (lines.length < 2) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "CSV file must have a header row and at least one candidate row.");
        }

        String jobId = jobService.createAndTriggerJob(user.userId(), jobDescription, bytes, filename);

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("job_id", jobId);
        body.put("status", "processing");
        body.put("message", "CSV validated and ranking job started.");
        body.put("rows_detected", lines.length - 1);
        body.put("filename", filename);

        return ResponseEntity.status(HttpStatus.ACCEPTED).body(body);
    }
}
