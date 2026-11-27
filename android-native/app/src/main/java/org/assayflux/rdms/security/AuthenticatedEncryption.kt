package org.assayflux.rdms.security

import java.nio.ByteBuffer
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Authenticated AES-GCM envelope for small payloads and backup chunks.
 * Format: magic(4) | version(1) | nonce(12) | ciphertext+tag.
 * Callers must stream/chunk large attachments rather than loading them wholly into memory.
 */
object AuthenticatedEncryption {
    private val magic = byteArrayOf(0x52, 0x44, 0x4D, 0x53) // RDMS
    private const val VERSION: Byte = 1
    private const val NONCE_BYTES = 12
    private const val TAG_BITS = 128

    fun encrypt(plaintext: ByteArray, key: SecretKey): ByteArray {
        val nonce = ByteArray(NONCE_BYTES).also { SecureRandom().nextBytes(it) }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key, GCMParameterSpec(TAG_BITS, nonce))
        cipher.updateAAD(magic + byteArrayOf(VERSION))
        val ciphertext = cipher.doFinal(plaintext)
        return ByteBuffer.allocate(magic.size + 1 + nonce.size + ciphertext.size)
            .put(magic).put(VERSION).put(nonce).put(ciphertext).array()
    }

    fun decrypt(envelope: ByteArray, key: SecretKey): ByteArray {
        require(envelope.size >= magic.size + 1 + NONCE_BYTES + 16) { "Encrypted data is truncated" }
        val buffer = ByteBuffer.wrap(envelope)
        val actualMagic = ByteArray(magic.size).also(buffer::get)
        require(actualMagic.contentEquals(magic)) { "Not an RDMS encrypted file" }
        val version = buffer.get()
        require(version == VERSION) { "Unsupported encrypted file version: $version" }
        val nonce = ByteArray(NONCE_BYTES).also(buffer::get)
        val ciphertext = ByteArray(buffer.remaining()).also(buffer::get)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(TAG_BITS, nonce))
        cipher.updateAAD(magic + byteArrayOf(VERSION))
        return cipher.doFinal(ciphertext) // Throws on tampering or wrong key.
    }
}
