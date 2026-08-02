# =============================================================================
# VereHire AI — Spring Boot Dockerfile (Multi-stage)
# =============================================================================

# Stage 1: Build — compile the JAR
FROM maven:3.9-eclipse-temurin-21-alpine AS builder

WORKDIR /app

# Copy pom.xml first to leverage Docker layer caching for dependencies.
# Dependencies are re-downloaded only when pom.xml changes.
COPY pom.xml .
RUN mvn dependency:go-offline --no-transfer-progress -B

# Copy source code and build
COPY src ./src
RUN mvn clean package -DskipTests --no-transfer-progress -B

# =============================================================================
# Stage 2: Runtime — minimal JRE image
FROM eclipse-temurin:21-jre-alpine

LABEL maintainer="VereHire AI"
LABEL version="2.0.0"
LABEL description="VereHire Spring Boot Backend API"

WORKDIR /app

# Create non-root user for security
RUN addgroup -S spring && adduser -S spring -G spring

# Copy the fat JAR from builder
COPY --from=builder /app/target/verehire-api-*.jar app.jar

# Change ownership to non-root user
RUN chown spring:spring app.jar

USER spring

EXPOSE 8080

# JVM tuning for containers: respect container memory limits
ENTRYPOINT ["java", \
    "-XX:+UseContainerSupport", \
    "-XX:MaxRAMPercentage=75.0", \
    "-Djava.security.egd=file:/dev/./urandom", \
    "-jar", "app.jar"]
