package org.assayflux.rdms.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Transaction
import kotlinx.coroutines.flow.Flow

@Dao
interface RdmsDao {
    @Query("SELECT * FROM studies ORDER BY updatedAtEpochMillis DESC")
    fun observeStudies(): Flow<List<StudyEntity>>

    @Query("SELECT * FROM participants WHERE studyId = :studyId ORDER BY createdAtEpochMillis DESC")
    fun observeParticipants(studyId: String): Flow<List<ParticipantEntity>>

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertStudy(study: StudyEntity)

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertParticipant(participant: ParticipantEntity)

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun appendAuditEvent(event: AuditEventEntity)

    @Transaction
    suspend fun createStudyWithAudit(study: StudyEntity, event: AuditEventEntity) {
        insertStudy(study)
        appendAuditEvent(event)
    }

    @Transaction
    suspend fun createParticipantWithAudit(participant: ParticipantEntity, event: AuditEventEntity) {
        insertParticipant(participant)
        appendAuditEvent(event)
    }

    @Query("UPDATE participants SET consentStatus = :status WHERE id = :participantId")
    suspend fun updateParticipantConsent(participantId: String, status: String)

    @Query("UPDATE studies SET status = :status, updatedAtEpochMillis = :updatedAt WHERE id = :studyId")
    suspend fun updateStudyStatus(studyId: String, status: String, updatedAt: Long)

    @Query("SELECT COUNT(*) FROM studies")
    suspend fun studyCount(): Int

    @Query("SELECT COUNT(*) FROM participants WHERE studyId = :studyId")
    suspend fun participantCount(studyId: String): Int

    @Query("UPDATE studies SET title = :title, description = :description, status = :status, updatedAtEpochMillis = :updatedAt WHERE id = :studyId")
    suspend fun updateStudy(studyId: String, title: String, description: String, status: String, updatedAt: Long)

    @Query("SELECT * FROM studies WHERE id = :studyId LIMIT 1")
    suspend fun getStudy(studyId: String): StudyEntity?
}
