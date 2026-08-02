package com.verehire.candidate;

import com.verehire.auth.AuthenticatedUser;
import com.verehire.job.JobService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.io.ByteArrayOutputStream;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * Export endpoint — generates CSV download from candidate results.
 *
 * GET /api/export?job_id={id} → Download ranked candidates as CSV
 */
@RestController
@RequestMapping("/api/export")
@Tag(name = "Export", description = "Export ranked candidates as CSV")
public class ExportController {

    private final CandidateRepository candidateRepository;
    private final JobService jobService;

    public ExportController(CandidateRepository candidateRepository, JobService jobService) {
        this.candidateRepository = candidateRepository;
        this.jobService = jobService;
    }

    @GetMapping
    @Operation(summary = "Export all ranked candidates for a job as a CSV download")
    public ResponseEntity<byte[]> exportCsv(
        @AuthenticationPrincipal AuthenticatedUser user,
        @RequestParam("job_id") String jobId
    ) {
        // Security boundary — verifies job belongs to authenticated user
        jobService.getJobForUser(jobId, user.userId());

        List<CandidateEntity> candidates = candidateRepository.findAllByJobIdOrderByRankAsc(jobId);

        byte[] csv = buildCsv(candidates);

        String filename = "verehire_candidates_" + jobId + ".csv";

        return ResponseEntity.ok()
            .contentType(MediaType.parseMediaType("text/csv"))
            .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + filename + "\"")
            .header("X-Total-Candidates", String.valueOf(candidates.size()))
            .body(csv);
    }

    private byte[] buildCsv(List<CandidateEntity> candidates) {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        PrintWriter writer = new PrintWriter(baos, true, StandardCharsets.UTF_8);

        // Header row
        writer.println(
            "rank,candidate_id,name,email,role,verdict,pr_score,github_score," +
            "dsa_score,percentile,summary,layer1_score,layer2_score,layer3_confidence"
        );

        for (CandidateEntity c : candidates) {
            writer.println(String.join(",",
                safe(c.getRank()),
                safe(c.getCandidateId()),
                csvEscape(c.getName()),
                csvEscape(c.getEmail()),
                csvEscape(c.getRole()),
                safe(c.getVerdict()),
                safe(c.getPrScore()),
                safe(c.getGithubScore()),
                safe(c.getDsaScore()),
                safe(c.getPercentile()),
                csvEscape(c.getSummary()),
                safe(c.getLayer1Score()),
                safe(c.getLayer2Score()),
                safe(c.getLayer3Confidence())
            ));
        }

        writer.flush();
        return baos.toByteArray();
    }

    private String safe(Object val) {
        return val != null ? val.toString() : "";
    }

    /**
     * RFC 4180 CSV escaping: if field contains comma, newline, or quote,
     * wrap in double-quotes and escape any internal double-quotes.
     */
    private String csvEscape(String val) {
        if (val == null) return "";
        if (val.contains(",") || val.contains("\"") || val.contains("\n") || val.contains("\r")) {
            return "\"" + val.replace("\"", "\"\"") + "\"";
        }
        return val;
    }
}
