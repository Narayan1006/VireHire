package com.verehire.health;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Health check endpoint — no authentication required.
 *
 * Returns the same JSON shape as the original Python backend so the
 * React frontend's version detection (backendSupportsMultipartRank)
 * correctly identifies this as v2.0.0 ≥ 1.0.1 and always uses
 * the multipart /api/rank endpoint.
 */
@RestController
@RequestMapping("/api")
@Tag(name = "Health", description = "Service health and version info")
public class HealthController {

    private static final String VERSION = "2.0.0";
    private static final String SERVICE = "VereHire Spring Boot API";

    @GetMapping("/health")
    @Operation(
        summary = "Service health check",
        description = "Returns service status and version. No authentication required."
    )
    public ResponseEntity<Map<String, Object>> health() {
        // LinkedHashMap preserves insertion order in JSON response
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("status", "ok");
        body.put("version", VERSION);
        body.put("service", SERVICE);
        body.put("timestamp", Instant.now().toString());
        return ResponseEntity.ok(body);
    }
}
