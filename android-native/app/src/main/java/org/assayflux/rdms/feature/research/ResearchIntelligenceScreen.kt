package org.assayflux.rdms.feature.research

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.assayflux.rdms.data.ChromeCaptureImportService
import org.assayflux.rdms.data.LocalDatabaseFactory
import org.assayflux.rdms.data.ResearchIntelligenceRepository
import org.assayflux.rdms.data.ResearchMaterialEntity
import org.assayflux.rdms.data.ResearchMaterialImporter

/** Offline research-material inbox. Import and extraction run locally on the device. */
@Composable
fun ResearchIntelligenceScreen() {
    val context = LocalContext.current
    val database = remember(context) { LocalDatabaseFactory.create(context) }
    val dao = remember(database) { database.researchIntelligenceDao() }
    val materials by dao.observeMaterials().collectAsState(initial = emptyList())
    val scope = rememberCoroutineScope()
    var status by remember { mutableStateOf("Files stay on this device. No web request or cloud upload is made.") }

    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            scope.launch {
                status = "Importing selected file into encrypted local storage…"
                try {
                    val result = withContext(Dispatchers.IO) {
                        val mediaType = context.contentResolver.getType(uri) ?: "application/octet-stream"
                        if (mediaType == "application/json" || mediaType == "text/json") {
                            ChromeCaptureImportService(context, dao).import(uri)
                        } else {
                            val imported = ResearchMaterialImporter(context).import(uri)
                            dao.insertMaterial(
                                ResearchMaterialEntity(
                                    id = imported.id,
                                    title = imported.displayName,
                                    mediaType = imported.mediaType,
                                    encryptedObjectPath = imported.encryptedFile.absolutePath,
                                    contentSha256 = imported.sha256,
                                    parserVersion = "pending",
                                    importedAtEpochMillis = imported.importedAtEpochMillis
                                )
                            )
                            null
                        }
                    }
                    status = if (result != null) {
                        "Captured “${result.title}”. Select it below to extract source passages."
                    } else {
                        "File imported and encrypted. Select it below to extract supported text."
                    }
                } catch (error: Throwable) {
                    status = "Import failed: ${error.message ?: "unknown error"}"
                }
            }
        }
    }

    Column(
        Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("Research Intelligence", style = MaterialTheme.typography.headlineMedium)
        Text("Collect papers and produce source-linked reading material without uploading research data.")
        Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(status, style = MaterialTheme.typography.bodySmall)
                Button(onClick = { picker.launch(arrayOf("*/*")) }) {
                    Text("Import paper or Chrome capture")
                }
            }
        }
        Text("Your research library", style = MaterialTheme.typography.titleMedium)
        if (materials.isEmpty()) {
            Text("No research materials imported yet.", style = MaterialTheme.typography.bodyMedium)
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(materials, key = { it.id }) { material ->
                    Card(
                        modifier = Modifier.fillMaxWidth().clickable {
                            scope.launch {
                                status = "Extracting passages from ${material.title}…"
                                try {
                                    val result = withContext(Dispatchers.IO) {
                                        ResearchIntelligenceRepository(context, dao)
                                            .extractMaterial(material.id)
                                    }
                                    status = "Extracted ${result.passageCount} source passages. " +
                                        result.warnings.joinToString(" ")
                                } catch (error: Throwable) {
                                    status = "Extraction unavailable: ${error.message ?: "unknown error"}"
                                }
                            }
                        },
                        colors = CardDefaults.cardColors()
                    ) {
                        Row(
                            Modifier.fillMaxWidth().padding(12.dp),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                                Text(material.title, style = MaterialTheme.typography.titleSmall)
                                Text(material.mediaType, style = MaterialTheme.typography.labelSmall)
                                Text("Status: ${material.extractionState}", style = MaterialTheme.typography.bodySmall)
                            }
                            OutlinedButton(onClick = {
                                scope.launch {
                                    status = "Extracting passages from ${material.title}…"
                                    try {
                                        val result = withContext(Dispatchers.IO) {
                                            ResearchIntelligenceRepository(context, dao)
                                                .extractMaterial(material.id)
                                        }
                                        status = "Extracted ${result.passageCount} source passages."
                                    } catch (error: Throwable) {
                                        status = "Extraction unavailable: ${error.message ?: "unknown error"}"
                                    }
                                }
                            }) { Text("Extract") }
                        }
                    }
                }
            }
        }
        Text(
            "Current support: TXT, Markdown and RDMS Chrome capture text. PDF, DOCX, OCR, AI-generated briefs and multi-paper synthesis are not yet enabled.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}
