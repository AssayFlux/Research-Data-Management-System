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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.assayflux.rdms.data.AuditEventEntity
import org.assayflux.rdms.data.LocalDatabaseFactory
import org.assayflux.rdms.data.ResearchParameterEntity
import org.assayflux.rdms.data.StudyEntity
import java.util.UUID

/** Native parameter dictionary with study-scoped keys and atomic audit logging. */
@Composable
fun ParametersScreen() {
    val context = LocalContext.current
    val database = remember(context) { LocalDatabaseFactory.create(context) }
    val studyDao = remember(database) { database.rdmsDao() }
    val domainDao = remember(database) { database.researchDomainDao() }
    val studies by studyDao.observeStudies().collectAsState(initial = emptyList())
    val scope = rememberCoroutineScope()

    var selectedStudyId by remember { mutableStateOf<String?>(null) }
    var parameterKey by remember { mutableStateOf("") }
    var label by remember { mutableStateOf("") }
    var dataType by remember { mutableStateOf("NUMBER") }
    var unit by remember { mutableStateOf("") }
    var category by remember { mutableStateOf("") }
    var referenceRange by remember { mutableStateOf("") }
    var status by remember { mutableStateOf("Parameters are stored locally and scoped to a study.") }

    LaunchedEffect(studies) {
        if (selectedStudyId == null && studies.isNotEmpty()) selectedStudyId = studies.first().id
        if (selectedStudyId != null && studies.none { it.id == selectedStudyId }) {
            selectedStudyId = studies.firstOrNull()?.id
        }
    }
    val parametersFlow = remember(domainDao, selectedStudyId) {
        selectedStudyId?.let { domainDao.observeParameters(it) }
            ?: flowOf(emptyList<ResearchParameterEntity>())
    }
    val parameters by parametersFlow.collectAsState(initial = emptyList())

    Column(
        Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Text("Research parameters", style = MaterialTheme.typography.headlineMedium)
        Text("Define study variables, data types, units and reference ranges.")
        if (studies.isEmpty()) {
            Text("Create a study before defining its parameters.")
        } else {
            Text("Study", style = MaterialTheme.typography.titleSmall)
            LazyColumn(
                modifier = Modifier.fillMaxWidth().weight(0.32f, fill = false),
                verticalArrangement = Arrangement.spacedBy(4.dp)
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
            Text("New parameter", style = MaterialTheme.typography.titleMedium)
            OutlinedTextField(
                value = parameterKey, onValueChange = { parameterKey = it },
                label = { Text("Parameter key (e.g. systolic_bp)") },
                singleLine = true, modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = label, onValueChange = { label = it },
                label = { Text("Display label") },
                singleLine = true, modifier = Modifier.fillMaxWidth()
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = dataType, onValueChange = { dataType = it.uppercase().take(24) },
                    label = { Text("Data type") }, singleLine = true,
                    modifier = Modifier.weight(1f)
                )
                OutlinedTextField(
                    value = unit, onValueChange = { unit = it },
                    label = { Text("Unit") }, singleLine = true,
                    modifier = Modifier.weight(1f)
                )
            }
            OutlinedTextField(
                value = category, onValueChange = { category = it },
                label = { Text("Category") }, singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = referenceRange, onValueChange = { referenceRange = it },
                label = { Text("Reference range / notes") },
                modifier = Modifier.fillMaxWidth()
            )
            Button(
                enabled = selectedStudyId != null && parameterKey.isNotBlank() &&
                    label.isNotBlank() && dataType.isNotBlank(),
                onClick = {
                    val studyId = selectedStudyId ?: return@Button
                    scope.launch {
                        val now = System.currentTimeMillis()
                        val id = UUID.randomUUID().toString()
                        try {
                            withContext(Dispatchers.IO) {
                                domainDao.createParameterWithAudit(
                                    ResearchParameterEntity(
                                        id = id,
                                        studyId = studyId,
                                        parameterKey = parameterKey.trim(),
                                        label = label.trim(),
                                        dataType = dataType.trim().uppercase(),
                                        unit = unit.trim().ifBlank { null },
                                        category = category.trim().ifBlank { null },
                                        referenceRangeJson = referenceRange.trim().ifBlank { null },
                                        validationJson = "{}",
                                        isRequired = false,
                                        isActive = true,
                                        createdAtEpochMillis = now
                                    ),
                                    AuditEventEntity(
                                        id = UUID.randomUUID().toString(),
                                        actorId = "local-user",
                                        action = "PARAMETER_CREATED",
                                        entityType = "PARAMETER",
                                        entityId = id,
                                        occurredAtEpochMillis = now
                                    )
                                )
                            }
                            parameterKey = ""; label = ""; unit = ""; category = ""; referenceRange = ""
                            status = "Parameter saved and audit event recorded."
                        } catch (error: Throwable) {
                            status = "Could not save parameter: ${error.message ?: "check for a duplicate key"}"
                        }
                    }
                }
            ) { Text("Save parameter") }
            Text(status, style = MaterialTheme.typography.bodySmall)
            Text("Parameters (${parameters.size})", style = MaterialTheme.typography.titleMedium)
            LazyColumn(verticalArrangement = Arrangement.spacedBy(7.dp)) {
                items(parameters, key = { it.id }) { parameter ->
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                            Text(parameter.label, style = MaterialTheme.typography.titleSmall)
                            Text(parameter.parameterKey, style = MaterialTheme.typography.bodySmall)
                            Text(
                                listOfNotNull(parameter.dataType, parameter.unit, parameter.category).joinToString(" • "),
                                style = MaterialTheme.typography.labelSmall
                            )
                            parameter.referenceRangeJson?.let {
                                Text("Reference: $it", style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
                }
            }
        }
    }
}
