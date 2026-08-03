package com.verehire.user;

public class SettingsDTO {
    private String githubToken;
    private String aiProvider;
    private String groqApiKey;
    private String ollamaBaseUrl;

    public SettingsDTO() {}

    public SettingsDTO(String githubToken, String aiProvider, String groqApiKey, String ollamaBaseUrl) {
        this.githubToken = githubToken;
        this.aiProvider = aiProvider;
        this.groqApiKey = groqApiKey;
        this.ollamaBaseUrl = ollamaBaseUrl;
    }

    public String getGithubToken() { return githubToken; }
    public void setGithubToken(String githubToken) { this.githubToken = githubToken; }

    public String getAiProvider() { return aiProvider; }
    public void setAiProvider(String aiProvider) { this.aiProvider = aiProvider; }

    public String getGroqApiKey() { return groqApiKey; }
    public void setGroqApiKey(String groqApiKey) { this.groqApiKey = groqApiKey; }

    public String getOllamaBaseUrl() { return ollamaBaseUrl; }
    public void setOllamaBaseUrl(String ollamaBaseUrl) { this.ollamaBaseUrl = ollamaBaseUrl; }

    public static SettingsDTOBuilder builder() { return new SettingsDTOBuilder(); }

    public static class SettingsDTOBuilder {
        private String githubToken;
        private String aiProvider;
        private String groqApiKey;
        private String ollamaBaseUrl;

        SettingsDTOBuilder() {}

        public SettingsDTOBuilder githubToken(String githubToken) { this.githubToken = githubToken; return this; }
        public SettingsDTOBuilder aiProvider(String aiProvider) { this.aiProvider = aiProvider; return this; }
        public SettingsDTOBuilder groqApiKey(String groqApiKey) { this.groqApiKey = groqApiKey; return this; }
        public SettingsDTOBuilder ollamaBaseUrl(String ollamaBaseUrl) { this.ollamaBaseUrl = ollamaBaseUrl; return this; }

        public SettingsDTO build() {
            return new SettingsDTO(githubToken, aiProvider, groqApiKey, ollamaBaseUrl);
        }
    }
}
