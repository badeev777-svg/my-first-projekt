package com.example.calendar.ui.main

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.calendar.data.TaskRepository
import com.example.calendar.data.db.TaskDatabase
import com.example.calendar.domain.Task
import com.example.calendar.notifications.TaskReminderWorker
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.time.DayOfWeek
import java.time.LocalDate

@OptIn(ExperimentalCoroutinesApi::class)
class MainViewModel(app: Application) : AndroidViewModel(app) {

    private val repo = TaskRepository(TaskDatabase.getInstance(app).taskDao())

    private val _selectedDate = MutableStateFlow(LocalDate.now())
    val selectedDate: StateFlow<LocalDate> = _selectedDate.asStateFlow()

    private val _weekStart = MutableStateFlow(LocalDate.now().with(DayOfWeek.MONDAY))
    val weekStart: StateFlow<LocalDate> = _weekStart.asStateFlow()

    val tasks: StateFlow<List<Task>> = _selectedDate
        .flatMapLatest { repo.getTasksForDate(it) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    val datesWithTasks: StateFlow<Set<LocalDate>> = _weekStart
        .flatMapLatest { start ->
            repo.getDatesWithTasks(start, start.plusDays(6))
                .map { list -> list.map { LocalDate.parse(it) }.toSet() }
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptySet())

    fun selectDate(date: LocalDate) { _selectedDate.value = date }
    fun previousWeek() { _weekStart.value = _weekStart.value.minusWeeks(1) }
    fun nextWeek() { _weekStart.value = _weekStart.value.plusWeeks(1) }

    fun toggleDone(task: Task) = viewModelScope.launch {
        repo.update(task.copy(isDone = !task.isDone))
    }

    fun deleteTask(task: Task) = viewModelScope.launch {
        TaskReminderWorker.cancel(getApplication(), task.id)
        repo.delete(task)
    }
}
