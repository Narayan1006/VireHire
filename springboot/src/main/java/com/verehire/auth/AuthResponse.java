package com.verehire.auth;

/**
 * Response DTO for /api/auth/login and /api/auth/signup.
 *
 * Matches the JSON shape the React frontend expects:
 * {
 *   "access_token": "eyJ...",
 *   "user": { "id": "uuid", "email": "user@example.com" }
 * }
 */
public class AuthResponse {

    private String accessToken;
    private UserInfo user;

    public AuthResponse() {
    }

    public AuthResponse(String accessToken, UserInfo user) {
        this.accessToken = accessToken;
        this.user = user;
    }

    public String getAccessToken() {
        return accessToken;
    }

    public void setAccessToken(String accessToken) {
        this.accessToken = accessToken;
    }

    public UserInfo getUser() {
        return user;
    }

    public void setUser(UserInfo user) {
        this.user = user;
    }

    public static class UserInfo {
        private String id;
        private String email;

        public UserInfo() {
        }

        public UserInfo(String id, String email) {
            this.id = id;
            this.email = email;
        }

        public String getId() {
            return id;
        }

        public void setId(String id) {
            this.id = id;
        }

        public String getEmail() {
            return email;
        }

        public void setEmail(String email) {
            this.email = email;
        }
    }
}
