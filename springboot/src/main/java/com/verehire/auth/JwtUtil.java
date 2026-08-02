package com.verehire.auth;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import io.jsonwebtoken.*;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.UUID;

/**
 * JWT utility â€” issues and verifies HS256 tokens.
 *
 * Token payload (claims):
 *   sub  â†’ user UUID (as string)
 *   email â†’ recruiter email
 *   iat  â†’ issued-at timestamp
 *   exp  â†’ expiration timestamp
 *
 * Security: Signature IS verified on every request (unlike the original
 * Python backend which had verify_signature=False â€” that bug is fixed here).
 */
@Component
public class JwtUtil {

    private static final Logger log = LoggerFactory.getLogger(JwtUtil.class);

    private final SecretKey signingKey;
    private final long expirationMs;

    public JwtUtil(
        @Value("${app.jwt.secret}") String secret,
        @Value("${app.jwt.expiration-ms}") long expirationMs
    ) {
        // HMAC-SHA256 requires at least 256-bit (32-byte) key.
        // We derive the key from the configured secret string.
        byte[] keyBytes = secret.getBytes(StandardCharsets.UTF_8);
        if (keyBytes.length < 32) {
            throw new IllegalArgumentException(
                "JWT secret must be at least 32 characters (256 bits). " +
                "Current length: " + keyBytes.length + " chars. " +
                "Generate one with: openssl rand -base64 64"
            );
        }
        this.signingKey = Keys.hmacShaKeyFor(keyBytes);
        this.expirationMs = expirationMs;
    }

    // â”€â”€ Token Generation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    /**
     * Issue a signed JWT for a successfully authenticated user.
     *
     * @param userId UUID of the authenticated user
     * @param email  Recruiter's email address
     * @return signed JWT string
     */
    public String generateToken(UUID userId, String email) {
        Date now = new Date();
        Date expiry = new Date(now.getTime() + expirationMs);

        return Jwts.builder()
            .subject(userId.toString())
            .claim("email", email)
            .issuedAt(now)
            .expiration(expiry)
            .signWith(signingKey)
            .compact();
    }

    // â”€â”€ Token Validation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    /**
     * Validate a token and return its claims.
     *
     * @param token raw JWT string (without "Bearer " prefix)
     * @return parsed {@link Claims} if valid
     * @throws JwtException if token is malformed, expired, or signature invalid
     */
    public Claims validateAndExtractClaims(String token) {
        return Jwts.parser()
            .verifyWith(signingKey)   // â† Signature IS verified (fix for Python's verify_signature=False)
            .build()
            .parseSignedClaims(token)
            .getPayload();
    }

    /**
     * Extract the user UUID from a validated token.
     *
     * @param token raw JWT string
     * @return user UUID
     */
    public UUID extractUserId(String token) {
        String subject = validateAndExtractClaims(token).getSubject();
        return UUID.fromString(subject);
    }

    /**
     * Extract the email from a validated token.
     *
     * @param token raw JWT string
     * @return recruiter email
     */
    public String extractEmail(String token) {
        return validateAndExtractClaims(token).get("email", String.class);
    }

    /**
     * Check if a token is expired without throwing an exception.
     * Used for logging/diagnostics only â€” validation always calls
     * {@link #validateAndExtractClaims} which throws on expiry.
     */
    public boolean isTokenExpired(String token) {
        try {
            Date expiry = validateAndExtractClaims(token).getExpiration();
            return expiry.before(new Date());
        } catch (ExpiredJwtException e) {
            return true;
        } catch (JwtException e) {
            log.debug("JWT parse error during expiry check: {}", e.getMessage());
            return true;
        }
    }
}

