package org.assayflux.rdms.data

import android.content.Context
import org.assayflux.rdms.ai.ChromeCaptureResearchExtractor
import org.assayflux.rdms.ai.ResearchMaterialTextExtractor
import org.assayflux.rdms.ai.PlainTextResearchExtractor
import org.assayflux.rdms.security.AttachmentVault
import org.assayflux.rdms.security.DeviceKeyStore
import java.io.ByteArrayOutputStream
import java.io.File
import java.security.MessageDigest
import java.util.UUID

data class MaterialExtractionResult(
    val materialId: String,
    val passageCount: Int,
    val warnings: List<String>
)

/** Local-only extraction coordinator. AES-GCM is verified by reading decrypted data to EOF. */
class ResearchIntelligenceRepository(
    private val context: Context,
    private val dao: ResearchIntelligenceDao,
    private val plainTextExtractor: ResearchMaterialTextExtractor = PlainTextResearchExtractor(),
    private val chromeExtractor: ResearchMaterialTextExtractor = ChromeCaptureResearchExtractor()
) {
    suspend fun extractMaterial(materialId: String): MaterialExtractionResult {
        val material = dao.getMaterial(materialId) ?: error("Research material not found")
        dao.setExtractionState(materialId, "PROCESSING")
        try {
            val file = File(material.encryptedObjectPath)
            require(file.isFile && file.length() <= MAX_ENCRYPTED_BYTES) {
                "Encrypted research file is missing or exceeds the configured limit"
            }
            val plaintext = file.inputStream().use { encrypted ->
                AttachmentVault.decryptFrom(encrypted, DeviceKeyStore.getOrCreateAesKey())
                    .use { decrypted -> decrypted.readBounded(MAX_PLAINTEXT_BYTES) }
            }
            val extractor = when (material.mediaType) {
                "application/vnd.rdms.web-capture+json" -> chromeExtractor
                "text/plain", "text/markdown", "text/x-markdown" -> plainTextExtractor
                else -> error("No offline extractor is available for ${material.mediaType}; PDF/DOCX/OCR adapters are pending")
            }
            val document = extractor.extract(material.id, material.mediaType, plaintext)
            val passages = document.pages.map { page ->
                ResearchPassageEntity(
                    id = UUID.randomUUID().toString(),
                    materialId = material.id,
                    pageNumber = page.pageNumber,
                    sectionHeading = page.sectionHeading,
                    startOffset = page.startOffset,
                    endOffset = page.endOffset,
                    text = page.text,
                    textSha256 = sha256(page.text.toByteArray(Charsets.UTF_8))
                )
            }
            dao.saveExtraction(passages, emptyList(), emptyList())
            dao.setExtractionState(materialId, "EXTRACTED")
            return MaterialExtractionResult(materialId, passages.size, document.warnings)
        } catch (error: Throwable) {
            dao.setExtractionState(materialId, "FAILED")
            throw error
        }
    }

    private fun java.io.InputStream.readBounded(limit: Int): ByteArray {
        val output = ByteArrayOutputStream()
        val buffer = ByteArray(8192)
        var total = 0
        while (true) {
            val count = read(buffer)
            if (count < 0) break
            total += count
            require(total <= limit) { "Decrypted research material exceeds configured size limit" }
            output.write(buffer, 0, count)
        }
        return output.toByteArray()
    }

    private fun sha256(bytes: ByteArray): String =
        MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }

    private companion object {
        const val MAX_ENCRYPTED_BYTES = 110L * 1024 * 1024
        const val MAX_PLAINTEXT_BYTES = 20 * 1024 * 1024
    }
}
