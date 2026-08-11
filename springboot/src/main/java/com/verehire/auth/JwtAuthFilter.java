package com.verehire.auth;

import com.verehire.user.FirestoreUserRepository;
import com.verehire.user.UserEntity;
import io.jsonwebtoken.JwtException;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.lang.NonNull;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Stateless JWT authentication filter.
 *
 * Runs once per request. Extracts the Bearer token from the Authorization
 * header, validates the signature and expiry via JwtUtil, loads the user
 * from Firestore, and populates the Spring SecurityContext.
 */
@Component
public class JwtAuthFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(JwtAuthFilter.class);

    private final JwtUtil jwtUtil;
    private final FirestoreUserRepository userRepository;

    public JwtAuthFilter(JwtUtil jwtUtil, FirestoreUserRepository userRepository) {
        this.jwtUtil = jwtUtil;
        this.userRepository = userRepository;
    }

    @Override
    protected void doFilterInternal(
        @NonNull HttpServletRequest request,
        @NonNull HttpServletResponse response,
        @NonNull FilterChain filterChain
    ) throws ServletException, IOException {

        String token = extractToken(request);

        if (token != null && SecurityContextHolder.getContext().getAuthentication() == null) {
            try {
                UUID userId = jwtUtil.extractUserId(token);
                String email = jwtUtil.extractEmail(token);

                Optional<UserEntity> userOpt = userRepository.findById(userId);
                if (userOpt.isPresent()) {
                    AuthenticatedUser principal = new AuthenticatedUser(userId, email);

                    UsernamePasswordAuthenticationToken authToken =
                        new UsernamePasswordAuthenticationToken(
                            principal,
                            null,
                            List.of(new SimpleGrantedAuthority("ROLE_RECRUITER"))
                        );
                    authToken.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
                    SecurityContextHolder.getContext().setAuthentication(authToken);

                    log.debug("Authenticated user: {} ({})", email, userId);
                } else {
                    log.debug("JWT valid but user not found in Firestore: {}", userId);
                }

            } catch (JwtException e) {
                log.debug("JWT validation failed: {}", e.getMessage());
            } catch (Exception e) {
                log.warn("Unexpected error during JWT processing: {}", e.getMessage());
            }
        }

        filterChain.doFilter(request, response);
    }

    private String extractToken(HttpServletRequest request) {
        String header = request.getHeader("Authorization");
        if (StringUtils.hasText(header) && header.startsWith("Bearer ")) {
            return header.substring(7).trim();
        }
        return null;
    }
}
