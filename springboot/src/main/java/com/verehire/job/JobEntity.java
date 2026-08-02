package com.verehire.job;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.OffsetDateTime;
import java.util.UUID;

@Entity
@Table(
    name = "jobs",
    schema = "public",
    indexes = {
        @Index(name = "idx_jobs_user_id", columnList = "user_id"),
        @Index(name = "idx_jobs_job_id",  columnList = "job_id"),
        @Index(name = "idx_jobs_status",  columnList = "user_id, status")
    }
)
public class JobEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(updatable = false, nullable = false)
    private UUID id;

    @Column(name = "job_id", unique = true, nullable = false, length = 8, updatable = false)
    private String jobId;

    @Column(name = "user_id", nullable = false, updatable = false)
    private UUID userId;

    @Column(name = "job_description", columnDefinition = "TEXT", nullable = false)
    private String jobDescription;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private JobStatus status = JobStatus.PROCESSING;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    @Column(name = "total_candidates")
    private Integer totalCandidates;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false, nullable = false)
    private OffsetDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;

    public JobEntity() {
    }

    public JobEntity(UUID id, String jobId, UUID userId, String jobDescription, JobStatus status, String errorMessage, Integer totalCandidates, OffsetDateTime createdAt, OffsetDateTime updatedAt) {
        this.id = id;
        this.jobId = jobId;
        this.userId = userId;
        this.jobDescription = jobDescription;
        this.status = status != null ? status : JobStatus.PROCESSING;
        this.errorMessage = errorMessage;
        this.totalCandidates = totalCandidates;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public String getJobId() { return jobId; }
    public void setJobId(String jobId) { this.jobId = jobId; }

    public UUID getUserId() { return userId; }
    public void setUserId(UUID userId) { this.userId = userId; }

    public String getJobDescription() { return jobDescription; }
    public void setJobDescription(String jobDescription) { this.jobDescription = jobDescription; }

    public JobStatus getStatus() { return status; }
    public void setStatus(JobStatus status) { this.status = status; }

    public String getErrorMessage() { return errorMessage; }
    public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }

    public Integer getTotalCandidates() { return totalCandidates; }
    public void setTotalCandidates(Integer totalCandidates) { this.totalCandidates = totalCandidates; }

    public OffsetDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }

    public OffsetDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(OffsetDateTime updatedAt) { this.updatedAt = updatedAt; }

    public static JobEntityBuilder builder() { return new JobEntityBuilder(); }

    public static class JobEntityBuilder {
        private UUID id;
        private String jobId;
        private UUID userId;
        private String jobDescription;
        private JobStatus status = JobStatus.PROCESSING;
        private String errorMessage;
        private Integer totalCandidates;
        private OffsetDateTime createdAt;
        private OffsetDateTime updatedAt;

        JobEntityBuilder() {}

        public JobEntityBuilder id(UUID id) { this.id = id; return this; }
        public JobEntityBuilder jobId(String jobId) { this.jobId = jobId; return this; }
        public JobEntityBuilder userId(UUID userId) { this.userId = userId; return this; }
        public JobEntityBuilder jobDescription(String jobDescription) { this.jobDescription = jobDescription; return this; }
        public JobEntityBuilder status(JobStatus status) { this.status = status; return this; }
        public JobEntityBuilder errorMessage(String errorMessage) { this.errorMessage = errorMessage; return this; }
        public JobEntityBuilder totalCandidates(Integer totalCandidates) { this.totalCandidates = totalCandidates; return this; }
        public JobEntityBuilder createdAt(OffsetDateTime createdAt) { this.createdAt = createdAt; return this; }
        public JobEntityBuilder updatedAt(OffsetDateTime updatedAt) { this.updatedAt = updatedAt; return this; }

        public JobEntity build() {
            return new JobEntity(id, jobId, userId, jobDescription, status, errorMessage, totalCandidates, createdAt, updatedAt);
        }
    }
}
