package org.assayflux.rdms.data

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import org.assayflux.rdms.security.AttachmentVault
import org.assayflux.rdms.security.DeviceKeyStore
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

/**
 * Imports a user-selected SAF document into app-private encrypted storage.
 * It does not upload, index, parse, or send document bytes to a provider.
 */
class ResearchMaterialImporter(private val context: Context) {
    fun import(uri: Uri): ImportedResearchFile {
        val resolver = context.contentResolver
        val mediaType = resolver.getType(uri) ?: "application/octet-stream"
        val displayName = resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)
            ?.use { cursor ->
                if (cursor.moveToFirst()) cursor.getString(0) else null
            } ?: "research-material"

        val directory = File(context.filesDir, "research-materials").apply { mkdirs() }
        check(directory.isDirectory) { "Cannot create private research-material directory" }
        val id = UUID.randomUUID().toString()
        val temporary = File(directory, ".$id.tmp")
        val destination = File(directory, "$id.rdma")
        val digest = MessageDigest.getInstance("SHA-256")

        try {
            val input = resolver.openInputStream(uri) ?: error("Cannot open selected document")
            input.use { source ->
                DigestInputStream(source, digest).use { digesting ->
                    FileOutputStream(temporary).use { output ->
                        AttachmentVault.encryptTo(digesting, output, DeviceKeyStore.getOrCreateAesKey())
                        output.fd.sync()
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
}
