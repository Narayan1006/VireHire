package com.verehire.candidate;

import com.verehire.exception.ApiException;
import com.verehire.job.JobService;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;

/**
 * Service for querying ranked candidate records.
 */
@Service
public class CandidateService {

    private final CandidateRepository candidateRepository;
    private final JobService jobService;

    public CandidateService(CandidateRepository candidateRepository, JobService jobService) {
        this.candidateRepository = candidateRepository;
        this.jobService = jobService;
    }

    /**
     * Retrieve paginated candidates for a job belonging to the authenticated user.
     *
     * @param userId owner recruiter ID
     * @param jobId 8-char hex job ID
     * @param verdict optional verdict filter (HIRE / REVIEW / REJECT)
     * @param minScore optional minimum PR score filter
     * @param page zero-indexed page number
     * @param limit page size
     * @return Page of CandidateEntity records
     */
    @Transactional(readOnly = true)
    public Page<CandidateEntity> getCandidates(
        UUID userId,
        String jobId,
        String verdict,
        Integer minScore,
        int page,
        int limit
    ) {
        // Enforce security boundary — verifies job belongs to userId
        jobService.getJobForUser(jobId, userId);

        Pageable pageable = PageRequest.of(page, limit);

        if (verdict != null && !verdict.isBlank() && minScore != null && minScore > 0) {
            return candidateRepository.findAllByJobIdAndVerdictAndPrScoreGreaterThanEqualOrderByRankAsc(
                jobId, verdict.toUpperCase(), minScore, pageable
            );
        } else if (verdict != null && !verdict.isBlank()) {
            return candidateRepository.findAllByJobIdAndVerdictOrderByRankAsc(
                jobId, verdict.toUpperCase(), pageable
            );
        } else if (minScore != null && minScore > 0) {
            return candidateRepository.findAllByJobIdAndPrScoreGreaterThanEqualOrderByRankAsc(
                jobId, minScore, pageable
            );
        } else {
            return candidateRepository.findAllByJobIdOrderByRankAsc(jobId, pageable);
        }
    }

    /**
     * Retrieve a single candidate detail by candidate UUID.
     *
     * @param userId owner recruiter ID
     * @param candidateUuid candidate UUID
     * @return CandidateEntity
     */
    @Transactional(readOnly = true)
    public CandidateEntity getCandidateById(UUID userId, UUID candidateUuid) {
        CandidateEntity candidate = candidateRepository.findById(candidateUuid)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Candidate not found: " + candidateUuid));

        // Enforce security boundary
        jobService.getJobForUser(candidate.getJobId(), userId);

        return candidate;
    }
}
