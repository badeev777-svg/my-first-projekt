package com.example.calendar.ui.add

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AddTaskScreen(
    dateArg: String,
    onBack: () -> Unit,
    vm: AddTaskViewModel = viewModel()
) {
    LaunchedEffect(dateArg) { vm.initDate(dateArg) }

    var showDatePicker by remember { mutableStateOf(false) }
    var showTimePicker by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Новая задача") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Назад")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            OutlinedTextField(
                value = vm.title,
                onValueChange = vm::setTitle,
                label = { Text("Название задачи") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )

            val dateLabel = vm.date.format(
                DateTimeFormatter.ofPattern("d MMMM yyyy", Locale("ru"))
            )
            OutlinedButton(
                onClick = { showDatePicker = true },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Дата: $dateLabel")
            }

            val timeLabel = vm.time ?: "Без времени"
            OutlinedButton(
                onClick = { showTimePicker = true },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Время: $timeLabel")
            }

            if (vm.time != null) {
                val parts = vm.time!!.split(":").map { it.toInt() }
                val rh = if (parts[0] == 0) 23 else parts[0] - 1
                val reminderStr = "%02d:%02d".format(rh, parts[1])
                Text(
                    text = "Напомним за час до начала — в $reminderStr",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.primary
                )
            }

            Spacer(modifier = Modifier.weight(1f))

            Button(
                onClick = { vm.save(onBack) },
                modifier = Modifier.fillMaxWidth(),
                enabled = vm.title.isNotBlank()
            ) {
                Text("Сохранить")
            }
        }
    }

    if (showDatePicker) {
        val pickerState = rememberDatePickerState(
            initialSelectedDateMillis = vm.date
                .toEpochDay() * 86_400_000L
        )
        DatePickerDialog(
            onDismissRequest = { showDatePicker = false },
            confirmButton = {
                TextButton(onClick = {
                    pickerState.selectedDateMillis?.let { millis ->
                        vm.setDate(LocalDate.ofEpochDay(millis / 86_400_000L))
                    }
                    showDatePicker = false
                }) { Text("OK") }
            },
            dismissButton = {
                TextButton(onClick = { showDatePicker = false }) { Text("Отмена") }
            }
        ) {
            DatePicker(state = pickerState)
        }
    }

    if (showTimePicker) {
        val timePickerState = rememberTimePickerState(
            initialHour = vm.time?.split(":")?.get(0)?.toInt() ?: 9,
            initialMinute = vm.time?.split(":")?.get(1)?.toInt() ?: 0,
            is24Hour = true
        )
        AlertDialog(
            onDismissRequest = { showTimePicker = false },
            confirmButton = {
                TextButton(onClick = {
                    vm.setTime("%02d:%02d".format(timePickerState.hour, timePickerState.minute))
                    showTimePicker = false
                }) { Text("OK") }
            },
            dismissButton = {
                TextButton(onClick = {
                    vm.setTime(null)
                    showTimePicker = false
                }) { Text("Без времени") }
            },
            text = { TimePicker(state = timePickerState) }
        )
    }
}
