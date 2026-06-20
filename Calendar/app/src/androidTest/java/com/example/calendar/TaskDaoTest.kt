package com.example.calendar

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.example.calendar.data.db.TaskDatabase
import com.example.calendar.domain.Task
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class TaskDaoTest {
    private lateinit var db: TaskDatabase

    @Before fun setup() {
        db = Room.inMemoryDatabaseBuilder(
            ApplicationProvider.getApplicationContext(), TaskDatabase::class.java
        ).allowMainThreadQueries().build()
    }

    @After fun teardown() { db.close() }

    @Test fun insertAndQueryByDate() = runTest {
        val task = Task(title = "Тест", date = "2026-06-20")
        db.taskDao().insert(task)
        val tasks = db.taskDao().getTasksForDate("2026-06-20").first()
        assertEquals(1, tasks.size)
        assertEquals("Тест", tasks[0].title)
    }

    @Test fun toggleDone() = runTest {
        db.taskDao().insert(Task(title = "Задача", date = "2026-06-20"))
        val task = db.taskDao().getTasksForDateOnce("2026-06-20").first()
        db.taskDao().update(task.copy(isDone = true))
        val updated = db.taskDao().getTasksForDateOnce("2026-06-20").first()
        assertTrue(updated.isDone)
    }
}
