package org.assayflux.rdms.ai

import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class PlainTextResearchExtractorTest {
    @Test
    fun parsesHeadingsAndPreservesOffsets(): Unit {
        runBlocking {
            val source = "# Results\nGroup A improved.\n\n# Limitations\nSmall sample.\n"
            val result = PlainTextResearchExtractor().extract(
                "material-1", "text/markdown", source.toByteArray()
            )
            assertEquals(2, result.pages.size)
            assertEquals("Results", result.pages[0].sectionHeading)
            assertEquals("Group A improved.", result.pages[0].text)
            assertEquals(
                source.substring(result.pages[0].startOffset, result.pages[0].endOffset),
                result.pages[0].text
            )
            assertEquals("Limitations", result.pages[1].sectionHeading)
            assertEquals(
                source.substring(result.pages[1].startOffset, result.pages[1].endOffset),
                result.pages[1].text
            )
        }
    }

    @Test
    fun rejectsUnsupportedMediaType(): Unit {
        assertThrows(IllegalArgumentException::class.java) {
            runBlocking {
                PlainTextResearchExtractor().extract("m1", "application/pdf", byteArrayOf())
            }
        }
    }

    @Test
    fun rejectsOversizedInput(): Unit {
        val parser = PlainTextResearchExtractor(maxInputBytes = 2)
        assertThrows(IllegalArgumentException::class.java) {
            runBlocking { parser.extract("m1", "text/plain", "long".toByteArray()) }
        }
    }

    @Test
    fun rejectsMalformedUtf8(): Unit {
        assertThrows(Exception::class.java) {
            runBlocking {
                PlainTextResearchExtractor().extract(
                    "m1", "text/plain", byteArrayOf(0xC3.toByte(), 0x28)
                )
            }
        }
    }
}
