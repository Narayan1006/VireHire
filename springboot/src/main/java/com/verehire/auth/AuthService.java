package com.verehire.auth;

import com.verehire.exception.ApiException;
import com.verehire.user.FirestoreUserRepository;
import com.verehire.user.UserEntity;
import com.verehire.user.UserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Authentication business logic.
 *
 * Handles recruiter signup and login using Spring Boot's own users table.
 * No Supabase Auth — Spring Boot is the sole owner of authentication.
 */
@Service
public class AuthService {

    private static final Logger log = LoggerFactory.getLogger(AuthService.class);

    private final FirestoreUserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;

    public AuthService(FirestoreUserRepository userRepository, PasswordEncoder passwordEncoder, JwtUtil jwtUtil) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtUtil = jwtUtil;
    }

    @Transactional
    public AuthResponse signup(String email, String password) {
        String normalizedEmail = email.trim().toLowerCase();

        if (userRepository.existsByEmail(normalizedEmail)) {
            throw new ApiException(HttpStatus.CONFLICT, "Email already registered.");
        }

        UserEntity user = UserEntity.builder()
            .email(normalizedEmail)
            .passwordHash(passwordEncoder.encode(password))
            .build();

        user = userRepository.save(user);
        log.info("New recruiter registered: {}", normalizedEmail);

        String token = jwtUtil.generateToken(user.getId(), user.getEmail());
        return new AuthResponse(token, new AuthResponse.UserInfo(user.getId().toString(), user.getEmail()));
    }

    @Transactional(readOnly = true)
    public AuthResponse login(String email, String password) {
        String normalizedEmail = email.trim().toLowerCase();

        UserEntity user = userRepository.findByEmail(normalizedEmail)
            .orElseThrow(() -> new ApiException(HttpStatus.UNAUTHORIZED, "Invalid email or password."));

        if (!passwordEncoder.matches(password, user.getPasswordHash())) {
            log.warn("Failed login attempt for: {}", normalizedEmail);
            throw new ApiException(HttpStatus.UNAUTHORIZED, "Invalid email or password.");
        }

        log.info("Recruiter logged in: {}", normalizedEmail);
        String token = jwtUtil.generateToken(user.getId(), user.getEmail());
        return new AuthResponse(token, new AuthResponse.UserInfo(user.getId().toString(), user.getEmail()));
    }
}
