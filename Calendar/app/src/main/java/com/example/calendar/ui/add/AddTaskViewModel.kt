package com.example.calendar.ui.add

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.glance.appwidget.updateAll
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.calendar.data.TaskRepository
import com.example.calendar.data.db.TaskDatabase
import com.example.calendar.domain.Task
import com.example.calendar.notifications.TaskReminderWorker
import com.example.calendar.ui.widget.CalendarWidget
import kotlinx.coroutines.launch
import java.time.LocalDate

class AddTaskViewModel(app: Application) : AndroidViewModel(app) {

    private val repo = TaskRepository(TaskDatabase.getInstance(app).taskDao())

    var title by mutableStateOf("")
        private set
    var date by mutableStateOf(LocalDate.now())
        private set
    var time by mutableStateOf<String?>(null)
        private set

    fun initDate(dateStr: String) {
        date = LocalDate.parse(dateStr)
    }

    fun onTitleChange(value: String) { title = value }
    fun onDateChange(value: LocalDate) { date = value }
    fun onTimeChange(value: String?) { time = value }

    fun save(onDone: () -> Unit) {
        if (title.isBlank()) return
        viewModelScope.launch {
            val id = repo.insert(
                Task(title = title.trim(), date = date.toString(), time = time)
            )
            if (time != null) {
                val task = Task(
                    id = id.toInt(),
                    title = title.trim(),
                    date = date.toString(),
                    time = time
                )
                TaskReminderWorker.schedule(getApplication(), task)
            }
            CalendarWidget().updateAll(getApplication())
            onDone()
        }
    }
}
