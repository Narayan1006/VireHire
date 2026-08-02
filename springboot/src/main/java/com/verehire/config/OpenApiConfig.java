package com.verehire.config;

import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
import io.swagger.v3.oas.models.servers.Server;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.List;

/**
 * OpenAPI 3 / Swagger configuration.
 *
 * Accessible at: /swagger-ui.html and /api-docs (configured in application.yml)
 *
 * Adds JWT Bearer authentication scheme so all protected endpoints
 * can be tested directly from the Swagger UI.
 */
@Configuration
public class OpenApiConfig {

    @Value("${app.version:2.0.0}")
    private String appVersion;

    @Bean
    public OpenAPI verehireOpenApi() {
        final String securitySchemeName = "bearerAuth";

        return new OpenAPI()
            .info(new Info()
                .title("VeriHire AI API")
                .description(
                    "**VeriHire AI** — Candidate Ranking & Hiring Intelligence Platform\n\n" +
                    "A 3-layer AI pipeline combining semantic retrieval, evidence verification, " +
                    "and LLM reasoning to automatically rank engineering candidates.\n\n" +
                    "## Architecture\n" +
                    "- **Spring Boot** (this service): Auth, storage, API gateway\n" +
                    "- **Python AI Service** (internal): ChromaDB + LLM pipeline\n" +
                    "- **Supabase PostgreSQL**: Persistent storage\n\n" +
                    "## Authentication\n" +
                    "All protected endpoints require a **Bearer JWT** in the Authorization header.\n" +
                    "Obtain a token via `POST /api/auth/login` or `POST /api/auth/signup`."
                )
                .version("v" + appVersion)
                .contact(new Contact()
                    .name("VeriHire Engineering")
                    .url("https://github.com/")
                )
                .license(new License()
                    .name("Proprietary")
                )
            )
            .servers(List.of(
                new Server().url("http://localhost:8080").description("Local Development"),
                new Server().url("https://api.verehire.ai").description("Production")
            ))
            .addSecurityItem(new SecurityRequirement().addList(securitySchemeName))
            .components(new Components()
                .addSecuritySchemes(securitySchemeName,
                    new SecurityScheme()
                        .name(securitySchemeName)
                        .type(SecurityScheme.Type.HTTP)
                        .scheme("bearer")
                        .bearerFormat("JWT")
                        .description(
                            "Enter the JWT obtained from POST /api/auth/login.\n\n" +
                            "Example: `eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOi...`"
                        )
                )
            );
    }
}
