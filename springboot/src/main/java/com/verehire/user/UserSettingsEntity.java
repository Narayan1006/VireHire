package com.verehire.user;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.OffsetDateTime;
import java.util.UUID;

@Entity
@Table(name = "user_settings")
public class UserSettingsEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.AUTO)
    private UUID id;

    @Column(name = "user_id", nullable = false, unique = true)
    private UUID userId;

    @Column(name = "github_token_encrypted")
    private String githubTokenEncrypted;

    @Column(name = "ai_provider", nullable = false)
    private String aiProvider;

    @Column(name = "groq_api_key_encrypted")
    private String groqApiKeyEncrypted;

    @Column(name = "ollama_base_url")
    private String ollamaBaseUrl;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;

    public UserSettingsEntity() {}

    public UserSettingsEntity(UUID id, UUID userId, String githubTokenEncrypted, String aiProvider, String groqApiKeyEncrypted, String ollamaBaseUrl, OffsetDateTime createdAt, OffsetDateTime updatedAt) {
        this.id = id;
        this.userId = userId;
        this.githubTokenEncrypted = githubTokenEncrypted;
        this.aiProvider = aiProvider;
        this.groqApiKeyEncrypted = groqApiKeyEncrypted;
        this.ollamaBaseUrl = ollamaBaseUrl;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public UUID getUserId() { return userId; }
    public void setUserId(UUID userId) { this.userId = userId; }

    public String getGithubTokenEncrypted() { return githubTokenEncrypted; }
    public void setGithubTokenEncrypted(String githubTokenEncrypted) { this.githubTokenEncrypted = githubTokenEncrypted; }

    public String getAiProvider() { return aiProvider; }
    public void setAiProvider(String aiProvider) { this.aiProvider = aiProvider; }

    public String getGroqApiKeyEncrypted() { return groqApiKeyEncrypted; }
    public void setGroqApiKeyEncrypted(String groqApiKeyEncrypted) { this.groqApiKeyEncrypted = groqApiKeyEncrypted; }

    public String getOllamaBaseUrl() { return ollamaBaseUrl; }
    public void setOllamaBaseUrl(String ollamaBaseUrl) { this.ollamaBaseUrl = ollamaBaseUrl; }

    public OffsetDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }

    public OffsetDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(OffsetDateTime updatedAt) { this.updatedAt = updatedAt; }

    public static UserSettingsEntityBuilder builder() { return new UserSettingsEntityBuilder(); }

    public static class UserSettingsEntityBuilder {
        private UUID id;
        private UUID userId;
        private String githubTokenEncrypted;
        private String aiProvider;
        private String groqApiKeyEncrypted;
        private String ollamaBaseUrl;
        private OffsetDateTime createdAt;
        private OffsetDateTime updatedAt;

        UserSettingsEntityBuilder() {}

        public UserSettingsEntityBuilder id(UUID id) { this.id = id; return this; }
        public UserSettingsEntityBuilder userId(UUID userId) { this.userId = userId; return this; }
        public UserSettingsEntityBuilder githubTokenEncrypted(String githubTokenEncrypted) { this.githubTokenEncrypted = githubTokenEncrypted; return this; }
        public UserSettingsEntityBuilder aiProvider(String aiProvider) { this.aiProvider = aiProvider; return this; }
        public UserSettingsEntityBuilder groqApiKeyEncrypted(String groqApiKeyEncrypted) { this.groqApiKeyEncrypted = groqApiKeyEncrypted; return this; }
        public UserSettingsEntityBuilder ollamaBaseUrl(String ollamaBaseUrl) { this.ollamaBaseUrl = ollamaBaseUrl; return this; }
        public UserSettingsEntityBuilder createdAt(OffsetDateTime createdAt) { this.createdAt = createdAt; return this; }
        public UserSettingsEntityBuilder updatedAt(OffsetDateTime updatedAt) { this.updatedAt = updatedAt; return this; }

        public UserSettingsEntity build() {
            return new UserSettingsEntity(id, userId, githubTokenEncrypted, aiProvider, groqApiKeyEncrypted, ollamaBaseUrl, createdAt, updatedAt);
        }
    }
}
