package org.assayflux.rdms.backup

import java.nio.ByteBuffer
import java.security.SecureRandom
import javax.crypto.AEADBadTagException
import javax.crypto.Cipher
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.PBEKeySpec
import javax.crypto.spec.SecretKeySpec

/**
 * Password-based portable backup envelope. Unlike the device Keystore key, this can
 * be opened on another device when the user supplies the same recovery password.
 *
 * Format: RDMB | version | PBKDF2 iteration count | salt(16) | nonce(12) | AES-GCM ciphertext.
 * Callers must clear their password char array after use. The archive itself still needs
 * to be created/validated by the backup service before this envelope is used.
 */
object PortableBackupCrypto {
    private val magic = byteArrayOf(0x52, 0x44, 0x4D, 0x42)
    private const val VERSION: Byte = 1
    private const val ITERATIONS = 310_000
    private const val SALT_BYTES = 16
    private const val NONCE_BYTES = 12
    private const val TAG_BITS = 128
    private const val MAX_PAYLOAD_BYTES = 512 * 1024 * 1024

    fun seal(payload: ByteArray, password: CharArray): ByteArray {
        require(payload.size <= MAX_PAYLOAD_BYTES) { "Backup payload exceeds size limit" }
        require(password.size >= 12) { "Backup password must contain at least 12 characters" }
        val salt = ByteArray(SALT_BYTES).also(SecureRandom()::nextBytes)
        val nonce = ByteArray(NONCE_BYTES).also(SecureRandom()::nextBytes)
        val header = ByteBuffer.allocate(magic.size + 1 + 4 + SALT_BYTES + NONCE_BYTES)
            .put(magic).put(VERSION).putInt(ITERATIONS).put(salt).put(nonce).array()
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, deriveKey(password, salt), GCMParameterSpec(TAG_BITS, nonce))
        cipher.updateAAD(header)
        return header + cipher.doFinal(payload)
    }

    fun open(envelope: ByteArray, password: CharArray): ByteArray {
        val headerSize = magic.size + 1 + 4 + SALT_BYTES + NONCE_BYTES
        require(envelope.size >= headerSize + TAG_BITS / 8) { "Backup envelope is truncated" }
        require(envelope.size <= MAX_PAYLOAD_BYTES + headerSize + TAG_BITS / 8) {
            "Backup envelope exceeds size limit"
        }
        val header = envelope.copyOfRange(0, headerSize)
        val input = ByteBuffer.wrap(header)
        val actualMagic = ByteArray(magic.size).also(input::get)
        require(actualMagic.contentEquals(magic)) { "Invalid backup envelope" }
        require(input.get() == VERSION) { "Unsupported backup version" }
        val iterations = input.int
        require(iterations in 100_000..1_000_000) { "Unsupported backup KDF parameters" }
        val salt = ByteArray(SALT_BYTES).also(input::get)
        val nonce = ByteArray(NONCE_BYTES).also(input::get)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, deriveKey(password, salt, iterations), GCMParameterSpec(TAG_BITS, nonce))
        cipher.updateAAD(header)
        return try {
            cipher.doFinal(envelope, headerSize, envelope.size - headerSize)
        } catch (error: AEADBadTagException) {
            throw SecurityException("Backup password is incorrect or the file has been modified", error)
        }
    }

    private fun deriveKey(password: CharArray, salt: ByteArray, iterations: Int = ITERATIONS): SecretKeySpec {
        val spec = PBEKeySpec(password, salt, iterations, 256)
        return try {
            val bytes = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
                .generateSecret(spec).encoded
            SecretKeySpec(bytes, "AES").also { bytes.fill(0) }
        } finally {
            spec.clearPassword()
        }
    }
}
