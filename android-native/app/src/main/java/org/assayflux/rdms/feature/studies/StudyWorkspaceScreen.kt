package org.assayflux.rdms.feature.studies

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
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.platform.LocalContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.assayflux.rdms.data.AuditEventEntity
import org.assayflux.rdms.data.ParticipantEntity
import org.assayflux.rdms.data.LocalDatabaseFactory
import org.assayflux.rdms.data.ParticipantEntity
import org.assayflux.rdms.data.StudyEntity
import java.util.UUID

/** Native local CRUD foundation for study and participant registration. */
@Composable
fun StudyWorkspaceScreen(initialSection: String = "Studies") {
    val context = LocalContext.current
    val database = remember(context) { LocalDatabaseFactory.create(context) }
    val dao = remember(database) { database.rdmsDao() }
    val studies by dao.observeStudies().collectAsState(initial = emptyList())
    val scope = rememberCoroutineScope()

    var selectedStudyId by remember { mutableStateOf<String?>(null) }
    var studyCode by remember { mutableStateOf("") }
    var studyTitle by remember { mutableStateOf("") }
    var studyDescription by remember { mutableStateOf("") }
    var participantCode by remember { mutableStateOf("") }
    var participantLabel by remember { mutableStateOf("") }
    var status by remember { mutableStateOf("All changes are stored locally in the encrypted database.") }
    var section by remember { mutableStateOf(initialSection) }

    LaunchedEffect(studies) {
        if (selectedStudyId == null && studies.isNotEmpty()) selectedStudyId = studies.first().id
        if (selectedStudyId != null && studies.none { it.id == selectedStudyId }) {
            selectedStudyId = studies.firstOrNull()?.id
        }
    }

    val participantsFlow = remember(dao, selectedStudyId) {
        selectedStudyId?.let { dao.observeParticipants(it) } ?: flowOf(emptyList<ParticipantEntity>())
    }
    val participants by participantsFlow.collectAsState(initial = emptyList())

    Column(
        Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(if (section == "Studies") "Studies" else "Participants", style = MaterialTheme.typography.headlineMedium)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = { section = "Studies" }) { Text("Studies") }
            OutlinedButton(onClick = { section = "Participants" }) { Text("Participants") }
        }
        Text(status, style = MaterialTheme.typography.bodySmall)
        if (section == "Studies") {
            Text("Create a research study", style = MaterialTheme.typography.titleMedium)
            OutlinedTextField(
                value = studyCode, onValueChange = { studyCode = it },
                label = { Text("Study code") }, singleLine = true, modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = studyTitle, onValueChange = { studyTitle = it },
                label = { Text("Study title") }, singleLine = true, modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = studyDescription, onValueChange = { studyDescription = it },
                label = { Text("Description") }, modifier = Modifier.fillMaxWidth()
            )
            Button(
                enabled = studyCode.isNotBlank() && studyTitle.isNotBlank(),
                onClick = {
                    scope.launch {
                        val now = System.currentTimeMillis()
                        val id = UUID.randomUUID().toString()
                        try {
                            withContext(Dispatchers.IO) {
                                dao.insertStudy(
                                    StudyEntity(
                                        id = id,
                                        studyCode = studyCode.trim(),
                                        title = studyTitle.trim(),
                                        description = studyDescription.trim(),
                                        createdAtEpochMillis = now,
                                        updatedAtEpochMillis = now
                                    )
                                )
                                dao.appendAuditEvent(
                                    AuditEventEntity(
                                        id = UUID.randomUUID().toString(),
                                        actorId = "local-user",
                                        action = "STUDY_CREATED",
                                        entityType = "STUDY",
                                        entityId = id,
                                        occurredAtEpochMillis = now
                                    )
                                )
                            }
                            selectedStudyId = id
                            studyCode = ""; studyTitle = ""; studyDescription = ""
                            status = "Study created and audit event recorded."
                        } catch (error: Throwable) {
                            status = "Could not create study: ${error.message ?: "check for a duplicate study code"}"
                        }
                    }
                }
            ) { Text("Create study") }

            Text("Your studies (${studies.size})", style = MaterialTheme.typography.titleMedium)
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(studies, key = { it.id }) { study ->
                    Card(
                        onClick = { selectedStudyId = study.id },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text(study.title, style = MaterialTheme.typography.titleSmall)
                            Text("${study.studyCode} • ${study.status}", style = MaterialTheme.typography.bodySmall)
                            Text(study.description, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
        } else {
            Text("Select a study", style = MaterialTheme.typography.titleMedium)
            if (studies.isEmpty()) {
                Text("Create a study before registering participants.")
            } else {
                LazyColumn(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    items(studies, key = { it.id }) { study ->
                        OutlinedButton(
                            onClick = { selectedStudyId = study.id },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(if (study.id == selectedStudyId) "✓ " + study.studyCode + " — " + study.title
                                 else study.studyCode + " — " + study.title)
                        }
                    }
                }
                Text("Register participant", style = MaterialTheme.typography.titleMedium)
                OutlinedTextField(
                    value = participantCode, onValueChange = { participantCode = it },
                    label = { Text("Participant code") }, singleLine = true, modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = participantLabel, onValueChange = { participantLabel = it },
                    label = { Text("Display label (avoid direct identifiers)") }, singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                Button(
                    enabled = selectedStudyId != null && participantCode.isNotBlank() && participantLabel.isNotBlank(),
                    onClick = {
                        val studyId = selectedStudyId ?: return@Button
                        scope.launch {
                            val now = System.currentTimeMillis()
                            val id = UUID.randomUUID().toString()
                            try {
                                withContext(Dispatchers.IO) {
                                    dao.insertParticipant(
                                        ParticipantEntity(
                                            id = id, studyId = studyId,
                                            participantCode = participantCode.trim(),
                                            displayLabel = participantLabel.trim(),
                                            consentStatus = "PENDING",
                                            createdAtEpochMillis = now
                                        )
                                    )
                                    dao.appendAuditEvent(
                                        AuditEventEntity(
                                            id = UUID.randomUUID().toString(),
                                            actorId = "local-user",
                                            action = "PARTICIPANT_CREATED",
                                            entityType = "PARTICIPANT",
                                            entityId = id,
                                            occurredAtEpochMillis = now
                                        )
                                    )
                                }
                                participantCode = ""; participantLabel = ""
                                status = "Participant registered with consent marked PENDING."
                            } catch (error: Throwable) {
                                status = "Could not register participant: ${error.message ?: "unknown error"}"
                            }
                        }
                    }
                ) { Text("Register participant") }

                Text("Participants (${participants.size})", style = MaterialTheme.typography.titleMedium)
                LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(participants, key = { it.id }) { participant ->
                        Card(modifier = Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                                Text(participant.displayLabel, style = MaterialTheme.typography.titleSmall)
                                Text(participant.participantCode, style = MaterialTheme.typography.bodySmall)
                                Text("Consent: ${participant.consentStatus}", style = MaterialTheme.typography.labelSmall)
                            }
                        }
                    }
                }
            }
        }
    }
}
