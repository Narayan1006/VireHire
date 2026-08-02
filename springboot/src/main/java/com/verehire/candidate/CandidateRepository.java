package com.verehire.candidate;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Spring Data JPA repository for {@link CandidateEntity}.
 *
 * All queries are scoped to a specific job_id.
 * User authorization (job_id belongs to userId) is enforced by JobRepository
 * before these methods are called — never call these directly without
 * first verifying job ownership via JobRepository.findByJobIdAndUserId().
 */
@Repository
public interface CandidateRepository extends JpaRepository<CandidateEntity, UUID> {

    /**
     * Paginated list of candidates for a job, sorted by rank ascending.
     * Supports optional verdict filter via Spring Data derived query.
     */
    Page<CandidateEntity> findAllByJobIdOrderByRankAsc(String jobId, Pageable pageable);

    /**
     * Filtered by verdict (HIRE / REVIEW / REJECT) + paginated.
     */
    Page<CandidateEntity> findAllByJobIdAndVerdictOrderByRankAsc(
        String jobId,
        String verdict,
        Pageable pageable
    );

    /**
     * Filtered by minimum pr_score + paginated.
     */
    Page<CandidateEntity> findAllByJobIdAndPrScoreGreaterThanEqualOrderByRankAsc(
        String jobId,
        int minScore,
        Pageable pageable
    );

    /**
     * Filtered by verdict AND minimum pr_score + paginated.
     */
    Page<CandidateEntity> findAllByJobIdAndVerdictAndPrScoreGreaterThanEqualOrderByRankAsc(
        String jobId,
        String verdict,
        int minScore,
        Pageable pageable
    );

    /**
     * All candidates for a job (no pagination).
     * Used by export endpoint to generate the full CSV.
     */
    List<CandidateEntity> findAllByJobIdOrderByRankAsc(String jobId);

    /**
     * Single candidate by UUID and job_id (combined for security).
     */
    Optional<CandidateEntity> findByIdAndJobId(UUID id, String jobId);

    /**
     * Total candidates in a job. Used by stats endpoint.
     */
    long countByJobId(String jobId);

    /**
     * Average PR score for a job. Used by stats endpoint.
     */
    @Query("SELECT COALESCE(AVG(c.prScore), 0) FROM CandidateEntity c WHERE c.jobId = :jobId")
    Double avgPrScoreByJobId(@Param("jobId") String jobId);

    /**
     * Count candidates with at least one verified evidence source.
     * A profile is "verified" if githubEvidence contains verified=true OR
     * leetcode contains verified=true. Uses JSON path check.
     *
     * Note: This is a native query because JPQL does not support JSONB operators.
     */
    @Query(
        value = """
            SELECT COUNT(*) FROM candidates
            WHERE job_id = :jobId
            AND (
                (github_evidence ->> 'verified')::boolean = true
                OR (leetcode ->> 'verified')::boolean = true
                OR (codeforces ->> 'verified')::boolean = true
            )
            """,
        nativeQuery = true
    )
    long countVerifiedByJobId(@Param("jobId") String jobId);

    /**
     * Verdict distribution for a job.
     * Returns Object[] rows: [verdict (String), count (Long)]
     */
    @Query("SELECT c.verdict, COUNT(c) FROM CandidateEntity c WHERE c.jobId = :jobId GROUP BY c.verdict")
    List<Object[]> countByVerdictForJob(@Param("jobId") String jobId);

    /**
     * Average PR score per verdict for a job.
     * Returns Object[] rows: [verdict (String), avg (Double)]
     */
    @Query("SELECT c.verdict, AVG(c.prScore) FROM CandidateEntity c WHERE c.jobId = :jobId GROUP BY c.verdict")
    List<Object[]> avgPrScoreByVerdictForJob(@Param("jobId") String jobId);

    /**
     * Delete all candidates for a job (used when re-running a pipeline).
     */
    void deleteAllByJobId(String jobId);
}
