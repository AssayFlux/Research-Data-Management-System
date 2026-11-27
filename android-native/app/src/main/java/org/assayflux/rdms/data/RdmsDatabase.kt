package org.assayflux.rdms.data

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [
        StudyEntity::class,
        ParticipantEntity::class,
        AuditEventEntity::class,
        ResearchMaterialEntity::class,
        ResearchPassageEntity::class,
        ResearchClaimEntity::class,
        ClaimPassageLinkEntity::class,
        ResearchParameterEntity::class,
        ResearchFormEntity::class,
        ResearchFormFieldEntity::class,
        ResearchVisitEntity::class,
        ResearchRecordEntity::class,
        ResearchRecordValueEntity::class,
        ResearchBiospecimenEntity::class,
        ResearchAdverseEventEntity::class,
        ResearchQualityIssueEntity::class,
        StudyAssignmentEntity::class
    ],
    version = 3,
    exportSchema = true
)
abstract class RdmsDatabase : RoomDatabase() {
    abstract fun rdmsDao(): RdmsDao
    abstract fun researchIntelligenceDao(): ResearchIntelligenceDao
}
