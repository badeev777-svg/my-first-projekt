package com.example.calendar.data

import androidx.room.*
import com.example.calendar.domain.Task
import kotlinx.coroutines.flow.Flow

@Dao
interface TaskDao {
    @Query("SELECT * FROM tasks WHERE date = :date ORDER BY time ASC NULLS LAST")
    fun getTasksForDate(date: String): Flow<List<Task>>

    @Query("SELECT * FROM tasks WHERE date = :date ORDER BY time ASC NULLS LAST")
    suspend fun getTasksForDateOnce(date: String): List<Task>

    @Query("SELECT DISTINCT date FROM tasks WHERE date BETWEEN :from AND :to")
    fun getDatesWithTasks(from: String, to: String): Flow<List<String>>

    @Insert
    suspend fun insert(task: Task): Long

    @Update
    suspend fun update(task: Task)

    @Delete
    suspend fun delete(task: Task)
}
