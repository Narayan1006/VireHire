package com.verehire.config;

import com.google.auth.oauth2.GoogleCredentials;
import com.google.cloud.firestore.Firestore;
import com.google.firebase.FirebaseApp;
import com.google.firebase.FirebaseOptions;
import com.google.firebase.cloud.FirestoreClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.io.ByteArrayInputStream;
import java.io.FileInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

/**
 * Initializes Firebase App and provides a Firestore client Bean for Spring Boot.
 *
 * Supports two credential loading modes:
 * 1. FIREBASE_CREDENTIALS_JSON environment variable containing raw JSON string.
 * 2. GOOGLE_APPLICATION_CREDENTIALS path to serviceAccountKey.json.
 * 3. Default Application Credentials if neither is explicitly passed.
 */
@Configuration
public class FirebaseConfig {

    private static final Logger log = LoggerFactory.getLogger(FirebaseConfig.class);

    @Value("${firebase.credentials.json:}")
    private String firebaseCredentialsJson;

    @Value("${firebase.credentials.path:}")
    private String firebaseCredentialsPath;

    @Bean
    public Firestore firestore() {
        try {
            if (FirebaseApp.getApps().isEmpty()) {
                InputStream serviceAccount = null;

                if (firebaseCredentialsJson != null && !firebaseCredentialsJson.isBlank()) {
                    log.info("Initializing Firebase from raw JSON environment variable");
                    serviceAccount = new ByteArrayInputStream(firebaseCredentialsJson.getBytes(StandardCharsets.UTF_8));
                } else if (firebaseCredentialsPath != null && !firebaseCredentialsPath.isBlank()) {
                    log.info("Initializing Firebase from file path: {}", firebaseCredentialsPath);
                    serviceAccount = new FileInputStream(firebaseCredentialsPath);
                } else {
                    log.info("Initializing Firebase with default application credentials");
                }

                FirebaseOptions.Builder optionsBuilder = FirebaseOptions.builder();
                if (serviceAccount != null) {
                    optionsBuilder.setCredentials(GoogleCredentials.fromStream(serviceAccount));
                } else {
                    optionsBuilder.setCredentials(GoogleCredentials.getApplicationDefault());
                }

                FirebaseApp.initializeApp(optionsBuilder.build());
                log.info("Firebase Application successfully initialized");
            }

            return FirestoreClient.getFirestore();
        } catch (Exception e) {
            log.error("Failed to initialize Firebase Admin SDK / Firestore: {}", e.getMessage(), e);
            throw new IllegalStateException("Could not initialize Firebase/Firestore connection", e);
        }
    }
}
