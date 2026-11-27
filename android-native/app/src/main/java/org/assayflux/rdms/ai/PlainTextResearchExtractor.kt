package org.assayflux.rdms.ai

import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction

/**
 * Offline, bounded TXT/Markdown ingestion. It preserves exact UTF-16 source offsets.
 * This parser does not perform AI interpretation or PDF/OCR extraction.
 */
class PlainTextResearchExtractor(
    private val maxInputBytes: Int = 20 * 1024 * 1024,
    private val maxCharacters: Int = 10_000_000
) : ResearchMaterialTextExtractor {
    override val extractorId: String = "rdms.plain-text"
    override val version: String = "1.1"

    override suspend fun extract(
        materialId: String,
        mediaType: String,
        bytes: ByteArray
    ): ExtractedDocument {
        require(materialId.isNotBlank()) { "materialId is required" }
        require(mediaType in setOf("text/plain", "text/markdown", "text/x-markdown")) {
            "Unsupported media type for plain-text extractor"
        }
        require(bytes.size <= maxInputBytes) { "Input exceeds configured size limit" }

        val decoder = Charsets.UTF_8.newDecoder()
            .onMalformedInput(CodingErrorAction.REPORT)
            .onUnmappableCharacter(CodingErrorAction.REPORT)
        val text = decoder.decode(ByteBuffer.wrap(bytes)).toString()
        require(text.length <= maxCharacters) { "Text exceeds configured character limit" }

        val pages = mutableListOf<ExtractedPage>()
        val body = StringBuilder()
        var offset = 0
        var bodyStart = 0
        var currentHeading: String? = null

        fun flush() {
            val raw = body.toString()
            val value = raw.trim()
            if (value.isNotEmpty()) {
                val leading = raw.indexOf(value)
                val start = bodyStart + leading
                pages += ExtractedPage(
                    pageNumber = null,
                    sectionHeading = currentHeading,
                    startOffset = start,
                    endOffset = start + value.length,
                    text = value
                )
            }
            body.setLength(0)
        }

        for (lineWithEnding in text.splitToSequence('\n')) {
            val line = lineWithEnding.removeSuffix("\r")
            val trimmed = line.trim()
            val heading = trimmed.dropWhile { it == '#' }.trim()
            val isHeading = trimmed.startsWith("#") && heading.isNotEmpty()
            if (isHeading) {
                flush()
                currentHeading = heading
            } else {
                if (body.isEmpty()) bodyStart = offset
                body.append(lineWithEnding).append('\n')
            }
            offset += lineWithEnding.length + 1
        }
        flush()

        return ExtractedDocument(
            pages = pages,
            warnings = listOf(
                "Plain-text ingestion only; no AI interpretation was performed.",
                "Offsets use Kotlin UTF-16 character indexing in the original decoded text."
            )
        )
    }
}
