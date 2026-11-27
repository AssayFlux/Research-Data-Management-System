package org.assayflux.rdms.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalDrawerSheet
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.NavigationDrawerItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.lightColorScheme
import androidx.compose.material3.rememberDrawerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import org.assayflux.rdms.feature.research.ResearchIntelligenceScreen
import org.assayflux.rdms.feature.studies.StudyWorkspaceScreen

private val RdmsTeal = Color(0xFF0F766E)
private val RdmsInk = Color(0xFF0F172A)
private val RdmsBody = Color(0xFF334155)
private val RdmsMuted = Color(0xFF64748B)
private val RdmsCanvas = Color(0xFFF7F9FB)
private val RdmsBorder = Color(0xFFE5E9EF)

@Composable
fun RdmsTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = lightColorScheme(
            primary = RdmsTeal,
            onPrimary = Color.White,
            secondary = Color(0xFF14B8A6),
            background = RdmsCanvas,
            surface = Color.White,
            onSurface = RdmsInk,
            onBackground = RdmsBody,
            outline = RdmsBorder
        ),
        content = content
    )
}

private data class RdmsDestination(val title: String, val group: String, val symbol: String)

private val destinations = listOf(
    RdmsDestination("Dashboard", "General", "▦"),
    RdmsDestination("Quick Entry", "General", "⚡"),
    RdmsDestination("Learn", "General", "▤"),
    RdmsDestination("Studies", "Workspace", "⚗"),
    RdmsDestination("Participants", "Workspace", "♙"),
    RdmsDestination("Parameters", "Workspace", "⌘"),
    RdmsDestination("Forms", "Workspace", "▧"),
    RdmsDestination("Formulas", "Workspace", "∑"),
    RdmsDestination("Records", "Data", "▣"),
    RdmsDestination("Visits", "Data", "◷"),
    RdmsDestination("Biospecimens", "Data", "⚗"),
    RdmsDestination("Recruitment", "Data", "⌁"),
    RdmsDestination("Adverse events", "Data", "⚠"),
    RdmsDestination("Data quality", "Data", "✓"),
    RdmsDestination("Critical alerts", "Data", "!"),
    RdmsDestination("Reliability", "Data", "∿"),
    RdmsDestination("Criteria & groups", "Data", "◎"),
    RdmsDestination("Query builder", "Data", "⌕"),
    RdmsDestination("Analysis", "Analysis", "∑"),
    RdmsDestination("Statistics", "Analysis", "▥"),
    RdmsDestination("Graphs", "Analysis", "⌁"),
    RdmsDestination("Longitudinal", "Analysis", "↗"),
    RdmsDestination("Print center", "Reports & data", "▤"),
    RdmsDestination("Export", "Reports & data", "↓"),
    RdmsDestination("Import", "Reports & data", "↑"),
    RdmsDestination("Research Intelligence", "Research", "✦"),
    RdmsDestination("Users & roles", "Admin", "♙"),
    RdmsDestination("Audit log", "Admin", "≡"),
    RdmsDestination("Backups", "Admin", "▣"),
    RdmsDestination("Settings", "Admin", "⚙")
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RdmsApp() {
    var selected by remember { mutableStateOf("Dashboard") }
    val drawerState = rememberDrawerState(DrawerValue.Closed)
    val scope = rememberCoroutineScope()

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet(
                drawerContainerColor = Color.White,
                drawerContentColor = RdmsBody
            ) {
                Column(Modifier.padding(horizontal = 12.dp, vertical = 18.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(8.dp)) {
                        Box(
                            Modifier.size(38.dp).background(RdmsTeal, RoundedCornerShape(11.dp)),
                            contentAlignment = Alignment.Center
                        ) { Text("R", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 20.sp) }
                        Spacer(Modifier.width(10.dp))
                        Column {
                            Text("RDMS", color = RdmsInk, fontWeight = FontWeight.Bold)
                            Text("Clinical Research Workspace", color = RdmsMuted, fontSize = 10.sp)
                        }
                    }
                    destinations.groupBy { it.group }.forEach { (group, items) ->
                        Text(
                            group.uppercase(),
                            color = RdmsMuted,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            letterSpacing = 1.1.sp,
                            modifier = Modifier.padding(start = 12.dp, top = 18.dp, bottom = 6.dp)
                        )
                        items.forEach { item ->
                            NavigationDrawerItem(
                                label = { Text(item.title, fontSize = 13.sp) },
                                selected = selected == item.title,
                                onClick = {
                                    selected = item.title
                                    scope.launch { drawerState.close() }
                                },
                                icon = { Text(item.symbol, color = if (selected == item.title) RdmsTeal else RdmsMuted) },
                                shape = RoundedCornerShape(8.dp),
                                modifier = Modifier.height(42.dp)
                            )
                        }
                    }
                }
            }
        }
    ) {
        Scaffold(
            containerColor = RdmsCanvas,
            topBar = {
                TopAppBar(
                    title = {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Column {
                                Text("RDMS", fontSize = 14.sp, fontWeight = FontWeight.Bold, color = RdmsInk)
                                Text("Clinical Research Workspace", fontSize = 10.sp, color = RdmsMuted)
                            }
                        }
                    },
                    navigationIcon = {
                        androidx.compose.material3.TextButton(onClick = { scope.launch { drawerState.open() } }) {
                            Text("☰", fontSize = 22.sp, color = RdmsInk)
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.White)
                )
            }
        ) { innerPadding ->
            if (selected == "Dashboard") {
                DashboardContent(
                    modifier = Modifier.padding(innerPadding),
                    onNavigate = { selected = it }
                )
            } else if (selected == "Research Intelligence") {
                Column(Modifier.padding(innerPadding)) {
                    ResearchIntelligenceScreen()
                }
            } else if (selected == "Studies" || selected == "Participants") {
                Column(Modifier.padding(innerPadding)) {
                    StudyWorkspaceScreen(initialSection = selected)
                }
            } else {
                DestinationContent(
                    title = selected,
                    modifier = Modifier.padding(innerPadding),
                    onBack = { selected = "Dashboard" }
                )
            }
        }
    }
}

@Composable
private fun DashboardContent(modifier: Modifier = Modifier, onNavigate: (String) -> Unit) {
    Column(
        modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Card(
            colors = CardDefaults.cardColors(containerColor = Color(0xFFECFDF5)),
            shape = RoundedCornerShape(12.dp),
            border = androidx.compose.foundation.BorderStroke(1.dp, RdmsBorder)
        ) {
            Row(Modifier.fillMaxWidth().padding(20.dp), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("WELCOME BACK", color = RdmsTeal, fontSize = 10.sp, fontWeight = FontWeight.ExtraBold, letterSpacing = 1.4.sp)
                    Text("Your research workspace", color = RdmsInk, fontSize = 22.sp, fontWeight = FontWeight.ExtraBold)
                    Text("Your research data. Organized. Secure. Accessible.", color = RdmsBody, fontSize = 12.sp)
                }
                Text("⚗", fontSize = 42.sp)
            }
        }
        SectionHeading("▦", "Overview")
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            MetricCard("⚗", "—", "STUDIES", Color(0xFF0F766E), Color(0xFFECFDF5), Modifier.weight(1f))
            MetricCard("♙", "—", "PARTICIPANTS", Color(0xFF2563EB), Color(0xFFEFF6FF), Modifier.weight(1f))
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            MetricCard("▣", "—", "RECORDS", Color(0xFF7C3AED), Color(0xFFF3E8FF), Modifier.weight(1f))
            MetricCard("⌘", "—", "PARAMETERS", Color(0xFFD97706), Color(0xFFFFFBEB), Modifier.weight(1f))
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            MetricCard("▧", "—", "FORMS", Color(0xFF0891B2), Color(0xFFECFEFF), Modifier.weight(1f))
            MetricCard("∑", "—", "FORMULAS", Color(0xFFEC4899), Color(0xFFFCE7F3), Modifier.weight(1f))
        }
        SectionHeading("⚡", "Quick actions")
        val actions = listOf(
            Triple("Add Participant", "Register a subject", "Participants"),
            Triple("Add Parameter", "New research variable", "Parameters"),
            Triple("Forms", "Build data collection", "Forms"),
            Triple("Quality", "Validate research data", "Data quality"),
            Triple("Analysis", "Explore study results", "Analysis"),
            Triple("Research Intelligence", "Review papers in one brief", "Research Intelligence")
        )
        actions.chunked(2).forEach { pair ->
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                pair.forEach { (title, subtitle, target) ->
                    Card(
                        onClick = { onNavigate(target) },
                        modifier = Modifier.weight(1f),
                        colors = CardDefaults.cardColors(containerColor = Color.White),
                        border = androidx.compose.foundation.BorderStroke(1.dp, RdmsBorder),
                        shape = RoundedCornerShape(10.dp)
                    ) {
                        Column(Modifier.padding(12.dp)) {
                            Text("↗", color = RdmsTeal, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                            Text(title, color = RdmsInk, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                            Text(subtitle, color = RdmsMuted, fontSize = 10.sp)
                        }
                    }
                }
                if (pair.size == 1) Spacer(Modifier.weight(1f))
            }
        }
        SectionHeading("✓", "Local workspace")
        Card(
            colors = CardDefaults.cardColors(containerColor = Color.White),
            border = androidx.compose.foundation.BorderStroke(1.dp, RdmsBorder),
            shape = RoundedCornerShape(10.dp)
        ) {
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                StatusRow("Storage mode", "Offline-first", Color(0xFF059669))
                StatusRow("Research files", "Local import pipeline in progress", Color(0xFFD97706))
                StatusRow("Security", "Biometric gate enabled; hardening in progress", Color(0xFFD97706))
            }
        }
        Text("Beta foundation — do not store production research data yet.", color = RdmsMuted, fontSize = 11.sp, modifier = Modifier.padding(bottom = 18.dp))
    }
}

@Composable
private fun MetricCard(symbol: String, value: String, label: String, accent: Color, tint: Color, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(containerColor = Color.White),
        border = androidx.compose.foundation.BorderStroke(1.dp, RdmsBorder),
        shape = RoundedCornerShape(10.dp)
    ) {
        Column(Modifier.fillMaxWidth().padding(13.dp)) {
            Box(Modifier.size(30.dp).background(tint, RoundedCornerShape(8.dp)), contentAlignment = Alignment.Center) {
                Text(symbol, color = accent, fontSize = 16.sp, fontWeight = FontWeight.Bold)
            }
            Text(value, color = RdmsInk, fontSize = 22.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 6.dp))
            Text(label, color = RdmsMuted, fontSize = 9.sp, fontWeight = FontWeight.Bold, letterSpacing = .6.sp)
        }
    }
}

@Composable
private fun SectionHeading(symbol: String, title: String) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(symbol, color = RdmsMuted, fontSize = 14.sp)
        Text(title, color = RdmsInk, fontSize = 13.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun StatusRow(label: String, value: String, color: Color) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
        Text(label, color = RdmsBody, fontSize = 12.sp, fontWeight = FontWeight.Medium)
        Text(value, color = color, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun DestinationContent(title: String, modifier: Modifier = Modifier, onBack: () -> Unit) {
    Column(
        modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(title, color = RdmsInk, fontSize = 23.sp, fontWeight = FontWeight.ExtraBold)
        Text("RDMS workspace", color = RdmsMuted, fontSize = 12.sp)
        Card(
            colors = CardDefaults.cardColors(containerColor = Color.White),
            border = androidx.compose.foundation.BorderStroke(1.dp, RdmsBorder),
            shape = RoundedCornerShape(10.dp)
        ) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("$title module", color = RdmsInk, fontWeight = FontWeight.Bold)
                Text(
                    "This native module is being migrated from the existing RDMS website. Its original workflow and visual design are being preserved; data operations will be connected as the encrypted local repository is completed.",
                    color = RdmsBody,
                    fontSize = 13.sp
                )
                androidx.compose.material3.Button(onClick = onBack) { Text("Back to dashboard") }
            }
        }
    }
}
