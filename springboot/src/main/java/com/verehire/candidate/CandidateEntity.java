package com.verehire.candidate;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.OffsetDateTime;
import java.util.UUID;

@Entity
@Table(
    name = "candidates",
    schema = "public",
    indexes = {
        @Index(name = "idx_candidates_job_id",   columnList = "job_id"),
        @Index(name = "idx_candidates_rank",     columnList = "job_id, rank"),
        @Index(name = "idx_candidates_verdict",  columnList = "job_id, verdict"),
        @Index(name = "idx_candidates_pr_score", columnList = "job_id, pr_score")
    },
    uniqueConstraints = @UniqueConstraint(
        name = "candidates_job_candidate_unique",
        columnNames = {"job_id", "candidate_id"}
    )
)
public class CandidateEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(updatable = false, nullable = false)
    private UUID id;

    @Column(name = "job_id", nullable = false, updatable = false, length = 8)
    private String jobId;

    @Column(name = "candidate_id", nullable = false, updatable = false)
    private String candidateId;

    @Column(nullable = false)
    private String name = "";

    @Column(nullable = false)
    private String email = "";

    @Column(nullable = false)
    private String role = "";

    @Column(nullable = false)
    private Integer rank = 1;

    @Column(nullable = false)
    private Integer percentile = 0;

    @Column(name = "pr_score", nullable = false)
    private Integer prScore = 0;

    @Column(name = "github_score", nullable = false)
    private Integer githubScore = 0;

    @Column(name = "dsa_score", nullable = false)
    private Integer dsaScore = 0;

    @Column(nullable = false, length = 10)
    private String verdict = "REJECT";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb", nullable = false)
    private String skills = "[]";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "github_evidence", columnDefinition = "jsonb", nullable = false)
    private String githubEvidence = "{}";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb", nullable = false)
    private String leetcode = "{}";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private String codeforces;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb", nullable = false)
    private String timeline = "[]";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "risk_flags", columnDefinition = "jsonb", nullable = false)
    private String riskFlags = "[]";

    @Column(columnDefinition = "TEXT", nullable = false)
    private String summary = "";

    @Column(name = "layer1_score", nullable = false)
    private Double layer1Score = 0.0;

    @Column(name = "layer2_score", nullable = false)
    private Double layer2Score = 0.0;

    @Column(name = "layer3_confidence", nullable = false)
    private Double layer3Confidence = 0.0;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false, nullable = false)
    private OffsetDateTime createdAt;

    public CandidateEntity() {
    }

    public CandidateEntity(UUID id, String jobId, String candidateId, String name, String email, String role, Integer rank, Integer percentile, Integer prScore, Integer githubScore, Integer dsaScore, String verdict, String skills, String githubEvidence, String leetcode, String codeforces, String timeline, String riskFlags, String summary, Double layer1Score, Double layer2Score, Double layer3Confidence, OffsetDateTime createdAt) {
        this.id = id;
        this.jobId = jobId;
        this.candidateId = candidateId;
        this.name = name != null ? name : "";
        this.email = email != null ? email : "";
        this.role = role != null ? role : "";
        this.rank = rank != null ? rank : 1;
        this.percentile = percentile != null ? percentile : 0;
        this.prScore = prScore != null ? prScore : 0;
        this.githubScore = githubScore != null ? githubScore : 0;
        this.dsaScore = dsaScore != null ? dsaScore : 0;
        this.verdict = verdict != null ? verdict : "REJECT";
        this.skills = skills != null ? skills : "[]";
        this.githubEvidence = githubEvidence != null ? githubEvidence : "{}";
        this.leetcode = leetcode != null ? leetcode : "{}";
        this.codeforces = codeforces;
        this.timeline = timeline != null ? timeline : "[]";
        this.riskFlags = riskFlags != null ? riskFlags : "[]";
        this.summary = summary != null ? summary : "";
        this.layer1Score = layer1Score != null ? layer1Score : 0.0;
        this.layer2Score = layer2Score != null ? layer2Score : 0.0;
        this.layer3Confidence = layer3Confidence != null ? layer3Confidence : 0.0;
        this.createdAt = createdAt;
    }

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public String getJobId() { return jobId; }
    public void setJobId(String jobId) { this.jobId = jobId; }

    public String getCandidateId() { return candidateId; }
    public void setCandidateId(String candidateId) { this.candidateId = candidateId; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }

    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }

    public Integer getRank() { return rank; }
    public void setRank(Integer rank) { this.rank = rank; }

    public Integer getPercentile() { return percentile; }
    public void setPercentile(Integer percentile) { this.percentile = percentile; }

    public Integer getPrScore() { return prScore; }
    public void setPrScore(Integer prScore) { this.prScore = prScore; }

    public Integer getGithubScore() { return githubScore; }
    public void setGithubScore(Integer githubScore) { this.githubScore = githubScore; }

    public Integer getDsaScore() { return dsaScore; }
    public void setDsaScore(Integer dsaScore) { this.dsaScore = dsaScore; }

    public String getVerdict() { return verdict; }
    public void setVerdict(String verdict) { this.verdict = verdict; }

    public String getSkills() { return skills; }
    public void setSkills(String skills) { this.skills = skills; }

    public String getGithubEvidence() { return githubEvidence; }
    public void setGithubEvidence(String githubEvidence) { this.githubEvidence = githubEvidence; }

    public String getLeetcode() { return leetcode; }
    public void setLeetcode(String leetcode) { this.leetcode = leetcode; }

    public String getCodeforces() { return codeforces; }
    public void setCodeforces(String codeforces) { this.codeforces = codeforces; }

    public String getTimeline() { return timeline; }
    public void setTimeline(String timeline) { this.timeline = timeline; }

    public String getRiskFlags() { return riskFlags; }
    public void setRiskFlags(String riskFlags) { this.riskFlags = riskFlags; }

    public String getSummary() { return summary; }
    public void setSummary(String summary) { this.summary = summary; }

    public Double getLayer1Score() { return layer1Score; }
    public void setLayer1Score(Double layer1Score) { this.layer1Score = layer1Score; }

    public Double getLayer2Score() { return layer2Score; }
    public void setLayer2Score(Double layer2Score) { this.layer2Score = layer2Score; }

    public Double getLayer3Confidence() { return layer3Confidence; }
    public void setLayer3Confidence(Double layer3Confidence) { this.layer3Confidence = layer3Confidence; }

    public OffsetDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }

    public static CandidateEntityBuilder builder() { return new CandidateEntityBuilder(); }

    public static class CandidateEntityBuilder {
        private UUID id;
        private String jobId;
        private String candidateId;
        private String name = "";
        private String email = "";
        private String role = "";
        private Integer rank = 1;
        private Integer percentile = 0;
        private Integer prScore = 0;
        private Integer githubScore = 0;
        private Integer dsaScore = 0;
        private String verdict = "REJECT";
        private String skills = "[]";
        private String githubEvidence = "{}";
        private String leetcode = "{}";
        private String codeforces;
        private String timeline = "[]";
        private String riskFlags = "[]";
        private String summary = "";
        private Double layer1Score = 0.0;
        private Double layer2Score = 0.0;
        private Double layer3Confidence = 0.0;
        private OffsetDateTime createdAt;

        CandidateEntityBuilder() {}

        public CandidateEntityBuilder id(UUID id) { this.id = id; return this; }
        public CandidateEntityBuilder jobId(String jobId) { this.jobId = jobId; return this; }
        public CandidateEntityBuilder candidateId(String candidateId) { this.candidateId = candidateId; return this; }
        public CandidateEntityBuilder name(String name) { this.name = name; return this; }
        public CandidateEntityBuilder email(String email) { this.email = email; return this; }
        public CandidateEntityBuilder role(String role) { this.role = role; return this; }
        public CandidateEntityBuilder rank(Integer rank) { this.rank = rank; return this; }
        public CandidateEntityBuilder percentile(Integer percentile) { this.percentile = percentile; return this; }
        public CandidateEntityBuilder prScore(Integer prScore) { this.prScore = prScore; return this; }
        public CandidateEntityBuilder githubScore(Integer githubScore) { this.githubScore = githubScore; return this; }
        public CandidateEntityBuilder dsaScore(Integer dsaScore) { this.dsaScore = dsaScore; return this; }
        public CandidateEntityBuilder verdict(String verdict) { this.verdict = verdict; return this; }
        public CandidateEntityBuilder skills(String skills) { this.skills = skills; return this; }
        public CandidateEntityBuilder githubEvidence(String githubEvidence) { this.githubEvidence = githubEvidence; return this; }
        public CandidateEntityBuilder leetcode(String leetcode) { this.leetcode = leetcode; return this; }
        public CandidateEntityBuilder codeforces(String codeforces) { this.codeforces = codeforces; return this; }
        public CandidateEntityBuilder timeline(String timeline) { this.timeline = timeline; return this; }
        public CandidateEntityBuilder riskFlags(String riskFlags) { this.riskFlags = riskFlags; return this; }
        public CandidateEntityBuilder summary(String summary) { this.summary = summary; return this; }
        public CandidateEntityBuilder layer1Score(Double layer1Score) { this.layer1Score = layer1Score; return this; }
        public CandidateEntityBuilder layer2Score(Double layer2Score) { this.layer2Score = layer2Score; return this; }
        public CandidateEntityBuilder layer3Confidence(Double layer3Confidence) { this.layer3Confidence = layer3Confidence; return this; }
        public CandidateEntityBuilder createdAt(OffsetDateTime createdAt) { this.createdAt = createdAt; return this; }

        public CandidateEntity build() {
            return new CandidateEntity(id, jobId, candidateId, name, email, role, rank, percentile, prScore, githubScore, dsaScore, verdict, skills, githubEvidence, leetcode, codeforces, timeline, riskFlags, summary, layer1Score, layer2Score, layer3Confidence, createdAt);
        }
    }
}
