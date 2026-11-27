package org.assayflux.rdms

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { RdmsBetaShell() }
    }
}

@Composable
private fun RdmsBetaShell() {
    MaterialTheme {
        Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
            Column(
                modifier = Modifier.fillMaxSize().padding(24.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                Text("RDMS", style = MaterialTheme.typography.headlineLarge)
                Text("Native Android beta", style = MaterialTheme.typography.titleMedium)
                Text("Offline-first research data management")
                Card(colors = CardDefaults.cardColors()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Foundation initialized", style = MaterialTheme.typography.titleMedium)
                        Text("This beta shell is the starting point for the native feature migration. No network permission is declared.")
                    }
                }
                Text("Feature modules, encrypted persistence, biometric unlock, migration, and backup/restore are staged for implementation and verification.")
            }
        }
    }
}
