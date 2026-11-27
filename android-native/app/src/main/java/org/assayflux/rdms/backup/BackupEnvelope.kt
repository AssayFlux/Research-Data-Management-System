package org.assayflux.rdms.backup

import org.assayflux.rdms.security.AuthenticatedEncryption
import javax.crypto.SecretKey

/**
 * Encryption wrapper for backup payloads. The payload should be a versioned archive
 * containing database export, attachment manifest, and hashes. This class does not
 * implement SAF/USB I/O or password-based cross-device key recovery.
 */
object BackupEnvelope {
    fun seal(archiveBytes: ByteArray, deviceKey: SecretKey): ByteArray =
        AuthenticatedEncryption.encrypt(archiveBytes, deviceKey)

    fun open(encryptedBytes: ByteArray, deviceKey: SecretKey): ByteArray =
        AuthenticatedEncryption.decrypt(encryptedBytes, deviceKey)
}
