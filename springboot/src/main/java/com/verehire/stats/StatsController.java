package com.verehire.stats;

import com.verehire.auth.AuthenticatedUser;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * Dashboard statistics endpoint.
 *
 * GET /api/stats → Aggregated metrics for the specified or latest job.
 */
@RestController
@RequestMapping("/api/stats")
@Tag(name = "Statistics", description = "Dashboard summary metrics and analytics")
public class StatsController {

    private final StatsService statsService;

    public StatsController(StatsService statsService) {
        this.statsService = statsService;
    }

    @GetMapping
    @Operation(summary = "Get dashboard summary statistics")
    public ResponseEntity<Map<String, Object>> getStats(
        @AuthenticationPrincipal AuthenticatedUser user,
        @RequestParam(value = "job_id", required = false) String jobId
    ) {
        Map<String, Object> stats = statsService.getDashboardStats(user.userId(), jobId);
        return ResponseEntity.ok(stats);
    }
}
