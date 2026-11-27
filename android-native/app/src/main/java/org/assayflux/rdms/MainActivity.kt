package org.assayflux.rdms

import android.os.Bundle
import android.view.WindowManager
import androidx.activity.compose.setContent
import androidx.fragment.app.FragmentActivity
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import org.assayflux.rdms.security.LocalAuth
import org.assayflux.rdms.ui.RdmsApp
import org.assayflux.rdms.ui.RdmsTheme

class MainActivity : FragmentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE)
        setContent { RdmsTheme { RdmsBetaShell() } }
    }
}

@Composable
private fun RdmsBetaShell() {
    var unlocked by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("Unlock to access locally stored research data.") }
    val activity = LocalContext.current as? FragmentActivity
    MaterialTheme {
        Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
            Column(
                modifier = Modifier.fillMaxSize().padding(24.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                Text("RDMS", style = MaterialTheme.typography.headlineLarge)
                Text("Native Android beta", style = MaterialTheme.typography.titleMedium)
                if (!unlocked) {
                    Text(message)
                    Button(onClick = {
                        if (activity == null) {
                            message = "Authentication host is unavailable."
                        } else if (!LocalAuth.canAuthenticate(activity)) {
                            message = "Set up a secure device lock or biometric method in Android settings."
                        } else {
                            LocalAuth.prompt(activity, { unlocked = true }, { message = it })
                        }
                    }) { Text("Unlock with biometrics / device credential") }
                } else {
                    RdmsApp()
                }
            }
        }
    }
}
