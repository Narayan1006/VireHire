package com.verehire.user;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

/**
 * Spring Data JPA repository for {@link UserEntity}.
 *
 * Used by AuthService for login (findByEmail) and by JwtAuthFilter
 * for principal loading (findById).
 */
@Repository
public interface UserRepository extends JpaRepository<UserEntity, UUID> {

    /**
     * Find a user by their email address (case-sensitive).
     * Used during login to retrieve the user and verify BCrypt hash.
     */
    Optional<UserEntity> findByEmail(String email);

    /**
     * Check if an email is already registered.
     * Used during signup to enforce unique email constraint at the app layer
     * before hitting the database unique constraint.
     */
    boolean existsByEmail(String email);
}
