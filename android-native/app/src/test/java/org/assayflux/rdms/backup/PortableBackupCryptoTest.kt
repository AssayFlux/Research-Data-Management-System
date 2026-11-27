package org.assayflux.rdms.backup

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class PortableBackupCryptoTest {
    @Test
    fun encryptsAndDecryptsAcrossIndependentCalls(): Unit {
        val password = "correct horse battery staple".toCharArray()
        val original = "RDMS portable backup test".toByteArray()
        val envelope = PortableBackupCrypto.seal(original, password)
        val restored = PortableBackupCrypto.open(envelope, password)
        assertArrayEquals(original, restored)
        password.fill('\u0000')
    }

    @Test
    fun rejectsWrongPasswordAndTampering(): Unit {
        val envelope = PortableBackupCrypto.seal(
            "private research data".toByteArray(),
            "correct horse battery staple".toCharArray()
        )
        assertThrows(SecurityException::class.java) {
            PortableBackupCrypto.open(envelope, "incorrect password".toCharArray())
        }
        val changed = envelope.copyOf().also { it[it.lastIndex] = (it.last().toInt() xor 1).toByte() }
        assertThrows(SecurityException::class.java) {
            PortableBackupCrypto.open(changed, "correct horse battery staple".toCharArray())
        }
    }

    @Test
    fun rejectsShortPassword(): Unit {
        assertThrows(IllegalArgumentException::class.java) {
            PortableBackupCrypto.seal(byteArrayOf(1), "short".toCharArray())
        }
    }
}
