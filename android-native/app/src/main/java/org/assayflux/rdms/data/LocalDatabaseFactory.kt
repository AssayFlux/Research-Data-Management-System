package org.assayflux.rdms.data

import android.content.Context
import androidx.room.Room
import net.sqlcipher.database.SQLiteDatabase
import net.sqlcipher.database.SupportFactory
import org.assayflux.rdms.security.DeviceKeyStore
import java.security.MessageDigest
import java.util.Base64

/**
 * SQLCipher-backed Room database.
 *
 * The Android Keystore AES key wraps a random SQLCipher passphrase. The wrapped
 * passphrase is stored in app-private preferences; the raw SQLCipher passphrase
 * exists only in memory during database open. Key rotation/recovery migration must
 * be completed before production use.
 */
object LocalDatabaseFactory {
    private const val PREFS = "rdms_key_material"
    private const val WRAPPED = "wrapped_sqlcipher_passphrase"

    fun create(context: Context): RdmsDatabase {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val wrappingKey = DeviceKeyStore.getOrCreateAesKey()
        val wrapped = prefs.getString(WRAPPED, null)
        val passphrase = if (wrapped == null) {
            val raw = ByteArray(32).also { java.security.SecureRandom().nextBytes(it) }
            val envelope = org.assayflux.rdms.security.AuthenticatedEncryption.encrypt(raw, wrappingKey)
            check(prefs.edit().putString(WRAPPED, Base64.getEncoder().encodeToString(envelope)).commit()) {
                "Could not persist encrypted database key"
            }
            raw
        } else {
            val envelope = Base64.getDecoder().decode(wrapped)
            org.assayflux.rdms.security.AuthenticatedEncryption.decrypt(envelope, wrappingKey)
        }
        val factory = SupportFactory(SQLiteDatabase.getBytes(passphrase))
        passphrase.fill(0)
        return Room.databaseBuilder(context, RdmsDatabase::class.java, "rdms-local.db")
            .openHelperFactory(factory)
            .build()
    }
}
