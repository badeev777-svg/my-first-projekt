package com.example.calendar.ui.main

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.calendar.domain.Task
import java.time.LocalDate
import java.time.format.TextStyle
import java.util.Locale

@Composable
fun MainScreen(
    onAddTask: (LocalDate) -> Unit,
    vm: MainViewModel = viewModel()
) {
    val selectedDate by vm.selectedDate.collectAsStateWithLifecycle()
    val weekStart by vm.weekStart.collectAsStateWithLifecycle()
    val tasks by vm.tasks.collectAsStateWithLifecycle()
    val datesWithTasks by vm.datesWithTasks.collectAsStateWithLifecycle()

    Scaffold(
        floatingActionButton = {
            FloatingActionButton(onClick = { onAddTask(selectedDate) }) {
                Icon(Icons.Default.Add, contentDescription = "Добавить")
            }
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .background(MaterialTheme.colorScheme.background)
        ) {
            MonthHeader(
                weekStart = weekStart,
                onPrevious = vm::previousWeek,
                onNext = vm::nextWeek
            )
            WeekStrip(
                weekStart = weekStart,
                selectedDate = selectedDate,
                datesWithTasks = datesWithTasks,
                onDateSelected = vm::selectDate,
                onSwipeLeft = vm::nextWeek,
                onSwipeRight = vm::previousWeek
            )
            HorizontalDivider(color = MaterialTheme.colorScheme.outline)
            TaskListHeader(date = selectedDate, count = tasks.size)
            TaskList(tasks = tasks, onToggle = vm::toggleDone, onDelete = vm::deleteTask)
        }
    }
}

@Composable
private fun MonthHeader(weekStart: LocalDate, onPrevious: () -> Unit, onNext: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        TextButton(onClick = onPrevious) {
            Text("‹", style = MaterialTheme.typography.headlineMedium)
        }
        val monthName = weekStart.month
            .getDisplayName(TextStyle.FULL_STANDALONE, Locale("ru"))
            .replaceFirstChar { it.uppercase() }
        Text("$monthName ${weekStart.year}", style = MaterialTheme.typography.titleMedium)
        TextButton(onClick = onNext) {
            Text("›", style = MaterialTheme.typography.headlineMedium)
        }
    }
}

@Composable
private fun WeekStrip(
    weekStart: LocalDate,
    selectedDate: LocalDate,
    datesWithTasks: Set<LocalDate>,
    onDateSelected: (LocalDate) -> Unit,
    onSwipeLeft: () -> Unit,
    onSwipeRight: () -> Unit
) {
    var dragTotal by remember { mutableFloatStateOf(0f) }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 8.dp, vertical = 4.dp)
            .pointerInput(Unit) {
                detectHorizontalDragGestures(
                    onDragEnd = {
                        if (dragTotal > 80f) onSwipeRight()
                        else if (dragTotal < -80f) onSwipeLeft()
                        dragTotal = 0f
                    },
                    onHorizontalDrag = { _, delta -> dragTotal += delta }
                )
            },
        horizontalArrangement = Arrangement.SpaceEvenly
    ) {
        val dayLabels = listOf("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")
        repeat(7) { i ->
            val date = weekStart.plusDays(i.toLong())
            val isSelected = date == selectedDate
            val hasTasks = date in datesWithTasks

            Column(
                modifier = Modifier
                    .weight(1f)
                    .padding(2.dp)
                    .background(
                        color = if (isSelected) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.surface,
                        shape = RoundedCornerShape(12.dp)
                    )
                    .clickable { onDateSelected(date) }
                    .padding(vertical = 6.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = dayLabels[i],
                    style = MaterialTheme.typography.labelSmall,
                    color = if (isSelected) Color.White.copy(alpha = 0.7f)
                    else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                )
                Text(
                    text = date.dayOfMonth.toString(),
                    style = MaterialTheme.typography.bodyMedium,
                    color = if (isSelected) Color.White else MaterialTheme.colorScheme.onSurface
                )
                Box(
                    modifier = Modifier
                        .size(4.dp)
                        .background(
                            color = if (hasTasks) {
                                if (isSelected) Color.White else MaterialTheme.colorScheme.primary
                            } else Color.Transparent,
                            shape = CircleShape
                        )
                )
            }
        }
    }
}

@Composable
private fun TaskListHeader(date: LocalDate, count: Int) {
    val day = date.dayOfMonth
    val month = date.month.getDisplayName(TextStyle.FULL_STANDALONE, Locale("ru"))
    Text(
        text = "$day $month · $count ${taskWord(count)}",
        style = MaterialTheme.typography.labelMedium,
        color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.5f),
        modifier = Modifier.padding(start = 16.dp, top = 12.dp, bottom = 8.dp)
    )
}

private fun taskWord(n: Int): String = when {
    n % 100 in 11..19 -> "задач"
    n % 10 == 1        -> "задача"
    n % 10 in 2..4     -> "задачи"
    else               -> "задач"
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TaskList(
    tasks: List<Task>,
    onToggle: (Task) -> Unit,
    onDelete: (Task) -> Unit
) {
    LazyColumn(
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 4.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        items(tasks, key = { it.id }) { task ->
            val dismissState = rememberSwipeToDismissBoxState(
                confirmValueChange = { value ->
                    if (value == SwipeToDismissBoxValue.EndToStart) {
                        onDelete(task)
                        true
                    } else false
                }
            )
            SwipeToDismissBox(
                state = dismissState,
                backgroundContent = {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .background(Color(0xFFB00020), RoundedCornerShape(12.dp))
                            .padding(end = 16.dp),
                        contentAlignment = Alignment.CenterEnd
                    ) {
                        Icon(Icons.Default.Delete, contentDescription = "Удалить", tint = Color.White)
                    }
                }
            ) {
                TaskItem(task = task, onToggle = { onToggle(task) })
            }
        }
    }
}

@Composable
private fun TaskItem(task: Task, onToggle: () -> Unit) {
    Surface(
        shape = RoundedCornerShape(12.dp),
        color = MaterialTheme.colorScheme.surface,
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Checkbox(checked = task.isDone, onCheckedChange = { onToggle() })
            Column {
                Text(
                    text = task.title,
                    style = MaterialTheme.typography.bodyMedium,
                    textDecoration = if (task.isDone) TextDecoration.LineThrough else null,
                    color = if (task.isDone) MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f)
                    else MaterialTheme.colorScheme.onSurface
                )
                if (task.time != null) {
                    val reminderTime = task.time.let {
                        val parts = it.split(":").map { p -> p.toInt() }
                        val h = if (parts[0] == 0) 23 else parts[0] - 1
                        "%02d:%02d".format(h, parts[1])
                    }
                    Text(
                        text = "🕐 ${task.time} · напомним в $reminderTime",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }
        }
    }
}
