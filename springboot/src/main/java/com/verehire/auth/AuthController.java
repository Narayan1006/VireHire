package com.verehire.auth;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * Authentication endpoints — no JWT required.
 *
 * POST /api/auth/signup → Register + return JWT
 * POST /api/auth/login  → Authenticate + return JWT
 * GET  /api/auth/me     → Return current user info (JWT required)
 * POST /api/auth/logout → Stateless logout (JWT required, frontend clears token)
 */
@RestController
@RequestMapping("/api/auth")
@Tag(name = "Authentication", description = "Recruiter signup, login, and session management")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/signup")
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(summary = "Register a new recruiter account")
    public ResponseEntity<AuthResponse> signup(@Valid @RequestBody SignupRequest request) {
        AuthResponse response = authService.signup(request.getEmail(), request.getPassword());
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @PostMapping("/login")
    @Operation(summary = "Authenticate and receive a JWT")
    public AuthResponse login(@Valid @RequestBody LoginRequest request) {
        return authService.login(request.getEmail(), request.getPassword());
    }

    @GetMapping("/me")
    @Operation(summary = "Return the current authenticated user")
    public Map<String, String> me(@AuthenticationPrincipal AuthenticatedUser user) {
        return Map.of(
            "id",    user.userId().toString(),
            "email", user.email(),
            "role",  "recruiter"
        );
    }

    @PostMapping("/logout")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    @Operation(
        summary = "Logout (stateless)",
        description = "JWT-based auth is stateless — the server holds no session. " +
                      "The frontend removes the token from localStorage. Returns 204."
    )
    public ResponseEntity<Void> logout(@AuthenticationPrincipal AuthenticatedUser user) {
        return ResponseEntity.noContent().build();
    }

    public static class SignupRequest {
        @NotBlank(message = "Email is required.")
        @Email(message = "Must be a valid email address.")
        private String email;

        @NotBlank(message = "Password is required.")
        @Size(min = 8, message = "Password must be at least 8 characters.")
        private String password;

        public SignupRequest() {}
        public SignupRequest(String email, String password) { this.email = email; this.password = password; }

        public String getEmail() { return email; }
        public void setEmail(String email) { this.email = email; }
        public String getPassword() { return password; }
        public void setPassword(String password) { this.password = password; }
    }

    public static class LoginRequest {
        @NotBlank(message = "Email is required.")
        @Email(message = "Must be a valid email address.")
        private String email;

        @NotBlank(message = "Password is required.")
        private String password;

        public LoginRequest() {}
        public LoginRequest(String email, String password) { this.email = email; this.password = password; }

        public String getEmail() { return email; }
        public void setEmail(String email) { this.email = email; }
        public String getPassword() { return password; }
        public void setPassword(String password) { this.password = password; }
    }
}
