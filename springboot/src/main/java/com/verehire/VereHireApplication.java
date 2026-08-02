package com.verehire;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

/**
 * VereHire AI — Spring Boot Application Entry Point
 *
 * Architecture:
 *   React Frontend → Spring Boot (this service) → Python AI Service
 *                                               → Supabase PostgreSQL
 *
 * Spring Boot is the single owner of:
 *   - Authentication (Spring Security + JWT)
 *   - Database (JPA / Hibernate → Supabase PostgreSQL)
 *   - Business logic (jobs, candidates, stats, export)
 *   - AI pipeline orchestration (calls Python via HTTP)
 *
 * Python AI Service is a stateless AI engine:
 *   - Receives: job description + CSV bytes
 *   - Returns:  structured JSON rankings
 *   - Writes:   nothing (database is Spring Boot's responsibility)
 *
 * @version 2.0.0
 */
@SpringBootApplication
@EnableAsync
public class VereHireApplication {

    public static void main(String[] args) {
        SpringApplication.run(VereHireApplication.class, args);
    }
}
