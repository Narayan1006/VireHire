package com.verehire.user;

import com.verehire.config.AESEncryptionUtil;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestClient;

import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/settings")
@Tag(name = "Settings", description = "BYOK settings management")
@SecurityRequirement(name = "Bearer Authentication")
public class SettingsController {

    private final SettingsService settingsService;
    private final RestClient restClient;
    private final AESEncryptionUtil encryptionUtil;

    public SettingsController(SettingsService settingsService, AESEncryptionUtil encryptionUtil) {
        this.settingsService = settingsService;
        this.encryptionUtil = encryptionUtil;
        this.restClient = RestClient.create();
    }

    @GetMapping
    @Operation(summary = "Get current settings", description = "Returns the user's masked settings.")
    public ResponseEntity<?> getSettings(Authentication authentication) {
        UUID userId = UUID.fromString(authentication.getName());
        SettingsDTO dto = settingsService.getSettings(userId);
        if (dto == null) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("message", "No settings found"));
        }
        return ResponseEntity.ok(dto);
    }

    @PostMapping
    @Operation(summary = "Save settings", description = "Creates or updates the user's settings.")
    public ResponseEntity<?> saveSettings(@RequestBody SettingsDTO dto, Authentication authentication) {
        UUID userId = UUID.fromString(authentication.getName());
        SettingsDTO saved = settingsService.saveSettings(userId, dto);
        return ResponseEntity.ok(saved);
    }

    @PostMapping("/test/github")
    @Operation(summary = "Test GitHub connection")
    public ResponseEntity<?> testGithub(@RequestBody Map<String, String> payload, Authentication auth) {
        String token = resolveToken(payload.get("token"), auth, true);
        if (token == null || token.isBlank()) return ResponseEntity.badRequest().body("Token required");

        try {
            restClient.get()
                    .uri("https://api.github.com/user")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
                    .header("X-GitHub-Api-Version", "2022-11-28")
                    .retrieve()
                    .toBodilessEntity();
            return ResponseEntity.ok(Map.of("message", "GitHub Connected"));
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of("error", "Invalid GitHub Token"));
        }
    }

    @PostMapping("/test/groq")
    @Operation(summary = "Test Groq connection")
    public ResponseEntity<?> testGroq(@RequestBody Map<String, String> payload, Authentication auth) {
        String token = resolveToken(payload.get("token"), auth, false);
        if (token == null || token.isBlank()) return ResponseEntity.badRequest().body("Token required");

        try {
            restClient.get()
                    .uri("https://api.groq.com/openai/v1/models")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
                    .retrieve()
                    .toBodilessEntity();
            return ResponseEntity.ok(Map.of("message", "Groq Connected"));
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of("error", "Groq Authentication Failed"));
        }
    }

    @PostMapping("/test/ollama")
    @Operation(summary = "Test Ollama connection")
    public ResponseEntity<?> testOllama(@RequestBody Map<String, String> payload) {
        String url = payload.get("url");
        if (url == null || url.isBlank()) url = "http://localhost:11434";
        if (url.endsWith("/")) url = url.substring(0, url.length() - 1);

        try {
            restClient.get()
                    .uri(url + "/api/tags")
                    .retrieve()
                    .toBodilessEntity();
            return ResponseEntity.ok(Map.of("message", "Ollama Running"));
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of("error", "Cannot reach Ollama server"));
        }
    }

    private String resolveToken(String providedToken, Authentication auth, boolean isGithub) {
        if (providedToken != null && !providedToken.isBlank() && !providedToken.contains("****")) {
            return providedToken.trim();
        }
        // If they just clicked "Test" without editing the masked password, fetch the real one from DB
        UUID userId = UUID.fromString(auth.getName());
        UserSettingsEntity entity = settingsService.getRawSettings(userId);
        if (entity != null) {
            String encrypted = isGithub ? entity.getGithubTokenEncrypted() : entity.getGroqApiKeyEncrypted();
            return encryptionUtil.decrypt(encrypted);
        }
        return null;
    }
}
