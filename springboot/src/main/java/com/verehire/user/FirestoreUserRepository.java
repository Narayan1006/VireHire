package com.verehire.user;

import com.google.api.core.ApiFuture;
import com.google.cloud.firestore.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Repository;

import java.util.*;
import java.util.concurrent.ExecutionException;

/**
 * Firestore-backed Repository for User accounts.
 * Completely replaces JPA / SQL / H2 databases.
 * Stores user documents in the 'users' Firestore collection.
 */
@Repository
public class FirestoreUserRepository {

    private static final Logger log = LoggerFactory.getLogger(FirestoreUserRepository.class);
    private final Firestore firestore;

    public FirestoreUserRepository(Firestore firestore) {
        this.firestore = firestore;
    }

    public boolean existsByEmail(String email) {
        try {
            ApiFuture<QuerySnapshot> query = firestore.collection("users")
                    .whereEqualTo("email", email.toLowerCase().trim())
                    .get();
            return !query.get().isEmpty();
        } catch (Exception e) {
            log.error("Failed to check if email exists in Firestore: {}", e.getMessage(), e);
            throw new RuntimeException("Firestore query failed", e);
        }
    }

    public Optional<UserEntity> findByEmail(String email) {
        try {
            ApiFuture<QuerySnapshot> query = firestore.collection("users")
                    .whereEqualTo("email", email.toLowerCase().trim())
                    .get();
            List<QueryDocumentSnapshot> docs = query.get().getDocuments();
            if (docs.isEmpty()) {
                return Optional.empty();
            }

            QueryDocumentSnapshot doc = docs.get(0);
            return Optional.of(mapDocToUser(doc));
        } catch (Exception e) {
            log.error("Failed to find user by email in Firestore: {}", e.getMessage(), e);
            return Optional.empty();
        }
    }

    public Optional<UserEntity> findById(UUID id) {
        try {
            DocumentSnapshot doc = firestore.collection("users").document(id.toString()).get().get();
            if (!doc.exists()) {
                return Optional.empty();
            }
            return Optional.of(mapDocToUser(doc));
        } catch (Exception e) {
            log.error("Failed to find user by ID in Firestore: {}", e.getMessage(), e);
            return Optional.empty();
        }
    }

    public UserEntity save(UserEntity user) {
        try {
            if (user.getId() == null) {
                user.setId(UUID.randomUUID());
            }

            Map<String, Object> data = new HashMap<>();
            data.put("id", user.getId().toString());
            data.put("email", user.getEmail().toLowerCase().trim());
            data.put("password_hash", user.getPasswordHash());
            data.put("created_at", FieldValue.serverTimestamp());

            firestore.collection("users").document(user.getId().toString()).set(data).get();
            log.info("Saved user document to Firestore: {}", user.getEmail());
            return user;
        } catch (Exception e) {
            log.error("Failed to save user to Firestore: {}", e.getMessage(), e);
            throw new RuntimeException("Failed to save user to Firestore", e);
        }
    }

    private UserEntity mapDocToUser(DocumentSnapshot doc) {
        UUID id = UUID.fromString(doc.getId());
        String email = doc.getString("email");
        String passwordHash = doc.getString("password_hash");
        return UserEntity.builder()
                .id(id)
                .email(email)
                .passwordHash(passwordHash)
                .build();
    }
}
