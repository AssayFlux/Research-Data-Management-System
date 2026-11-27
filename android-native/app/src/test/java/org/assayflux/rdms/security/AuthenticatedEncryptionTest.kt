package org.assayflux.rdms.security

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertThrows
import org.junit.Test
import javax.crypto.KeyGenerator

class AuthenticatedEncryptionTest {
    private fun key() = KeyGenerator.getInstance("AES").apply { init(256) }.generateKey()

    @Test fun roundTripPreservesPayload() {
        val source = "local research export".toByteArray()
        val k = key()
        val encrypted = AuthenticatedEncryption.encrypt(source, k)
        assertArrayEquals(source, AuthenticatedEncryption.decrypt(encrypted, k))
    }

    @Test fun tamperedEnvelopeIsRejected() {
        val k = key()
        val envelope = AuthenticatedEncryption.encrypt("payload".toByteArray(), k)
        envelope[envelope.lastIndex] = (envelope.last().toInt() xor 1).toByte()
        assertThrows(Exception::class.java) { AuthenticatedEncryption.decrypt(envelope, k) }
    }

    @Test fun truncatedEnvelopeIsRejected() {
        assertThrows(IllegalArgumentException::class.java) {
            AuthenticatedEncryption.decrypt(byteArrayOf(1, 2), key())
        }
    }
}
