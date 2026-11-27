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
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
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
import java.util.UUID

private data class FormFieldDraft(
    val key: String,
    val label: String,
    val type: String,
    val required: Boolean
)

/** Versioned study form builder; form and its fields are saved atomically. */
@Composable
fun FormsScreen() {
    val context = LocalContext.current
    val database = remember(context) { LocalDatabaseFactory.create(context) }
    val studyDao = remember(database) { database.rdmsDao() }
    val domainDao = remember(database) { database.researchDomainDao() }
    val studies by studyDao.observeStudies().collectAsState(initial = emptyList())
    val scope = rememberCoroutineScope()

    var selectedStudyId by remember { mutableStateOf<String?>(null) }
    var formKey by remember { mutableStateOf("") }
    var title by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var fieldKey by remember { mutableStateOf("") }
    var fieldLabel by remember { mutableStateOf("") }
    var fieldType by remember { mutableStateOf("TEXT") }
    var fieldRequired by remember { mutableStateOf(false) }
    val drafts = remember { mutableStateListOf<FormFieldDraft>() }
    var status by remember { mutableStateOf("Create a versioned data-collection form for a study.") }

    LaunchedEffect(studies) {
        if (selectedStudyId == null && studies.isNotEmpty()) selectedStudyId = studies.first().id
        if (selectedStudyId != null && studies.none { it.id == selectedStudyId }) {
            selectedStudyId = studies.firstOrNull()?.id
        }
    }
    val formsFlow = remember(domainDao, selectedStudyId) {
        selectedStudyId?.let { domainDao.observeForms(it) }
            ?: flowOf(emptyList<ResearchFormEntity>())
    }
    val forms by formsFlow.collectAsState(initial = emptyList())

    Column(
        Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(9.dp)
    ) {
        Text("Form builder", style = MaterialTheme.typography.headlineMedium)
        Text("Forms are versioned; saved field definitions remain linked to records.")
        if (studies.isEmpty()) {
            Text("Create a study before building a form.")
        } else {
            Text("Study", style = MaterialTheme.typography.titleSmall)
            LazyColumn(
                modifier = Modifier.fillMaxWidth().weight(0.2f, fill = false),
                verticalArrangement = Arrangement.spacedBy(3.dp)
            ) {
                items(studies, key = { it.id }) { study ->
                    OutlinedButton(
                        onClick = { selectedStudyId = study.id },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text((if (selectedStudyId == study.id) "✓ " else "") + study.studyCode + " — " + study.title)
                    }
                }
            }
            Text("New form", style = MaterialTheme.typography.titleMedium)
            OutlinedTextField(
                value = formKey, onValueChange = { formKey = it },
                label = { Text("Form key") }, singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = title, onValueChange = { title = it },
                label = { Text("Form title") }, singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = description, onValueChange = { description = it },
                label = { Text("Description") }, modifier = Modifier.fillMaxWidth()
            )
            Text("Add a field", style = MaterialTheme.typography.titleSmall)
            OutlinedTextField(
                value = fieldKey, onValueChange = { fieldKey = it },
                label = { Text("Field key") }, singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = fieldLabel, onValueChange = { fieldLabel = it },
                    label = { Text("Field label") }, singleLine = true,
                    modifier = Modifier.weight(1f)
                )
                OutlinedTextField(
                    value = fieldType, onValueChange = { fieldType = it.uppercase().take(24) },
                    label = { Text("Type") }, singleLine = true,
                    modifier = Modifier.weight(0.7f)
                )
            }
            Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                Checkbox(checked = fieldRequired, onCheckedChange = { fieldRequired = it })
                Text("Required field")
                OutlinedButton(
                    enabled = fieldKey.isNotBlank() && fieldLabel.isNotBlank() && fieldType.isNotBlank(),
                    onClick = {
                        if (drafts.none { it.key.equals(fieldKey.trim(), ignoreCase = true) }) {
                            drafts.add(FormFieldDraft(fieldKey.trim(), fieldLabel.trim(), fieldType.trim(), fieldRequired))
                            fieldKey = ""; fieldLabel = ""; fieldRequired = false
                        } else {
                            status = "Field keys must be unique within a form."
                        }
                    }
                ) { Text("Add field") }
            }
            if (drafts.isNotEmpty()) {
                Text("Fields to save (${drafts.size})", style = MaterialTheme.typography.titleSmall)
                drafts.forEachIndexed { index, draft ->
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text("${index + 1}. ${draft.label} (${draft.key}) — ${draft.type}")
                        OutlinedButton(onClick = { drafts.removeAt(index) }) { Text("Remove") }
                    }
                }
            }
            Button(
                enabled = selectedStudyId != null && formKey.isNotBlank() &&
                    title.isNotBlank() && drafts.isNotEmpty(),
                onClick = {
                    val studyId = selectedStudyId ?: return@Button
                    scope.launch {
                        val now = System.currentTimeMillis()
                        val formId = UUID.randomUUID().toString()
                        try {
                            withContext(Dispatchers.IO) {
                                val currentVersion = forms.filter { it.formKey == formKey.trim() }
                                    .maxOfOrNull { it.version } ?: 0
                                val form = ResearchFormEntity(
                                    id = formId,
                                    studyId = studyId,
                                    formKey = formKey.trim(),
                                    title = title.trim(),
                                    description = description.trim(),
                                    version = currentVersion + 1,
                                    status = "DRAFT",
                                    createdAtEpochMillis = now,
                                    updatedAtEpochMillis = now
                                )
                                val fields = drafts.mapIndexed { index, draft ->
                                    ResearchFormFieldEntity(
                                        id = UUID.randomUUID().toString(),
                                        formId = formId,
                                        parameterId = null,
                                        fieldKey = draft.key,
                                        label = draft.label,
                                        inputType = draft.type,
                                        required = draft.required,
                                        validationJson = "{}",
                                        position = index
                                    )
                                }
                                domainDao.createFormWithFieldsAndAudit(
                                    form,
                                    fields,
                                    AuditEventEntity(
                                        id = UUID.randomUUID().toString(),
                                        actorId = "local-user",
                                        action = "FORM_CREATED",
                                        entityType = "FORM",
                                        entityId = formId,
                                        occurredAtEpochMillis = now
                                    )
                                )
                            }
                            formKey = ""; title = ""; description = ""; drafts.clear()
                            status = "Form and field definitions saved."
                        } catch (error: Throwable) {
                            status = "Could not save form: ${error.message ?: "check the form key"}"
                        }
                    }
                }
            ) { Text("Save form version") }
            Text(status, style = MaterialTheme.typography.bodySmall)
            Text("Existing forms (${forms.size})", style = MaterialTheme.typography.titleMedium)
            LazyColumn(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                items(forms, key = { it.id }) { form ->
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(11.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                            Text(form.title, style = MaterialTheme.typography.titleSmall)
                            Text("${form.formKey} • v${form.version} • ${form.status}", style = MaterialTheme.typography.bodySmall)
                            Text(form.description, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
        }
    }
}
