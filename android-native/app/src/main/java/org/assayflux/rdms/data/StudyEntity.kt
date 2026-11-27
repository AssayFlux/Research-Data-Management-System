package org.assayflux.rdms.data

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(tableName = "studies", indices = [Index(value = ["studyCode"], unique = true)])
data class StudyEntity(
    @PrimaryKey val id: String,
    val studyCode: String,
    val title: String,
    val description: String = "",
    val status: String = "ACTIVE",
    val createdAtEpochMillis: Long,
    val updatedAtEpochMillis: Long
)

@Entity(tableName = "participants", indices = [Index("studyId"), Index("participantCode")])
data class ParticipantEntity(
    @PrimaryKey val id: String,
    val studyId: String,
    val participantCode: String,
    val displayLabel: String,
    val consentStatus: String,
    val createdAtEpochMillis: Long
)

@Entity(tableName = "audit_events", indices = [Index("occurredAtEpochMillis"), Index("entityId")])
data class AuditEventEntity(
    @PrimaryKey val id: String,
    val actorId: String,
    val action: String,
    val entityType: String,
    val entityId: String,
    val occurredAtEpochMillis: Long,
    val detailsJson: String = "{}"
)
