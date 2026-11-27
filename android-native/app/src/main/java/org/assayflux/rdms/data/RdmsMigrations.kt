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


/** Adds the structured offline research workspace while preserving all v1/v2 data. */
val MIGRATION_2_3 = object : Migration(2, 3) {
    override fun migrate(db: SupportSQLiteDatabase) {
        db.execSQL("""
            CREATE TABLE IF NOT EXISTS research_parameters (
                id TEXT NOT NULL PRIMARY KEY, studyId TEXT NOT NULL, parameterKey TEXT NOT NULL,
                label TEXT NOT NULL, dataType TEXT NOT NULL, unit TEXT, category TEXT,
                referenceRangeJson TEXT, validationJson TEXT NOT NULL, isRequired INTEGER NOT NULL,
                isActive INTEGER NOT NULL, createdAtEpochMillis INTEGER NOT NULL,
                FOREIGN KEY(studyId) REFERENCES studies(id) ON UPDATE NO ACTION ON DELETE CASCADE
            )
        """.trimIndent())
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_parameters_studyId ON research_parameters(studyId)")
        db.execSQL("CREATE UNIQUE INDEX IF NOT EXISTS index_research_parameters_studyId_parameterKey ON research_parameters(studyId, parameterKey)")

        db.execSQL("""
            CREATE TABLE IF NOT EXISTS research_forms (
                id TEXT NOT NULL PRIMARY KEY, studyId TEXT NOT NULL, formKey TEXT NOT NULL,
                title TEXT NOT NULL, description TEXT NOT NULL, version INTEGER NOT NULL,
                status TEXT NOT NULL, createdAtEpochMillis INTEGER NOT NULL, updatedAtEpochMillis INTEGER NOT NULL,
                FOREIGN KEY(studyId) REFERENCES studies(id) ON UPDATE NO ACTION ON DELETE CASCADE
            )
        """.trimIndent())
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_forms_studyId ON research_forms(studyId)")
        db.execSQL("CREATE UNIQUE INDEX IF NOT EXISTS index_research_forms_studyId_formKey_version ON research_forms(studyId, formKey, version)")

        db.execSQL("""
            CREATE TABLE IF NOT EXISTS research_form_fields (
                id TEXT NOT NULL PRIMARY KEY, formId TEXT NOT NULL, parameterId TEXT,
                fieldKey TEXT NOT NULL, label TEXT NOT NULL, inputType TEXT NOT NULL,
                required INTEGER NOT NULL, validationJson TEXT NOT NULL, position INTEGER NOT NULL,
                FOREIGN KEY(formId) REFERENCES research_forms(id) ON UPDATE NO ACTION ON DELETE CASCADE,
                FOREIGN KEY(parameterId) REFERENCES research_parameters(id) ON UPDATE NO ACTION ON DELETE SET NULL
            )
        """.trimIndent())
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_form_fields_formId ON research_form_fields(formId)")
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_form_fields_parameterId ON research_form_fields(parameterId)")
        db.execSQL("CREATE UNIQUE INDEX IF NOT EXISTS index_research_form_fields_formId_fieldKey ON research_form_fields(formId, fieldKey)")

        db.execSQL("""
            CREATE TABLE IF NOT EXISTS research_visits (
                id TEXT NOT NULL PRIMARY KEY, studyId TEXT NOT NULL, participantId TEXT NOT NULL,
                visitCode TEXT NOT NULL, visitLabel TEXT NOT NULL, plannedAtEpochMillis INTEGER,
                completedAtEpochMillis INTEGER, status TEXT NOT NULL, notes TEXT NOT NULL,
                FOREIGN KEY(studyId) REFERENCES studies(id) ON UPDATE NO ACTION ON DELETE CASCADE,
                FOREIGN KEY(participantId) REFERENCES participants(id) ON UPDATE NO ACTION ON DELETE CASCADE
            )
        """.trimIndent())
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_visits_studyId ON research_visits(studyId)")
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_visits_participantId ON research_visits(participantId)")
        db.execSQL("CREATE UNIQUE INDEX IF NOT EXISTS index_research_visits_studyId_participantId_visitCode ON research_visits(studyId, participantId, visitCode)")

        db.execSQL("""
            CREATE TABLE IF NOT EXISTS research_records (
                id TEXT NOT NULL PRIMARY KEY, studyId TEXT NOT NULL, participantId TEXT NOT NULL,
                formId TEXT, visitId TEXT, recordStatus TEXT NOT NULL, isLocked INTEGER NOT NULL,
                createdAtEpochMillis INTEGER NOT NULL, updatedAtEpochMillis INTEGER NOT NULL, lockedAtEpochMillis INTEGER,
                FOREIGN KEY(studyId) REFERENCES studies(id) ON UPDATE NO ACTION ON DELETE CASCADE,
                FOREIGN KEY(participantId) REFERENCES participants(id) ON UPDATE NO ACTION ON DELETE CASCADE,
                FOREIGN KEY(formId) REFERENCES research_forms(id) ON UPDATE NO ACTION ON DELETE SET NULL,
                FOREIGN KEY(visitId) REFERENCES research_visits(id) ON UPDATE NO ACTION ON DELETE SET NULL
            )
        """.trimIndent())
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_records_studyId ON research_records(studyId)")
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_records_participantId ON research_records(participantId)")
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_records_formId ON research_records(formId)")
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_records_visitId ON research_records(visitId)")
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_records_updatedAtEpochMillis ON research_records(updatedAtEpochMillis)")

        db.execSQL("""
            CREATE TABLE IF NOT EXISTS research_record_values (
                id TEXT NOT NULL PRIMARY KEY, recordId TEXT NOT NULL, fieldId TEXT NOT NULL,
                valueText TEXT, valueNumber REAL, valueJson TEXT, missingReason TEXT, recordedAtEpochMillis INTEGER NOT NULL,
                FOREIGN KEY(recordId) REFERENCES research_records(id) ON UPDATE NO ACTION ON DELETE CASCADE,
                FOREIGN KEY(fieldId) REFERENCES research_form_fields(id) ON UPDATE NO ACTION ON DELETE CASCADE
            )
        """.trimIndent())
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_record_values_recordId ON research_record_values(recordId)")
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_record_values_fieldId ON research_record_values(fieldId)")
        db.execSQL("CREATE UNIQUE INDEX IF NOT EXISTS index_research_record_values_recordId_fieldId ON research_record_values(recordId, fieldId)")

        db.execSQL("""
            CREATE TABLE IF NOT EXISTS research_biospecimens (
                id TEXT NOT NULL PRIMARY KEY, studyId TEXT NOT NULL, participantId TEXT NOT NULL,
                visitId TEXT, specimenCode TEXT NOT NULL, specimenType TEXT NOT NULL,
                collectedAtEpochMillis INTEGER, storageLocation TEXT, status TEXT NOT NULL, notes TEXT NOT NULL,
                FOREIGN KEY(studyId) REFERENCES studies(id) ON UPDATE NO ACTION ON DELETE CASCADE,
                FOREIGN KEY(participantId) REFERENCES participants(id) ON UPDATE NO ACTION ON DELETE CASCADE,
                FOREIGN KEY(visitId) REFERENCES research_visits(id) ON UPDATE NO ACTION ON DELETE SET NULL
            )
        """.trimIndent())
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_biospecimens_studyId ON research_biospecimens(studyId)")
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_biospecimens_participantId ON research_biospecimens(participantId)")
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_biospecimens_visitId ON research_biospecimens(visitId)")
        db.execSQL("CREATE UNIQUE INDEX IF NOT EXISTS index_research_biospecimens_studyId_specimenCode ON research_biospecimens(studyId, specimenCode)")

        db.execSQL("""
            CREATE TABLE IF NOT EXISTS research_adverse_events (
                id TEXT NOT NULL PRIMARY KEY, studyId TEXT NOT NULL, participantId TEXT NOT NULL,
                eventCode TEXT NOT NULL, description TEXT NOT NULL, severity TEXT NOT NULL,
                relatedness TEXT NOT NULL, onsetAtEpochMillis INTEGER, outcome TEXT, status TEXT NOT NULL,
                createdAtEpochMillis INTEGER NOT NULL,
                FOREIGN KEY(studyId) REFERENCES studies(id) ON UPDATE NO ACTION ON DELETE CASCADE,
                FOREIGN KEY(participantId) REFERENCES participants(id) ON UPDATE NO ACTION ON DELETE CASCADE
            )
        """.trimIndent())
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_adverse_events_studyId ON research_adverse_events(studyId)")
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_adverse_events_participantId ON research_adverse_events(participantId)")
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_adverse_events_severity ON research_adverse_events(severity)")
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_adverse_events_status ON research_adverse_events(status)")

        db.execSQL("""
            CREATE TABLE IF NOT EXISTS research_quality_issues (
                id TEXT NOT NULL PRIMARY KEY, studyId TEXT NOT NULL, entityType TEXT NOT NULL,
                entityId TEXT NOT NULL, issueCode TEXT NOT NULL, description TEXT NOT NULL,
                severity TEXT NOT NULL, status TEXT NOT NULL, createdAtEpochMillis INTEGER NOT NULL,
                resolvedAtEpochMillis INTEGER,
                FOREIGN KEY(studyId) REFERENCES studies(id) ON UPDATE NO ACTION ON DELETE CASCADE
            )
        """.trimIndent())
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_quality_issues_studyId ON research_quality_issues(studyId)")
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_quality_issues_entityType ON research_quality_issues(entityType)")
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_quality_issues_entityId ON research_quality_issues(entityId)")
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_quality_issues_status ON research_quality_issues(status)")
        db.execSQL("CREATE INDEX IF NOT EXISTS index_research_quality_issues_severity ON research_quality_issues(severity)")

        db.execSQL("""
            CREATE TABLE IF NOT EXISTS study_assignments (
                id TEXT NOT NULL PRIMARY KEY, studyId TEXT NOT NULL, userId TEXT NOT NULL,
                role TEXT NOT NULL, assignedAtEpochMillis INTEGER NOT NULL,
                FOREIGN KEY(studyId) REFERENCES studies(id) ON UPDATE NO ACTION ON DELETE CASCADE
            )
        """.trimIndent())
        db.execSQL("CREATE INDEX IF NOT EXISTS index_study_assignments_studyId ON study_assignments(studyId)")
        db.execSQL("CREATE INDEX IF NOT EXISTS index_study_assignments_userId ON study_assignments(userId)")
        db.execSQL("CREATE UNIQUE INDEX IF NOT EXISTS index_study_assignments_studyId_userId ON study_assignments(studyId, userId)")
    }
}
