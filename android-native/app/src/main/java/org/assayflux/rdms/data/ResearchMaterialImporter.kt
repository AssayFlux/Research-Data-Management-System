package org.assayflux.rdms.data

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import org.assayflux.rdms.security.AttachmentVault
import org.assayflux.rdms.security.DeviceKeyStore
import java.io.FilterInputStream
import java.io.FilterOutputStream
import java.io.File
import java.io.FileOutputStream
import java.security.DigestInputStream
import java.security.MessageDigest
import java.util.UUID

data class ImportedResearchFile(
    val id: String,
    val displayName: String,
    val mediaType: String,
    val encryptedFile: File,
    val sha256: String,
    val importedAtEpochMillis: Long
)

/** User-selected SAF import into app-private encrypted storage. No network or upload. */
class ResearchMaterialImporter(
    private val context: Context,
    private val maxBytes: Long = 100L * 1024 * 1024
) {
    fun import(uri: Uri): ImportedResearchFile {
        val resolver = context.contentResolver
        val mediaType = resolver.getType(uri) ?: "application/octet-stream"
        val displayName = resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)
            ?.use { cursor -> if (cursor.moveToFirst()) cursor.getString(0) else null }
            ?: "research-material"

        val directory = File(context.filesDir, "research-materials").apply { mkdirs() }
        check(directory.isDirectory) { "Cannot create private research-material directory" }
        val id = UUID.randomUUID().toString()
        val temporary = File(directory, ".$id.tmp")
        val destination = File(directory, "$id.rdma")
        val digest = MessageDigest.getInstance("SHA-256")

        try {
            val input = resolver.openInputStream(uri) ?: error("Cannot open selected document")
            input.use { source ->
                val bounded = SizeLimitedInputStream(source, maxBytes)
                DigestInputStream(bounded, digest).use { digesting ->
                    FileOutputStream(temporary).use { fileOutput ->
                        // CipherOutputStream must close to write the GCM tag. This wrapper
                        // allows that close while keeping the file descriptor open for fsync.
                        val nonClosing = object : FilterOutputStream(fileOutput) {
                            override fun close() { flush() }
                        }
                        AttachmentVault.encryptTo(
                            digesting, nonClosing, DeviceKeyStore.getOrCreateAesKey()
                        )
                        fileOutput.fd.sync()
                    }
                }
            }
            check(temporary.renameTo(destination)) { "Cannot publish encrypted document" }
            return ImportedResearchFile(
                id = id,
                displayName = displayName,
                mediaType = mediaType,
                encryptedFile = destination,
                sha256 = digest.digest().joinToString("") { "%02x".format(it) },
                importedAtEpochMillis = System.currentTimeMillis()
            )
        } catch (error: Throwable) {
            temporary.delete()
            destination.delete()
            throw error
        }
    }

    private class SizeLimitedInputStream(
        input: java.io.InputStream,
        private val limit: Long
    ) : FilterInputStream(input) {
        private var count = 0L

        override fun read(): Int {
            val value = super.read()
            if (value >= 0) {
                count++
                check(count <= limit) { "Research document exceeds configured import size limit" }
            }
            return value
        }

        override fun read(buffer: ByteArray, offset: Int, length: Int): Int {
            val value = super.read(buffer, offset, length)
            if (value > 0) {
                count += value
                check(count <= limit) { "Research document exceeds configured import size limit" }
            }
            return value
        }
    }
}
