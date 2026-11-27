package org.assayflux.rdms.security

import android.content.Context
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity

/**
 * OS-mediated biometric authorization. The application never reads or stores biometric templates.
 * A recovery credential and key-rotation policy must be configured before production use.
 */
object LocalAuth {
    fun canAuthenticate(context: Context): Boolean =
        BiometricManager.from(context).canAuthenticate(
            BiometricManager.Authenticators.BIOMETRIC_STRONG or
                BiometricManager.Authenticators.DEVICE_CREDENTIAL
        ) == BiometricManager.BIOMETRIC_SUCCESS

    fun prompt(
        activity: FragmentActivity,
        onAuthorized: () -> Unit,
        onFailure: (String) -> Unit
    ) {
        val executor = ContextCompat.getMainExecutor(activity)
        val prompt = BiometricPrompt(
            activity,
            executor,
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    onAuthorized()
                }
                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    onFailure(errString.toString())
                }
                override fun onAuthenticationFailed() {
                    onFailure("Authentication was not recognized. Try again.")
                }
            }
        )
        val info = BiometricPrompt.PromptInfo.Builder()
            .setTitle("Unlock RDMS")
            .setSubtitle("Authorize access to locally stored research data")
            .setAllowedAuthenticators(
                BiometricManager.Authenticators.BIOMETRIC_STRONG or
                    BiometricManager.Authenticators.DEVICE_CREDENTIAL
            )
            .build()
        prompt.authenticate(info)
    }
}
