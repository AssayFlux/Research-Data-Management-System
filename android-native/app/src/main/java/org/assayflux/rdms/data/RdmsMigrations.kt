package org.assayflux.rdms.data

import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

/** Adds the research-literature evidence tables without destroying existing local study data. */
val MIGRATION_1_2 = object : Migration(1, 2) {
    override fun migrate(db: SupportSQLiteDatabase) {
        db.execSQL("""
            CREATE TABLE IF NOT EXISTS research_materials (
                id TEXT NOT NULL PRIMARY KEY,
                title TEXT NOT NULL,
                authorsJson TEXT NOT NULL,
                doi TEXT,
                pmid TEXT,
                publicationDate TEXT,
                mediaType TEXT NOT NULL,
                encryptedObjectPath TEXT NOT NULL,
                contentSha256 TEXT NOT NULL,
                licenseId TEXT,
                permissionState TEXT NOT NULL,
                parserVersion TEXT NOT NULL,
                importedAtEpochMillis INTEGER NOT NULL,
                extractionState TEXT NOT NULL
            )
        """.trimIndent())
        db.execSQL("CREATE UNIQUE INDEX IF NOT EXISTS index_research_materials_contentSha256 ON research_materials(contentSha256)")
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_materials_importedAtEpochMillis ON research_materials(importedAtEpochMillis)")

        db.execSQL("""
            CREATE TABLE IF NOT EXISTS research_passages (
                id TEXT NOT NULL PRIMARY KEY,
                materialId TEXT NOT NULL,
                pageNumber INTEGER,
                sectionHeading TEXT,
                startOffset INTEGER NOT NULL,
                endOffset INTEGER NOT NULL,
                text TEXT NOT NULL,
                textSha256 TEXT NOT NULL,
                FOREIGN KEY(materialId) REFERENCES research_materials(id) ON UPDATE NO ACTION ON DELETE CASCADE
            )
        """.trimIndent())
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_passages_materialId ON research_passages(materialId)")
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_passages_materialId_pageNumber_startOffset ON research_passages(materialId, pageNumber, startOffset)")

        db.execSQL("""
            CREATE TABLE IF NOT EXISTS research_claims (
                id TEXT NOT NULL PRIMARY KEY,
                materialId TEXT NOT NULL,
                claimText TEXT NOT NULL,
                claimType TEXT NOT NULL,
                topicKey TEXT,
                entityTagsJson TEXT NOT NULL,
                evidenceClass TEXT NOT NULL,
                uncertaintyText TEXT,
                reviewState TEXT NOT NULL,
                extractionRunId TEXT NOT NULL,
                createdAtEpochMillis INTEGER NOT NULL,
                FOREIGN KEY(materialId) REFERENCES research_materials(id) ON UPDATE NO ACTION ON DELETE CASCADE
            )
        """.trimIndent())
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_claims_materialId ON research_claims(materialId)")
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_claims_reviewState ON research_claims(reviewState)")
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_claims_topicKey ON research_claims(topicKey)")

        db.execSQL("""
            CREATE TABLE IF NOT EXISTS claim_passage_links (
                claimId TEXT NOT NULL,
                passageId TEXT NOT NULL,
                supportType TEXT NOT NULL,
                PRIMARY KEY(claimId, passageId),
                FOREIGN KEY(claimId) REFERENCES research_claims(id) ON UPDATE NO ACTION ON DELETE CASCADE,
                FOREIGN KEY(passageId) REFERENCES research_passages(id) ON UPDATE NO ACTION ON DELETE CASCADE
            )
        """.trimIndent())
        db.execSQL("CREATE INDEX IF NOT EXISTS index_claim_passage_links_passageId ON claim_passage_links(passageId)")
    }
}
