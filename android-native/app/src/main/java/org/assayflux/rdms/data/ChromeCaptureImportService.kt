package org.assayflux.rdms.data

import android.content.Context
import android.net.Uri
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.InputStream

data class ChromeCaptureImportResult(
    val materialId: String,
    val title: String,
    val sourceUrl: String,
    val pageTextCharacters: Int,
    val selectedTextCharacters: Int
)

/**
 * Validates a user-selected RDMS Chrome capture and catalogs the encrypted original.
 * This deliberately does not run AI, fetch the URL, or trust page text as instructions.
 */
class ChromeCaptureImportService(
    private val context: Context,
    private val dao: ResearchIntelligenceDao,
    private val fileImporter: ResearchMaterialImporter = ResearchMaterialImporter(context),
    private val maxJsonBytes: Int = 20 * 1024 * 1024,
    private val maxTextCharacters: Int = 10_000_000
) {
    suspend fun import(uri: Uri): ChromeCaptureImportResult {
        val payload = context.contentResolver.openInputStream(uri)?.use { it.readBounded(maxJsonBytes) }
            ?: error("Cannot read selected RDMS capture")
        val json = JSONObject(payload.toString(Charsets.UTF_8))
        require(json.optString("schema") == "rdms.web-capture.v1") {
            "Unsupported RDMS browser-capture schema"
        }

        val source = json.optJSONObject("source") ?: error("Capture has no source metadata")
        val sourceUrl = source.optString("url").trim()
        require(sourceUrl.startsWith("https://") || sourceUrl.startsWith("http://")) {
            "Capture source must be an HTTP or HTTPS URL"
        }
        val title = source.optString("title").trim().ifBlank { "Untitled web research capture" }
        val pageText = json.optString("pageText")
        val selectedText = json.optString("selectedText")
        require(pageText.isNotBlank()) { "Capture contains no readable page text" }
        require(pageText.length <= maxTextCharacters && selectedText.length <= maxTextCharacters) {
            "Captured text exceeds the configured size limit"
        }

        val imported = fileImporter.import(uri)
        try {
            val authors = JSONArray()
            source.optString("authors").takeIf { it.isNotBlank() }?.let(authors::put)
            val entity = ResearchMaterialEntity(
                id = imported.id,
                title = title,
                authorsJson = authors.toString(),
                doi = source.optString("doi").takeIf { it.isNotBlank() },
                publicationDate = source.optString("publishedDate").takeIf { it.isNotBlank() },
                mediaType = "application/vnd.rdms.web-capture+json",
                encryptedObjectPath = imported.encryptedFile.absolutePath,
                contentSha256 = imported.sha256,
                parserVersion = "rdms.web-capture.v1",
                importedAtEpochMillis = imported.importedAtEpochMillis
            )
            dao.insertMaterial(entity)
        } catch (error: Throwable) {
            imported.encryptedFile.delete()
            throw error
        }

        return ChromeCaptureImportResult(
            materialId = imported.id,
            title = title,
            sourceUrl = sourceUrl,
            pageTextCharacters = pageText.length,
            selectedTextCharacters = selectedText.length
        )
    }

    private fun InputStream.readBounded(limit: Int): ByteArray {
        val output = ByteArrayOutputStream()
        val buffer = ByteArray(8192)
        var total = 0
        while (true) {
            val count = read(buffer)
            if (count < 0) break
            total += count
            require(total <= limit) { "Capture file exceeds the configured size limit" }
            output.write(buffer, 0, count)
        }
        return output.toByteArray()
    }
}
