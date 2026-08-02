package com.verehire.job;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Spring Data JPA repository for {@link JobEntity}.
 *
 * All multi-result queries are scoped by userId to enforce recruiter
 * data isolation (replaces Supabase RLS).
 */
@Repository
public interface JobRepository extends JpaRepository<JobEntity, UUID> {

    /**
     * Lookup a job by its short hex ID.
     * Used by status polling and candidate retrieval endpoints.
     */
    Optional<JobEntity> findByJobId(String jobId);

    /**
     * Lookup a job by its short hex ID AND owner.
     * Used to prevent cross-user access to job data.
     */
    Optional<JobEntity> findByJobIdAndUserId(String jobId, UUID userId);

    /**
     * All jobs belonging to a user, newest first.
     * Used for the dashboard job history view (future feature).
     */
    List<JobEntity> findAllByUserIdOrderByCreatedAtDesc(UUID userId);

    /**
     * The most recently created job for a user.
     * Used by GET /api/stats when no job_id is specified.
     */
    @Query("SELECT j FROM JobEntity j WHERE j.userId = :userId ORDER BY j.createdAt DESC LIMIT 1")
    Optional<JobEntity> findLatestByUserId(@Param("userId") UUID userId);

    /**
     * Check if a job belongs to a specific user.
     * Lightweight authorization check before loading full entity.
     */
    boolean existsByJobIdAndUserId(String jobId, UUID userId);
}
