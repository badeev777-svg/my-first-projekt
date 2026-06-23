package com.example.calendar.data

import androidx.room.*
import com.example.calendar.domain.Task
import kotlinx.coroutines.flow.Flow

@Dao
interface TaskDao {
    @Query("SELECT * FROM tasks WHERE date = :date ORDER BY CASE WHEN time IS NULL THEN 1 ELSE 0 END ASC, time ASC")
    fun getTasksForDate(date: String): Flow<List<Task>>

    @Query("SELECT * FROM tasks WHERE date = :date ORDER BY CASE WHEN time IS NULL THEN 1 ELSE 0 END ASC, time ASC")
    suspend fun getTasksForDateOnce(date: String): List<Task>

    @Query("SELECT DISTINCT date FROM tasks WHERE date BETWEEN :from AND :to")
    fun getDatesWithTasks(from: String, to: String): Flow<List<String>>

    @Insert
    suspend fun insert(task: Task): Long

    @Update
    suspend fun update(task: Task)

    @Delete
    suspend fun delete(task: Task)

    @Query("UPDATE tasks SET isDone = 1 - isDone WHERE id = :id")
    suspend fun toggleDone(id: Int): Int

    @Query("DELETE FROM tasks WHERE id = :id")
    suspend fun deleteById(id: Int)
}
