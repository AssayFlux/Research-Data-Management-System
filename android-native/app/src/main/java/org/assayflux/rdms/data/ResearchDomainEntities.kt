package org.assayflux.rdms.data

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "research_parameters",
    foreignKeys = [ForeignKey(entity = StudyEntity::class, parentColumns = ["id"], childColumns = ["studyId"], onDelete = ForeignKey.CASCADE)],
    indices = [Index("studyId"), Index(value = ["studyId", "parameterKey"], unique = true)]
)
data class ResearchParameterEntity(
    @PrimaryKey val id: String,
    val studyId: String,
    val parameterKey: String,
    val label: String,
    val dataType: String,
    val unit: String?,
    val category: String?,
    val referenceRangeJson: String?,
    val validationJson: String,
    val isRequired: Boolean,
    val isActive: Boolean,
    val createdAtEpochMillis: Long
)

@Entity(
    tableName = "research_forms",
    foreignKeys = [ForeignKey(entity = StudyEntity::class, parentColumns = ["id"], childColumns = ["studyId"], onDelete = ForeignKey.CASCADE)],
    indices = [Index("studyId"), Index(value = ["studyId", "formKey", "version"], unique = true)]
)
data class ResearchFormEntity(
    @PrimaryKey val id: String,
    val studyId: String,
    val formKey: String,
    val title: String,
    val description: String,
    val version: Int,
    val status: String,
    val createdAtEpochMillis: Long,
    val updatedAtEpochMillis: Long
)

@Entity(
    tableName = "research_form_fields",
    foreignKeys = [
        ForeignKey(entity = ResearchFormEntity::class, parentColumns = ["id"], childColumns = ["formId"], onDelete = ForeignKey.CASCADE),
        ForeignKey(entity = ResearchParameterEntity::class, parentColumns = ["id"], childColumns = ["parameterId"], onDelete = ForeignKey.SET_NULL)
    ],
    indices = [Index("formId"), Index("parameterId"), Index(value = ["formId", "fieldKey"], unique = true)]
)
data class ResearchFormFieldEntity(
    @PrimaryKey val id: String,
    val formId: String,
    val parameterId: String?,
    val fieldKey: String,
    val label: String,
    val inputType: String,
    val required: Boolean,
    val validationJson: String,
    val position: Int
)

@Entity(
    tableName = "research_visits",
    foreignKeys = [
        ForeignKey(entity = StudyEntity::class, parentColumns = ["id"], childColumns = ["studyId"], onDelete = ForeignKey.CASCADE),
        ForeignKey(entity = ParticipantEntity::class, parentColumns = ["id"], childColumns = ["participantId"], onDelete = ForeignKey.CASCADE)
    ],
    indices = [Index("studyId"), Index("participantId"), Index(value = ["studyId", "participantId", "visitCode"], unique = true)]
)
data class ResearchVisitEntity(
    @PrimaryKey val id: String,
    val studyId: String,
    val participantId: String,
    val visitCode: String,
    val visitLabel: String,
    val plannedAtEpochMillis: Long?,
    val completedAtEpochMillis: Long?,
    val status: String,
    val notes: String
)

@Entity(
    tableName = "research_records",
    foreignKeys = [
        ForeignKey(entity = StudyEntity::class, parentColumns = ["id"], childColumns = ["studyId"], onDelete = ForeignKey.CASCADE),
        ForeignKey(entity = ParticipantEntity::class, parentColumns = ["id"], childColumns = ["participantId"], onDelete = ForeignKey.CASCADE),
        ForeignKey(entity = ResearchFormEntity::class, parentColumns = ["id"], childColumns = ["formId"], onDelete = ForeignKey.SET_NULL),
        ForeignKey(entity = ResearchVisitEntity::class, parentColumns = ["id"], childColumns = ["visitId"], onDelete = ForeignKey.SET_NULL)
    ],
    indices = [Index("studyId"), Index("participantId"), Index("formId"), Index("visitId"), Index("updatedAtEpochMillis")]
)
data class ResearchRecordEntity(
    @PrimaryKey val id: String,
    val studyId: String,
    val participantId: String,
    val formId: String?,
    val visitId: String?,
    val recordStatus: String,
    val isLocked: Boolean,
    val createdAtEpochMillis: Long,
    val updatedAtEpochMillis: Long,
    val lockedAtEpochMillis: Long?
)

@Entity(
    tableName = "research_record_values",
    foreignKeys = [
        ForeignKey(entity = ResearchRecordEntity::class, parentColumns = ["id"], childColumns = ["recordId"], onDelete = ForeignKey.CASCADE),
        ForeignKey(entity = ResearchFormFieldEntity::class, parentColumns = ["id"], childColumns = ["fieldId"], onDelete = ForeignKey.CASCADE)
    ],
    indices = [Index("recordId"), Index("fieldId"), Index(value = ["recordId", "fieldId"], unique = true)]
)
data class ResearchRecordValueEntity(
    @PrimaryKey val id: String,
    val recordId: String,
    val fieldId: String,
    val valueText: String?,
    val valueNumber: Double?,
    val valueJson: String?,
    val missingReason: String?,
    val recordedAtEpochMillis: Long
)

@Entity(
    tableName = "research_biospecimens",
    foreignKeys = [
        ForeignKey(entity = StudyEntity::class, parentColumns = ["id"], childColumns = ["studyId"], onDelete = ForeignKey.CASCADE),
        ForeignKey(entity = ParticipantEntity::class, parentColumns = ["id"], childColumns = ["participantId"], onDelete = ForeignKey.CASCADE),
        ForeignKey(entity = ResearchVisitEntity::class, parentColumns = ["id"], childColumns = ["visitId"], onDelete = ForeignKey.SET_NULL)
    ],
    indices = [Index("studyId"), Index("participantId"), Index("visitId"), Index(value = ["studyId", "specimenCode"], unique = true)]
)
data class ResearchBiospecimenEntity(
    @PrimaryKey val id: String,
    val studyId: String,
    val participantId: String,
    val visitId: String?,
    val specimenCode: String,
    val specimenType: String,
    val collectedAtEpochMillis: Long?,
    val storageLocation: String?,
    val status: String,
    val notes: String
)

@Entity(
    tableName = "research_adverse_events",
    foreignKeys = [
        ForeignKey(entity = StudyEntity::class, parentColumns = ["id"], childColumns = ["studyId"], onDelete = ForeignKey.CASCADE),
        ForeignKey(entity = ParticipantEntity::class, parentColumns = ["id"], childColumns = ["participantId"], onDelete = ForeignKey.CASCADE)
    ],
    indices = [Index("studyId"), Index("participantId"), Index("severity"), Index("status")]
)
data class ResearchAdverseEventEntity(
    @PrimaryKey val id: String,
    val studyId: String,
    val participantId: String,
    val eventCode: String,
    val description: String,
    val severity: String,
    val relatedness: String,
    val onsetAtEpochMillis: Long?,
    val outcome: String?,
    val status: String,
    val createdAtEpochMillis: Long
)

@Entity(
    tableName = "research_quality_issues",
    foreignKeys = [ForeignKey(entity = StudyEntity::class, parentColumns = ["id"], childColumns = ["studyId"], onDelete = ForeignKey.CASCADE)],
    indices = [Index("studyId"), Index("entityType"), Index("entityId"), Index("status"), Index("severity")]
)
data class ResearchQualityIssueEntity(
    @PrimaryKey val id: String,
    val studyId: String,
    val entityType: String,
    val entityId: String,
    val issueCode: String,
    val description: String,
    val severity: String,
    val status: String,
    val createdAtEpochMillis: Long,
    val resolvedAtEpochMillis: Long?
)

@Entity(
    tableName = "study_assignments",
    foreignKeys = [ForeignKey(entity = StudyEntity::class, parentColumns = ["id"], childColumns = ["studyId"], onDelete = ForeignKey.CASCADE)],
    indices = [Index("studyId"), Index("userId"), Index(value = ["studyId", "userId"], unique = true)]
)
data class StudyAssignmentEntity(
    @PrimaryKey val id: String,
    val studyId: String,
    val userId: String,
    val role: String,
    val assignedAtEpochMillis: Long
)
