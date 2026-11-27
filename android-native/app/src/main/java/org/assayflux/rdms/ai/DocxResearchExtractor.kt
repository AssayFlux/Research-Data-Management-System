package org.assayflux.rdms.ai

import org.xmlpull.v1.XmlPullParser
import org.xmlpull.v1.XmlPullParserFactory
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.util.zip.ZipInputStream

/** Bounded, offline DOCX body-text extraction. Does not execute macros or external links. */
class DocxResearchExtractor(
    private val maxPackageBytes: Int = 20 * 1024 * 1024,
    private val maxDocumentXmlBytes: Int = 20 * 1024 * 1024,
    private val maxExpandedPackageBytes: Int = 40 * 1024 * 1024,
    private val maxCharacters: Int = 10_000_000
) : ResearchMaterialTextExtractor {
    override val extractorId: String = "rdms.docx"
    override val version: String = "1.0"

    override suspend fun extract(
        materialId: String,
        mediaType: String,
        bytes: ByteArray
    ): ExtractedDocument {
        require(mediaType == DOCX_MEDIA_TYPE) { "Unsupported media type for DOCX extractor" }
        require(bytes.size <= maxPackageBytes) { "DOCX package exceeds configured size limit" }

        var documentXml: ByteArray? = null
        var expandedTotal = 0
        ZipInputStream(ByteArrayInputStream(bytes)).use { zip ->
            while (true) {
                val entry = zip.nextEntry ?: break
                val isDocument = entry.name == "word/document.xml"
                if (isDocument) {
                    require(documentXml == null) { "DOCX contains duplicate document.xml entries" }
                }
                val output = if (isDocument) ByteArrayOutputStream() else null
                val buffer = ByteArray(8192)
                var entryTotal = 0
                while (true) {
                    val count = zip.read(buffer)
                    if (count < 0) break
                    entryTotal += count
                    expandedTotal += count
                    require(expandedTotal <= maxExpandedPackageBytes) {
                        "DOCX expands beyond configured package size limit"
                    }
                    if (isDocument) {
                        require(entryTotal <= maxDocumentXmlBytes) {
                            "DOCX document XML exceeds configured size limit"
                        }
                        output!!.write(buffer, 0, count)
                    }
                }
                if (isDocument) documentXml = output!!.toByteArray()
                zip.closeEntry()
            }
        }
        val xml = documentXml ?: error("DOCX main document part is missing")
        val paragraphs = parseParagraphs(xml)
        val pages = mutableListOf<ExtractedPage>()
        var offset = 0
        paragraphs.forEach { paragraph ->
            val value = paragraph.trim()
            if (value.isNotEmpty()) {
                require(offset + value.length <= maxCharacters) {
                    "DOCX extracted text exceeds configured character limit"
                }
                pages += ExtractedPage(
                    pageNumber = null,
                    sectionHeading = null,
                    startOffset = offset,
                    endOffset = offset + value.length,
                    text = value
                )
                offset += value.length + 1
            }
        }
        return ExtractedDocument(
            pages = pages,
            warnings = listOf(
                "DOCX body paragraphs extracted locally; tables, headers, footers, comments and footnotes may be omitted.",
                "Embedded objects, macros, hyperlinks and external relationships were not executed or followed.",
                "Offsets refer to normalized extracted paragraph text, not byte positions in the DOCX ZIP package."
            )
        )
    }

    private fun parseParagraphs(xml: ByteArray): List<String> {
        val factory = XmlPullParserFactory.newInstance()
        factory.isNamespaceAware = true
        val parser = factory.newPullParser()
        parser.setFeature(XmlPullParser.FEATURE_PROCESS_DOCDECL, false)
        parser.setInput(ByteArrayInputStream(xml), "UTF-8")
        val result = mutableListOf<String>()
        var paragraph = StringBuilder()
        var inParagraph = false
        var inText = false
        var total = 0
        while (parser.eventType != XmlPullParser.END_DOCUMENT) {
            when (parser.eventType) {
                XmlPullParser.START_TAG -> when (parser.name) {
                    "p" -> {
                        inParagraph = true
                        paragraph = StringBuilder()
                    }
                    "t" -> if (inParagraph) inText = true
                    "tab" -> if (inParagraph) paragraph.append('\t')
                    "br", "cr" -> if (inParagraph) paragraph.append(' ')
                }
                XmlPullParser.TEXT -> if (inParagraph && inText) {
                    paragraph.append(parser.text)
                    total += parser.text.length
                    require(total <= maxCharacters) {
                        "DOCX extracted text exceeds configured character limit"
                    }
                }
                XmlPullParser.END_TAG -> when (parser.name) {
                    "t" -> inText = false
                    "p" -> if (inParagraph) {
                        result += paragraph.toString()
                        inParagraph = false
                        inText = false
                    }
                }
            }
            parser.next()
        }
        return result
    }

    companion object {
        const val DOCX_MEDIA_TYPE =
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }
}
