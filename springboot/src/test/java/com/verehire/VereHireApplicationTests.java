package com.verehire;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.TestPropertySource;

/**
 * Smoke test — verifies the Spring Boot application context loads.
 *
 * Note: Requires environment variables for DB and JWT.
 * Use @TestPropertySource to override with test values.
 */
@SpringBootTest
@TestPropertySource(properties = {
    "SUPABASE_JDBC_URL=jdbc:h2:mem:testdb;DB_CLOSE_DELAY=-1",
    "SUPABASE_DB_USERNAME=sa",
    "SUPABASE_DB_PASSWORD=",
    "JWT_SECRET=test-secret-min-32-chars-for-hmac-sha256-test",
    "AI_SERVICE_URL=http://localhost:9999"
})
class VereHireApplicationTests {

    @Test
    void contextLoads() {
        // Verifies the Spring context initializes without errors
    }
}
