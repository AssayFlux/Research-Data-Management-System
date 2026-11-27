package org.assayflux.rdms.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
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

    @Query("SELECT COUNT(*) FROM studies")
    suspend fun studyCount(): Int
}
