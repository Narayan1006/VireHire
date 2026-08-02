package com.verehire.stats;

import com.verehire.candidate.CandidateRepository;
import com.verehire.job.JobEntity;
import com.verehire.job.JobRepository;
import com.verehire.job.JobService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;

/**
 * Service for computing dashboard statistics.
 *
 * Replicates the logic of the original Python GET /api/stats endpoint:
 *   - total_candidates
 *   - avg_score (PR score)
 *   - verified_profiles
 *   - time_saved (estimate: 15 min per candidate)
 *   - verdict_breakdown (counts per HIRE/REVIEW/REJECT)
 *   - avg_scores_by_verdict
 */
@Service
public class StatsService {

    private final CandidateRepository candidateRepository;
    private final JobRepository jobRepository;
    private final JobService jobService;

    public StatsService(
        CandidateRepository candidateRepository,
        JobRepository jobRepository,
        JobService jobService
    ) {
        this.candidateRepository = candidateRepository;
        this.jobRepository = jobRepository;
        this.jobService = jobService;
    }

    @Transactional(readOnly = true)
    public Map<String, Object> getDashboardStats(UUID userId, String jobId) {
        String targetJobId = jobId;

        if (targetJobId == null || targetJobId.isBlank()) {
            Optional<JobEntity> latest = jobRepository.findLatestByUserId(userId);
            if (latest.isEmpty()) {
                return emptyStats();
            }
            targetJobId = latest.get().getJobId();
        } else {
            // Verify job belongs to user
            jobService.getJobForUser(targetJobId, userId);
        }

        long total = candidateRepository.countByJobId(targetJobId);
        if (total == 0) {
            return emptyStats();
        }

        Double avgScoreRaw = candidateRepository.avgPrScoreByJobId(targetJobId);
        int avgScore = (int) Math.round(avgScoreRaw != null ? avgScoreRaw : 0.0);

        long verified = candidateRepository.countVerifiedByJobId(targetJobId);

        // Time saved estimate: 15 min per candidate manual resume review
        double hoursSaved = Math.round((total * 15.0 / 60.0) * 10.0) / 10.0;
        String timeSaved = hoursSaved + " hrs";

        // Verdict breakdown
        Map<String, Integer> verdictBreakdown = new LinkedHashMap<>();
        verdictBreakdown.put("HIRE", 0);
        verdictBreakdown.put("REVIEW", 0);
        verdictBreakdown.put("REJECT", 0);

        List<Object[]> verdictCounts = candidateRepository.countByVerdictForJob(targetJobId);
        for (Object[] row : verdictCounts) {
            String v = (String) row[0];
            Long cnt = (Long) row[1];
            if (v != null) {
                verdictBreakdown.put(v, cnt.intValue());
            }
        }

        // Avg score per verdict
        Map<String, Integer> avgScoresByVerdict = new LinkedHashMap<>();
        avgScoresByVerdict.put("HIRE", 0);
        avgScoresByVerdict.put("REVIEW", 0);
        avgScoresByVerdict.put("REJECT", 0);

        List<Object[]> verdictAvgs = candidateRepository.avgPrScoreByVerdictForJob(targetJobId);
        for (Object[] row : verdictAvgs) {
            String v = (String) row[0];
            Double avg = (Double) row[1];
            if (v != null && avg != null) {
                avgScoresByVerdict.put(v, (int) Math.round(avg));
            }
        }

        Map<String, Object> stats = new LinkedHashMap<>();
        stats.put("total_candidates", (int) total);
        stats.put("avg_score", avgScore);
        stats.put("verified_profiles", (int) verified);
        stats.put("time_saved", timeSaved);
        stats.put("verdict_breakdown", verdictBreakdown);
        stats.put("avg_scores_by_verdict", avgScoresByVerdict);
        stats.put("job_id", targetJobId);

        return stats;
    }

    private Map<String, Object> emptyStats() {
        Map<String, Object> stats = new LinkedHashMap<>();
        stats.put("total_candidates", 0);
        stats.put("avg_score", 0);
        stats.put("verified_profiles", 0);
        stats.put("time_saved", "0 hrs");
        stats.put("verdict_breakdown", Map.of("HIRE", 0, "REVIEW", 0, "REJECT", 0));
        stats.put("avg_scores_by_verdict", Map.of("HIRE", 0, "REVIEW", 0, "REJECT", 0));
        return stats;
    }
}
