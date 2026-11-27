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
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.assayflux.rdms.data.AuditEventEntity
import org.assayflux.rdms.data.LocalDatabaseFactory
import org.assayflux.rdms.data.ResearchFormEntity
import org.assayflux.rdms.data.ResearchFormFieldEntity
import org.assayflux.rdms.data.ResearchRecordEntity
import org.assayflux.rdms.data.ResearchRecordValueEntity
import org.assayflux.rdms.data.ParticipantEntity
import java.util.UUID

/** Dynamic form entry with required-field checks, explicit missing states and record locking. */
@Composable
fun RecordsScreen() {
    val context = LocalContext.current
    val database = remember(context) { LocalDatabaseFactory.create(context) }
    val studyDao = remember(database) { database.rdmsDao() }
    val domainDao = remember(database) { database.researchDomainDao() }
    val studies by studyDao.observeStudies().collectAsState(initial = emptyList())
    val scope = rememberCoroutineScope()

    var studyId by remember { mutableStateOf<String?>(null) }
    var participantId by remember { mutableStateOf<String?>(null) }
    var formId by remember { mutableStateOf<String?>(null) }
    var status by remember { mutableStateOf("Select a study, participant and form to enter research data.") }
    val fieldValues = remember { mutableStateMapOf<String, String>() }

    LaunchedEffect(studies) {
        if (studyId == null && studies.isNotEmpty()) studyId = studies.first().id
        if (studyId != null && studies.none { it.id == studyId }) studyId = studies.firstOrNull()?.id
    }
    val participantsFlow = remember(studyDao, studyId) {
        studyId?.let { studyDao.observeParticipants(it) } ?: flowOf(emptyList<ParticipantEntity>())
    }
    val participants by participantsFlow.collectAsState(initial = emptyList())
    LaunchedEffect(participants) {
        if (participantId == null && participants.isNotEmpty()) participantId = participants.first().id
        if (participantId != null && participants.none { it.id == participantId }) {
            participantId = participants.firstOrNull()?.id
        }
    }
    val formsFlow = remember(domainDao, studyId) {
        studyId?.let { domainDao.observeForms(it) } ?: flowOf(emptyList<ResearchFormEntity>())
    }
    val forms by formsFlow.collectAsState(initial = emptyList())
    LaunchedEffect(forms) {
        if (formId == null && forms.isNotEmpty()) formId = forms.first().id
        if (formId != null && forms.none { it.id == formId }) formId = forms.firstOrNull()?.id
    }
    val fieldsFlow = remember(domainDao, formId) {
        formId?.let { domainDao.observeFormFields(it) } ?: flowOf(emptyList<ResearchFormFieldEntity>())
    }
    val fields by fieldsFlow.collectAsState(initial = emptyList())
    val recordsFlow = remember(domainDao, participantId) {
        participantId?.let { domainDao.observeRecords(it) } ?: flowOf(emptyList<ResearchRecordEntity>())
    }
    val records by recordsFlow.collectAsState(initial = emptyList())

    Column(
        Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(9.dp)
    ) {
        Text("Research records", style = MaterialTheme.typography.headlineMedium)
        Text("Enter data against a versioned study form. Blank optional fields are preserved as missing.")
        if (studies.isEmpty()) {
            Text("Create a study before entering records.")
        } else {
            Text("Study", style = MaterialTheme.typography.titleSmall)
            LazyColumn(
                modifier = Modifier.fillMaxWidth().weight(0.15f, fill = false),
                verticalArrangement = Arrangement.spacedBy(3.dp)
            ) {
                items(studies, key = { it.id }) { study ->
                    OutlinedButton(onClick = { studyId = study.id; participantId = null; formId = null },
                        modifier = Modifier.fillMaxWidth()) {
                        Text((if (studyId == study.id) "✓ " else "") + study.studyCode + " — " + study.title)
                    }
                }
            }
            Text("Participant", style = MaterialTheme.typography.titleSmall)
            if (participants.isEmpty()) Text("No participants registered in this study.")
            participants.forEach { participant ->
                OutlinedButton(
                    onClick = { participantId = participant.id },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text((if (participantId == participant.id) "✓ " else "") +
                        participant.participantCode + " — " + participant.displayLabel)
                }
            }
            Text("Form version", style = MaterialTheme.typography.titleSmall)
            if (forms.isEmpty()) Text("Build a form before entering data.")
            forms.forEach { form ->
                OutlinedButton(
                    onClick = { formId = form.id; fieldValues.clear() },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text((if (formId == form.id) "✓ " else "") +
                        form.title + " (v${form.version})")
                }
            }
            if (formId != null && fields.isNotEmpty()) {
                Text("Data entry", style = MaterialTheme.typography.titleMedium)
                fields.forEach { field ->
                    OutlinedTextField(
                        value = fieldValues[field.id] ?: "",
                        onValueChange = { fieldValues[field.id] = it },
                        label = { Text(field.label + if (field.required) " *" else "") },
                        supportingText = { Text("${field.inputType} • ${if (field.required) "Required" else "Optional"}") },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
                Button(
                    enabled = participantId != null,
                    onClick = {
                        val selectedParticipant = participantId ?: return@Button
                        val selectedStudy = studyId ?: return@Button
                        val selectedForm = forms.firstOrNull { it.id == formId } ?: return@Button
                        val missingRequired = fields.filter { it.required && fieldValues[it.id].isNullOrBlank() }
                        val invalidNumbers = fields.filter {
                            it.inputType.uppercase() in setOf("NUMBER", "DECIMAL", "INTEGER") &&
                                !fieldValues[it.id].isNullOrBlank() &&
                                fieldValues[it.id]?.toDoubleOrNull() == null
                        }
                        if (missingRequired.isNotEmpty()) {
                            status = "Complete required fields: " + missingRequired.joinToString { it.label }
                            return@Button
                        }
                        if (invalidNumbers.isNotEmpty()) {
                            status = "Enter valid numeric values for: " + invalidNumbers.joinToString { it.label }
                            return@Button
                        }
                        val valueSnapshot = fieldValues.toMap()
                        scope.launch {
                            val now = System.currentTimeMillis()
                            val recordId = UUID.randomUUID().toString()
                            try {
                                withContext(Dispatchers.IO) {
                                    val values = fields.map { field ->
                                        val raw = valueSnapshot[field.id]?.trim().orEmpty()
                                        val numeric = if (field.inputType.uppercase() in setOf("NUMBER", "DECIMAL", "INTEGER")) raw.toDoubleOrNull() else null
                                        ResearchRecordValueEntity(
                                            id = UUID.randomUUID().toString(),
                                            recordId = recordId,
                                            fieldId = field.id,
                                            valueText = raw.ifBlank { null },
                                            valueNumber = numeric,
                                            valueJson = null,
                                            missingReason = if (raw.isBlank()) "NOT_RECORDED" else null,
                                            recordedAtEpochMillis = now
                                        )
                                    }
                                    domainDao.createRecordWithValuesAndAudit(
                                        ResearchRecordEntity(
                                            id = recordId,
                                            studyId = selectedStudy,
                                            participantId = selectedParticipant,
                                            formId = selectedForm.id,
                                            visitId = null,
                                            recordStatus = "DRAFT",
                                            isLocked = false,
                                            createdAtEpochMillis = now,
                                            updatedAtEpochMillis = now,
                                            lockedAtEpochMillis = null
                                        ),
                                        values,
                                        AuditEventEntity(
                                            id = UUID.randomUUID().toString(),
                                            actorId = "local-user",
                                            action = "RESEARCH_RECORD_CREATED",
                                            entityType = "RESEARCH_RECORD",
                                            entityId = recordId,
                                            occurredAtEpochMillis = now
                                        )
                                    )
                                }
                                fieldValues.clear()
                                status = "Record saved with ${fields.size} field values; optional blanks retained as NOT_RECORDED."
                            } catch (error: Throwable) {
                                status = "Could not save record: ${error.message ?: "unknown error"}"
                            }
                        }
                    }
                ) { Text("Save research record") }
            }
            Text(status, style = MaterialTheme.typography.bodySmall)
            Text("Participant records (${records.size})", style = MaterialTheme.typography.titleMedium)
            records.forEach { record ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Row(
                        Modifier.fillMaxWidth().padding(10.dp),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                            Text(record.recordStatus, style = MaterialTheme.typography.titleSmall)
                            Text("Created ${record.createdAtEpochMillis}", style = MaterialTheme.typography.bodySmall)
                            Text(if (record.isLocked) "Locked" else "Editable", style = MaterialTheme.typography.labelSmall)
                        }
                        if (!record.isLocked) {
                            OutlinedButton(onClick = {
                                scope.launch {
                                    val now = System.currentTimeMillis()
                                    try {
                                        withContext(Dispatchers.IO) {
                                            domainDao.lockRecordWithAudit(
                                                record.id, now,
                                                AuditEventEntity(
                                                    id = UUID.randomUUID().toString(),
                                                    actorId = "local-user",
                                                    action = "RESEARCH_RECORD_LOCKED",
                                                    entityType = "RESEARCH_RECORD",
                                                    entityId = record.id,
                                                    occurredAtEpochMillis = now
                                                )
                                            )
                                        }
                                        status = "Record locked. Its values can no longer be edited."
                                    } catch (error: Throwable) {
                                        status = "Could not lock record: ${error.message ?: "unknown error"}"
                                    }
                                }
                            }) { Text("Lock") }
                        }
                    }
                }
            }
        }
    }
}
