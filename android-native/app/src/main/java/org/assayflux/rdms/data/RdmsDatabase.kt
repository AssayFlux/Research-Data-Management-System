package org.assayflux.rdms.data

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [StudyEntity::class, ParticipantEntity::class, AuditEventEntity::class],
    version = 1,
    exportSchema = true
)
abstract class RdmsDatabase : RoomDatabase() {
    abstract fun rdmsDao(): RdmsDao
}
