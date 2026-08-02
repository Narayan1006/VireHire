package com.verehire.job;

/**
 * Pipeline job lifecycle states.
 *
 * PROCESSING  → Job created, Python AI pipeline is running (@Async thread)
 * COMPLETED   → Pipeline finished, all candidates saved to the database
 * FAILED      → Pipeline threw an exception; error_message column is populated
 *
 * Stored as TEXT in PostgreSQL (EnumType.STRING).
 * The DB CHECK constraint enforces the same values.
 */
public enum JobStatus {
    PROCESSING,
    COMPLETED,
    FAILED
}
