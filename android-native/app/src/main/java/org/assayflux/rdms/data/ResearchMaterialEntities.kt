package org.assayflux.rdms.data

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "research_materials",
    indices = [Index(value = ["contentSha256"], unique = true), Index("importedAtEpochMillis")]
)
data class ResearchMaterialEntity(
    @PrimaryKey val id: String,
    val title: String,
    val authorsJson: String = "[]",
    val doi: String? = null,
    val pmid: String? = null,
    val publicationDate: String? = null,
    val mediaType: String,
    val encryptedObjectPath: String,
    val contentSha256: String,
    val licenseId: String? = null,
    val permissionState: String = "UNKNOWN",
    val parserVersion: String,
    val importedAtEpochMillis: Long,
    val extractionState: String = "PENDING"
)

@Entity(
    tableName = "research_passages",
    foreignKeys = [ForeignKey(
        entity = ResearchMaterialEntity::class,
        parentColumns = ["id"],
        childColumns = ["materialId"],
        onDelete = ForeignKey.CASCADE
    )],
    indices = [Index("materialId"), Index(value = ["materialId", "pageNumber", "startOffset"])]
)
data class ResearchPassageEntity(
    @PrimaryKey val id: String,
    val materialId: String,
    val pageNumber: Int?,
    val sectionHeading: String?,
    val startOffset: Int,
    val endOffset: Int,
    val text: String,
    val textSha256: String
)

@Entity(
    tableName = "research_claims",
    foreignKeys = [ForeignKey(
        entity = ResearchMaterialEntity::class,
        parentColumns = ["id"],
        childColumns = ["materialId"],
        onDelete = ForeignKey.CASCADE
    )],
    indices = [Index("materialId"), Index("reviewState"), Index("topicKey")]
)
data class ResearchClaimEntity(
    @PrimaryKey val id: String,
    val materialId: String,
    val claimText: String,
    val claimType: String,
    val topicKey: String?,
    val entityTagsJson: String = "[]",
    val evidenceClass: String,
    val uncertaintyText: String? = null,
    val reviewState: String = "UNREVIEWED",
    val extractionRunId: String,
    val createdAtEpochMillis: Long
)

@Entity(
    tableName = "claim_passage_links",
    primaryKeys = ["claimId", "passageId"],
    foreignKeys = [
        ForeignKey(
            entity = ResearchClaimEntity::class,
            parentColumns = ["id"],
            childColumns = ["claimId"],
            onDelete = ForeignKey.CASCADE
        ),
        ForeignKey(
            entity = ResearchPassageEntity::class,
            parentColumns = ["id"],
            childColumns = ["passageId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index("passageId")]
)
data class ClaimPassageLinkEntity(
    val claimId: String,
    val passageId: String,
    val supportType: String = "SUPPORTS"
)
