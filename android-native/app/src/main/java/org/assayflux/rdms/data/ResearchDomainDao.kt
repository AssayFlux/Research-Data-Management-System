package org.assayflux.rdms.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Transaction
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface ResearchDomainDao {
    @Query("SELECT * FROM research_parameters WHERE studyId = :studyId ORDER BY label")
    fun observeParameters(studyId: String): Flow<List<ResearchParameterEntity>>

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertParameter(parameter: ResearchParameterEntity)

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun appendAuditEvent(event: AuditEventEntity)

    @Transaction
    suspend fun createFormWithFieldsAndAudit(
        form: ResearchFormEntity,
        fields: List<ResearchFormFieldEntity>,
        event: AuditEventEntity
    ) {
        insertForm(form)
        if (fields.isNotEmpty()) insertFormFields(fields)
        appendAuditEvent(event)
    }

    @Transaction
    suspend fun createParameterWithAudit(parameter: ResearchParameterEntity, event: AuditEventEntity) {
        insertParameter(parameter)
        appendAuditEvent(event)
    }

    @Update
    suspend fun updateParameter(parameter: ResearchParameterEntity)

    @Query("SELECT * FROM research_forms WHERE studyId = :studyId ORDER BY title, version DESC")
    fun observeForms(studyId: String): Flow<List<ResearchFormEntity>>

    @Query("SELECT * FROM research_form_fields WHERE formId = :formId ORDER BY position")
    fun observeFormFields(formId: String): Flow<List<ResearchFormFieldEntity>>

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertForm(form: ResearchFormEntity)

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertFormFields(fields: List<ResearchFormFieldEntity>)

    @Transaction
    suspend fun createFormWithFields(form: ResearchFormEntity, fields: List<ResearchFormFieldEntity>) {
        insertForm(form)
        if (fields.isNotEmpty()) insertFormFields(fields)
    }

    @Query("SELECT * FROM research_visits WHERE participantId = :participantId ORDER BY plannedAtEpochMillis")
    fun observeVisits(participantId: String): Flow<List<ResearchVisitEntity>>

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertVisit(visit: ResearchVisitEntity)

    @Update
    suspend fun updateVisit(visit: ResearchVisitEntity)

    @Query("SELECT * FROM research_records WHERE participantId = :participantId ORDER BY updatedAtEpochMillis DESC")
    fun observeRecords(participantId: String): Flow<List<ResearchRecordEntity>>

    @Query("SELECT * FROM research_record_values WHERE recordId = :recordId ORDER BY fieldId")
    fun observeRecordValues(recordId: String): Flow<List<ResearchRecordValueEntity>>

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertRecord(record: ResearchRecordEntity)

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertRecordValues(values: List<ResearchRecordValueEntity>)

    @Transaction
    suspend fun createRecordWithValuesAndAudit(
        record: ResearchRecordEntity,
        values: List<ResearchRecordValueEntity>,
        event: AuditEventEntity
    ) {
        insertRecord(record)
        if (values.isNotEmpty()) insertRecordValues(values)
        appendAuditEvent(event)
    }

    @Transaction
    suspend fun lockRecordWithAudit(recordId: String, lockedAt: Long, event: AuditEventEntity) {
        check(lockRecord(recordId, lockedAt) == 1) { "Record is already locked or no longer exists" }
        appendAuditEvent(event)
    }

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveRecordValue(value: ResearchRecordValueEntity)

    @Query("UPDATE research_records SET isLocked = 1, lockedAtEpochMillis = :lockedAt, updatedAtEpochMillis = :lockedAt WHERE id = :recordId AND isLocked = 0")
    suspend fun lockRecord(recordId: String, lockedAt: Long): Int

    @Query("SELECT * FROM research_biospecimens WHERE studyId = :studyId ORDER BY collectedAtEpochMillis DESC")
    fun observeBiospecimens(studyId: String): Flow<List<ResearchBiospecimenEntity>>

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertBiospecimen(specimen: ResearchBiospecimenEntity)

    @Query("SELECT * FROM research_adverse_events WHERE studyId = :studyId ORDER BY createdAtEpochMillis DESC")
    fun observeAdverseEvents(studyId: String): Flow<List<ResearchAdverseEventEntity>>

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertAdverseEvent(event: ResearchAdverseEventEntity)

    @Query("SELECT * FROM research_quality_issues WHERE studyId = :studyId ORDER BY createdAtEpochMillis DESC")
    fun observeQualityIssues(studyId: String): Flow<List<ResearchQualityIssueEntity>>

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertQualityIssue(issue: ResearchQualityIssueEntity)

    @Query("UPDATE research_quality_issues SET status = :status, resolvedAtEpochMillis = :resolvedAt WHERE id = :issueId")
    suspend fun updateQualityIssueStatus(issueId: String, status: String, resolvedAt: Long?)

    @Query("SELECT * FROM study_assignments WHERE studyId = :studyId ORDER BY userId")
    fun observeStudyAssignments(studyId: String): Flow<List<StudyAssignmentEntity>>

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertStudyAssignment(assignment: StudyAssignmentEntity)

    @Query("SELECT role FROM study_assignments WHERE studyId = :studyId AND userId = :userId LIMIT 1")
    suspend fun roleForUser(studyId: String, userId: String): String?
}
