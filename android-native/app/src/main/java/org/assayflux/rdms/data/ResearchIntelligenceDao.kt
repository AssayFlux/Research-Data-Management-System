package org.assayflux.rdms.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Transaction
import kotlinx.coroutines.flow.Flow

@Dao
interface ResearchIntelligenceDao {
    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertMaterial(material: ResearchMaterialEntity)

    @Query("SELECT * FROM research_materials WHERE id = :materialId LIMIT 1")
    suspend fun getMaterial(materialId: String): ResearchMaterialEntity?

    @Query("UPDATE research_materials SET extractionState = :state WHERE id = :materialId")
    suspend fun setExtractionState(materialId: String, state: String)

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertPassages(passages: List<ResearchPassageEntity>)

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertClaims(claims: List<ResearchClaimEntity>)

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertClaimPassageLinks(links: List<ClaimPassageLinkEntity>)

    @Query("SELECT * FROM research_materials ORDER BY importedAtEpochMillis DESC")
    fun observeMaterials(): Flow<List<ResearchMaterialEntity>>

    @Query("SELECT * FROM research_claims WHERE materialId = :materialId ORDER BY createdAtEpochMillis")
    fun observeClaims(materialId: String): Flow<List<ResearchClaimEntity>>

    @Query("""
        SELECT p.* FROM research_passages p
        INNER JOIN claim_passage_links l ON l.passageId = p.id
        WHERE l.claimId = :claimId
        ORDER BY p.pageNumber, p.startOffset
    """)
    suspend fun passagesSupportingClaim(claimId: String): List<ResearchPassageEntity>

    @Query("UPDATE research_claims SET reviewState = :state WHERE id = :claimId")
    suspend fun setClaimReviewState(claimId: String, state: String)

    @Transaction
    suspend fun saveExtraction(
        passages: List<ResearchPassageEntity>,
        claims: List<ResearchClaimEntity>,
        links: List<ClaimPassageLinkEntity>
    ) {
        insertPassages(passages)
        insertClaims(claims)
        insertClaimPassageLinks(links)
    }
}
