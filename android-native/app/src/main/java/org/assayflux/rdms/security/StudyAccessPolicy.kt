package org.assayflux.rdms.security

/**
 * Explicit assignment policy. Empty assignments intentionally grant no study access.
 * Callers must apply this policy at every repository/use-case boundary.
 */
data class StudyGrant(val userId: String, val studyId: String, val role: String)

object StudyAccessPolicy {
    fun canRead(userId: String, studyId: String, grants: Collection<StudyGrant>): Boolean =
        grants.any { it.userId == userId && it.studyId == studyId && it.role in setOf("OWNER", "RESEARCHER", "VIEWER") }

    fun canWrite(userId: String, studyId: String, grants: Collection<StudyGrant>): Boolean =
        grants.any { it.userId == userId && it.studyId == studyId && it.role in setOf("OWNER", "RESEARCHER") }

    fun canAdminister(userId: String, studyId: String, grants: Collection<StudyGrant>): Boolean =
        grants.any { it.userId == userId && it.studyId == studyId && it.role == "OWNER" }
}
