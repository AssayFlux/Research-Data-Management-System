package org.assayflux.rdms.ai

import org.json.JSONObject
import java.nio.charset.CodingErrorAction

/**
 * Turns the plain-text fields of a locally imported Chrome capture into source passages.
 * It does not fetch the URL, execute page scripts, follow instructions in the page, or
 * claim that any passage is scientifically verified.
 */
class ChromeCaptureResearchExtractor(
    private val textExtractor: PlainTextResearchExtractor = PlainTextResearchExtractor(),
    private val maxCaptureBytes: Int = 20 * 1024 * 1024,
    private val maxTextCharacters: Int = 10_000_000
) : ResearchMaterialTextExtractor {
    override val extractorId: String = "rdms.chrome-capture"
    override val version: String = "1.0"

    override suspend fun extract(
        materialId: String,
        mediaType: String,
        bytes: ByteArray
    ): ExtractedDocument {
        require(mediaType == "application/vnd.rdms.web-capture+json") {
            "Unsupported media type for Chrome capture extractor"
        }
        require(bytes.size <= maxCaptureBytes) { "Chrome capture exceeds configured size limit" }
        val decoder = Charsets.UTF_8.newDecoder()
            .onMalformedInput(CodingErrorAction.REPORT)
            .onUnmappableCharacter(CodingErrorAction.REPORT)
        val json = JSONObject(decoder.decode(java.nio.ByteBuffer.wrap(bytes)).toString())
        require(json.optString("schema") == "rdms.web-capture.v1") {
            "Unsupported RDMS browser-capture schema"
        }
        val source = json.optJSONObject("source") ?: error("Capture has no source metadata")
        val url = source.optString("url")
        require(url.startsWith("https://") || url.startsWith("http://")) {
            "Capture source URL must use HTTP or HTTPS"
        }
        val pageText = json.optString("pageText").trim()
        val selectedText = json.optString("selectedText").trim()
        require(pageText.isNotBlank()) { "Capture contains no readable page text" }
        require(pageText.length + selectedText.length <= maxTextCharacters) {
            "Captured text exceeds configured character limit"
        }

        val combined = buildString {
            append("# Captured webpage text\n\n")
            append(pageText)
            if (selectedText.isNotBlank() && selectedText != pageText) {
                append("\n\n# Researcher-selected text\n\n")
                append(selectedText)
            }
        }
        val extracted = textExtractor.extract(
            materialId = materialId,
            mediaType = "text/plain",
            bytes = combined.toByteArray(Charsets.UTF_8)
        )
        return extracted.copy(
            warnings = extracted.warnings + listOf(
                "Source URL: $url",
                "Passage offsets refer to the captured text package, not the live webpage DOM.",
                "The capture may omit figures, tables, supplementary files and dynamically loaded content."
            )
        )
    }
}
