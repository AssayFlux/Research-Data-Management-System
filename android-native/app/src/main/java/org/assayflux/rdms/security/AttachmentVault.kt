package org.assayflux.rdms.security

import java.io.InputStream
import java.io.OutputStream
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.CipherInputStream
import javax.crypto.CipherOutputStream
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Streaming AES-GCM attachment format. Header: RDMA | version | 12-byte nonce.
 * Consumers must read to EOF to force GCM tag verification before accepting an attachment.
 */
object AttachmentVault {
    private val magic = byteArrayOf(0x52, 0x44, 0x4D, 0x41)
    private const val VERSION: Byte = 1
    private const val NONCE_SIZE = 12

    fun encryptTo(input: InputStream, destination: OutputStream, key: SecretKey) {
        val nonce = ByteArray(NONCE_SIZE).also { SecureRandom().nextBytes(it) }
        destination.write(magic)
        destination.write(VERSION.toInt())
        destination.write(nonce)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key, GCMParameterSpec(128, nonce))
        cipher.updateAAD(magic + byteArrayOf(VERSION))
        CipherOutputStream(destination, cipher).use { encrypted ->
            input.copyTo(encrypted)
        }
    }

    fun decryptFrom(source: InputStream, key: SecretKey): InputStream {
        val header = ByteArray(magic.size + 1 + NONCE_SIZE)
        var offset = 0
        while (offset < header.size) {
            val count = source.read(header, offset, header.size - offset)
            require(count > 0) { "Encrypted attachment header is truncated" }
            offset += count
        }
        require(header.copyOfRange(0, magic.size).contentEquals(magic)) { "Invalid attachment format" }
        require(header[magic.size] == VERSION) { "Unsupported attachment version" }
        val nonce = header.copyOfRange(magic.size + 1, header.size)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(128, nonce))
        cipher.updateAAD(magic + byteArrayOf(VERSION))
        return CipherInputStream(source, cipher)
    }
}
