package org.assayflux.rdms.ai

/**
 * Evidence-first contracts for the offline research-material pipeline.
 * Extractors return passage-linked candidates; they do not assert scientific truth.
 */
enum class ResearchEvidenceClass {
    OBSERVED_IN_SOURCE, AUTHOR_REPORTED, DERIVED_FROM_SOURCE, AI_INTERPRETATION, HYPOTHESIS
}

enum class ClaimReviewState { UNREVIEWED, ACCEPTED, REJECTED, NEEDS_REVIEW, DISPUTED }

data class SourcePassage(
    val pageNumber: Int?,
    val sectionHeading: String?,
    val startOffset: Int,
    val endOffset: Int,
    val text: String
)

data class ExtractedResearchClaim(
    val text: String,
    val claimType: String,
    val topicKey: String?,
    val entityTags: List<String>,
    val evidenceClass: ResearchEvidenceClass,
    val supportingPassages: List<SourcePassage>,
    val uncertainty: String? = null
)

data class ResearchBrief(
    val materialId: String,
    val title: String,
    val objective: String?,
    val studyDesign: String?,
    val populationOrModel: String?,
    val sampleSize: String?,
    val methods: List<String>,
    val keyFindings: List<ExtractedResearchClaim>,
    val limitations: List<ExtractedResearchClaim>,
    val keyTerms: List<String>,
    val unansweredQuestions: List<String>,
    val generatedAtEpochMillis: Long,
    val extractorId: String,
    val extractorVersion: String,
    val humanReviewed: Boolean = false
)

interface ResearchMaterialTextExtractor {
    val extractorId: String
    val version: String
    suspend fun extract(materialId: String, mediaType: String, bytes: ByteArray): ExtractedDocument
}

data class ExtractedDocument(
    val pages: List<ExtractedPage>,
    val warnings: List<String>
)

data class ExtractedPage(
    val pageNumber: Int?,
    val sectionHeading: String?,
    val startOffset: Int,
    val endOffset: Int,
    val text: String
)

interface EvidenceGroundedBriefGenerator {
    val generatorId: String
    val version: String
    suspend fun generate(materialId: String, pages: List<ExtractedPage>): ResearchBrief
}

/** Safe default: no hosted model or network dependency is implied by this contract. */
interface OfflineResearchIntelligence {
    suspend fun buildBrief(materialId: String): ResearchBrief
}
