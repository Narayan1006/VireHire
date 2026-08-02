package com.verehire.auth;

import java.util.UUID;

/**
 * Immutable principal stored in the Spring SecurityContext after JWT validation.
 *
 * Retrieved in any @RestController via:
 *   @AuthenticationPrincipal AuthenticatedUser user
 *
 * or via SecurityContextHolder:
 *   AuthenticatedUser user = (AuthenticatedUser)
 *       SecurityContextHolder.getContext().getAuthentication().getPrincipal();
 *
 * @param userId UUID of the authenticated recruiter
 * @param email  Recruiter's email address
 */
public record AuthenticatedUser(UUID userId, String email) {
}
