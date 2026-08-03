package com.verehire.user;

import com.verehire.config.AESEncryptionUtil;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Optional;
import java.util.UUID;

@Service
public class SettingsService {

    private final UserSettingsRepository repository;
    private final AESEncryptionUtil encryptionUtil;

    public SettingsService(UserSettingsRepository repository, AESEncryptionUtil encryptionUtil) {
        this.repository = repository;
        this.encryptionUtil = encryptionUtil;
    }

    @Transactional(readOnly = true)
    public SettingsDTO getSettings(UUID userId) {
        Optional<UserSettingsEntity> entityOpt = repository.findByUserId(userId);
        if (entityOpt.isEmpty()) {
            return null;
        }
        UserSettingsEntity entity = entityOpt.get();
        return SettingsDTO.builder()
                .githubToken(mask(encryptionUtil.decrypt(entity.getGithubTokenEncrypted())))
                .aiProvider(entity.getAiProvider())
                .groqApiKey(mask(encryptionUtil.decrypt(entity.getGroqApiKeyEncrypted())))
                .ollamaBaseUrl(entity.getOllamaBaseUrl())
                .build();
    }
    
    @Transactional(readOnly = true)
    public UserSettingsEntity getRawSettings(UUID userId) {
        return repository.findByUserId(userId).orElse(null);
    }

    @Transactional
    public SettingsDTO saveSettings(UUID userId, SettingsDTO dto) {
        UserSettingsEntity entity = repository.findByUserId(userId)
                .orElse(UserSettingsEntity.builder().userId(userId).build());

        // Update provider and URL
        entity.setAiProvider(dto.getAiProvider());
        entity.setOllamaBaseUrl(dto.getOllamaBaseUrl());

        // Update GitHub token only if it's not empty and not masked
        if (dto.getGithubToken() != null && !dto.getGithubToken().isBlank() && !dto.getGithubToken().contains("****")) {
            entity.setGithubTokenEncrypted(encryptionUtil.encrypt(dto.getGithubToken().trim()));
        } else if (dto.getGithubToken() != null && dto.getGithubToken().trim().isEmpty()) {
            entity.setGithubTokenEncrypted(null);
        }

        // Update Groq key only if it's not empty and not masked
        if (dto.getGroqApiKey() != null && !dto.getGroqApiKey().isBlank() && !dto.getGroqApiKey().contains("****")) {
            entity.setGroqApiKeyEncrypted(encryptionUtil.encrypt(dto.getGroqApiKey().trim()));
        }

        UserSettingsEntity saved = repository.save(entity);

        return SettingsDTO.builder()
                .githubToken(mask(encryptionUtil.decrypt(saved.getGithubTokenEncrypted())))
                .aiProvider(saved.getAiProvider())
                .groqApiKey(mask(encryptionUtil.decrypt(saved.getGroqApiKeyEncrypted())))
                .ollamaBaseUrl(saved.getOllamaBaseUrl())
                .build();
    }

    private String mask(String secret) {
        if (secret == null || secret.isBlank()) return "";
        if (secret.length() <= 4) return "****";
        return "*".repeat(secret.length() - 4) + secret.substring(secret.length() - 4);
    }
}
