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
        ClaimPassageLinkEntity::class
    ],
    version = 2,
    exportSchema = true
)
abstract class RdmsDatabase : RoomDatabase() {
    abstract fun rdmsDao(): RdmsDao
    abstract fun researchIntelligenceDao(): ResearchIntelligenceDao
}
