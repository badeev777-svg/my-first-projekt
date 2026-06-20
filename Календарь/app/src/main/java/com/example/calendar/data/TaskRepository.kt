package com.example.calendar.data

import com.example.calendar.domain.Task
import kotlinx.coroutines.flow.Flow
import java.time.LocalDate

class TaskRepository(private val dao: TaskDao) {

    fun getTasksForDate(date: LocalDate): Flow<List<Task>> =
        dao.getTasksForDate(date.toString())

    suspend fun getTasksForDateOnce(date: LocalDate): List<Task> =
        dao.getTasksForDateOnce(date.toString())

    fun getDatesWithTasks(from: LocalDate, to: LocalDate): Flow<List<String>> =
        dao.getDatesWithTasks(from.toString(), to.toString())

    suspend fun insert(task: Task): Long = dao.insert(task)

    suspend fun update(task: Task) = dao.update(task)

    suspend fun delete(task: Task) = dao.delete(task)
}
