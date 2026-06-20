package com.example.calendar.domain

import androidx.room.Entity
import androidx.room.PrimaryKey

// date хранится как "2026-06-20", time как "15:00" или null
@Entity(tableName = "tasks")
data class Task(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val title: String,
    val date: String,
    val time: String? = null,
    val isDone: Boolean = false
)
