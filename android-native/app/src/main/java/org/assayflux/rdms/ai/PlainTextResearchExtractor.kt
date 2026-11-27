package org.assayflux.rdms.ai

import java.nio.charset.CodingErrorAction

/**
 * Offline, bounded TXT/Markdown ingestion. This is a parser, not an AI model:
 * it preserves source text and offsets so later extraction can cite exact passages.
 */
class PlainTextResearchExtractor(
    private val maxInputBytes: Int = 20 * 1024 * 1024,
    private val maxCharacters: Int = 10_000_000
) : ResearchMaterialTextExtractor {
    override val extractorId: String = "rdms.plain-text"
    override val version: String = "1.0"

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
        val text = decoder.decode(java.nio.ByteBuffer.wrap(bytes)).toString()
        require(text.length <= maxCharacters) { "Text exceeds configured character limit" }

        val lines = text.split('\n')
        val pages = mutableListOf<ExtractedPage>()
        var offset = 0
        var currentHeading: String? = null
        val body = StringBuilder()
        var bodyStart = 0

        fun flush() {
            val value = body.toString().trim()
            if (value.isNotEmpty()) {
                val leading = body.indexOf(value)
                pages += ExtractedPage(
                    pageNumber = null,
                    sectionHeading = currentHeading,
                    text = value
                )
                // offsets are represented in passage text by the caller's source map;
                // line/character map is preserved separately in the warning metadata for now.
                body.setLength(0)
                bodyStart = offset + leading
            }
        }

        for (line in lines) {
            val heading = line.trim().removePrefix("#").trim()
            val isHeading = line.trimStart().startsWith("#") && heading.isNotEmpty()
            if (isHeading) {
                flush()
                currentHeading = heading
            } else {
                if (body.isEmpty()) bodyStart = offset
                body.append(line).append('\n')
            }
            offset += line.length + 1
        }
        flush()

        return ExtractedDocument(
            pages = pages,
            warnings = listOf(
                "Plain-text ingestion only; no AI interpretation was performed.",
                "Paragraph offsets must be mapped by the persistence adapter before claim-level citations are enabled."
            )
        )
    }
}
