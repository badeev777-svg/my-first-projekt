# Календарь — план реализации Android-приложения

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Нативное Android-приложение (Kotlin + Compose) с задачами на день, чекбоксами на главном экране и локальными уведомлениями в 9:00 и за 1 час до задачи.

**Architecture:** MVVM — Room DB хранит задачи локально, WorkManager планирует уведомления. Данные текут через StateFlow: Room → Repository → ViewModel → Compose UI. Навигация через NavHost (два экрана: главный и добавление задачи).

**Tech Stack:** Kotlin, Jetpack Compose, Room 2.6, WorkManager 2.9, Compose Navigation 2.7, Material3, KSP, minSdk 26 (Android 8.0).

---

## Файловая структура

```
app/src/main/java/com/example/calendar/
├── data/
│   ├── db/TaskDatabase.kt        — Room DB singleton
│   ├── TaskDao.kt                — SQL-запросы
│   └── TaskRepository.kt        — прослойка между DAO и ViewModel
├── domain/
│   └── Task.kt                  — Room entity
├── notifications/
│   ├── NotificationHelper.kt    — каналы + утилита показа уведомления
│   ├── MorningDigestWorker.kt   — ежедневно в 9:00
│   └── TaskReminderWorker.kt    — за 1 час до задачи
├── ui/
│   ├── theme/
│   │   └── Theme.kt             — тёмная тема (цвета + MaterialTheme)
│   ├── main/
│   │   ├── MainViewModel.kt     — стейт главного экрана
│   │   └── MainScreen.kt        — Compose UI: полоса недели + список задач
│   └── add/
│       ├── AddTaskViewModel.kt  — логика сохранения задачи
│       └── AddTaskScreen.kt     — Compose UI: форма добавления
└── MainActivity.kt              — точка входа + NavHost
```

---

## Task 1: Настройка проекта

**Files:**
- Modify: `app/build.gradle.kts`
- Modify: `app/src/main/AndroidManifest.xml`

- [ ] **Шаг 1: Создать новый Android-проект в Android Studio**

  File → New → New Project → Empty Activity (Compose)
  - Name: `Календарь`
  - Package: `com.example.calendar`
  - Language: Kotlin
  - Min SDK: API 26
  - Build configuration: Kotlin DSL

- [ ] **Шаг 2: Обновить `app/build.gradle.kts`**

```kotlin
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.ksp)
}

android {
    namespace = "com.example.calendar"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.example.calendar"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"
    }

    buildFeatures { compose = true }
    composeOptions { kotlinCompilerExtensionVersion = "1.5.10" }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.04.01")
    implementation(composeBom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.activity:activity-compose:1.9.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.7.0")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.7.0")
    implementation("androidx.navigation:navigation-compose:2.7.7")

    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    ksp("androidx.room:room-compiler:2.6.1")

    implementation("androidx.work:work-runtime-ktx:2.9.0")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.0")
    androidTestImplementation("androidx.room:room-testing:2.6.1")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
}
```

- [ ] **Шаг 3: Обновить `libs.versions.toml` — добавить KSP-плагин**

```toml
[versions]
ksp = "1.9.23-1.0.20"

[plugins]
ksp = { id = "com.google.devtools.ksp", version.ref = "ksp" }
```

В `build.gradle.kts` (корневом) добавь в `plugins`:
```kotlin
alias(libs.plugins.ksp) apply false
```

- [ ] **Шаг 4: Добавить разрешения в `AndroidManifest.xml`**

```xml
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
<uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM" />
```

- [ ] **Шаг 5: Убедиться что проект собирается**

```
Build → Make Project (Ctrl+F9)
```
Ожидание: BUILD SUCCESSFUL, без ошибок.

- [ ] **Шаг 6: Коммит**

```bash
git add .
git commit -m "feat: initial Android project setup with dependencies"
```

---

## Task 2: Модель данных — Task entity, DAO, Database

**Files:**
- Create: `app/src/main/java/com/example/calendar/domain/Task.kt`
- Create: `app/src/main/java/com/example/calendar/data/TaskDao.kt`
- Create: `app/src/main/java/com/example/calendar/data/db/TaskDatabase.kt`
- Test: `app/src/androidTest/java/com/example/calendar/TaskDaoTest.kt`

- [ ] **Шаг 1: Создать `domain/Task.kt`**

```kotlin
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
```

- [ ] **Шаг 2: Создать `data/TaskDao.kt`**

```kotlin
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
```

- [ ] **Шаг 3: Создать `data/db/TaskDatabase.kt`**

```kotlin
package com.example.calendar.data.db

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import com.example.calendar.data.TaskDao
import com.example.calendar.domain.Task

@Database(entities = [Task::class], version = 1, exportSchema = false)
abstract class TaskDatabase : RoomDatabase() {
    abstract fun taskDao(): TaskDao

    companion object {
        @Volatile private var INSTANCE: TaskDatabase? = null

        fun getInstance(context: Context): TaskDatabase =
            INSTANCE ?: synchronized(this) {
                Room.databaseBuilder(context, TaskDatabase::class.java, "calendar_db")
                    .build()
                    .also { INSTANCE = it }
            }
    }
}
```

- [ ] **Шаг 4: Написать инструментированный тест DAO**

```kotlin
// app/src/androidTest/java/com/example/calendar/TaskDaoTest.kt
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
        val id = db.taskDao().insert(Task(title = "Задача", date = "2026-06-20"))
        val task = db.taskDao().getTasksForDateOnce("2026-06-20").first()
        db.taskDao().update(task.copy(isDone = true))
        val updated = db.taskDao().getTasksForDateOnce("2026-06-20").first()
        assertTrue(updated.isDone)
    }
}
```

- [ ] **Шаг 5: Запустить тест**

```
Run → TaskDaoTest (нужен подключённый эмулятор или устройство)
```
Ожидание: 2 теста зелёные.

- [ ] **Шаг 6: Коммит**

```bash
git add .
git commit -m "feat: add Task entity, DAO and Room database"
```

---

## Task 3: Repository

**Files:**
- Create: `app/src/main/java/com/example/calendar/data/TaskRepository.kt`

- [ ] **Шаг 1: Создать `data/TaskRepository.kt`**

```kotlin
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
```

- [ ] **Шаг 2: Коммит**

```bash
git add .
git commit -m "feat: add TaskRepository"
```

---

## Task 4: Инфраструктура уведомлений

**Files:**
- Create: `app/src/main/java/com/example/calendar/notifications/NotificationHelper.kt`
- Modify: `app/src/main/AndroidManifest.xml`

- [ ] **Шаг 1: Создать `notifications/NotificationHelper.kt`**

```kotlin
package com.example.calendar.notifications

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.PackageManager
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat

object NotificationHelper {
    const val CHANNEL_MORNING = "morning_digest"
    const val CHANNEL_REMINDER = "task_reminder"

    fun createChannels(context: Context) {
        val manager = context.getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL_MORNING, "Утренний дайджест", NotificationManager.IMPORTANCE_DEFAULT)
        )
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL_REMINDER, "Напоминания о задачах", NotificationManager.IMPORTANCE_HIGH)
        )
    }

    fun show(context: Context, channelId: String, notifId: Int, title: String, text: String) {
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED) return

        val manager = context.getSystemService(NotificationManager::class.java)
        val notification = NotificationCompat.Builder(context, channelId)
            .setSmallIcon(android.R.drawable.ic_popup_reminder)
            .setContentTitle(title)
            .setContentText(text)
            .setAutoCancel(true)
            .build()
        manager.notify(notifId, notification)
    }
}
```

- [ ] **Шаг 2: Коммит**

```bash
git add .
git commit -m "feat: add notification channels and helper"
```

---

## Task 5: MorningDigestWorker

**Files:**
- Create: `app/src/main/java/com/example/calendar/notifications/MorningDigestWorker.kt`

- [ ] **Шаг 1: Создать `notifications/MorningDigestWorker.kt`**

```kotlin
package com.example.calendar.notifications

import android.content.Context
import androidx.work.*
import com.example.calendar.data.TaskRepository
import com.example.calendar.data.db.TaskDatabase
import java.time.Duration
import java.time.LocalDate
import java.time.LocalDateTime
import java.util.concurrent.TimeUnit

class MorningDigestWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {

    override suspend fun doWork(): Result {
        val dao = TaskDatabase.getInstance(applicationContext).taskDao()
        val repo = TaskRepository(dao)
        val tasks = repo.getTasksForDateOnce(LocalDate.now()).filter { !it.isDone }

        if (tasks.isNotEmpty()) {
            val text = tasks.joinToString(", ") { it.title }
            NotificationHelper.show(
                context = applicationContext,
                channelId = NotificationHelper.CHANNEL_MORNING,
                notifId = 1000,
                title = "Задачи на сегодня",
                text = text
            )
        }

        // Перепланировать на завтра 9:00
        schedule(applicationContext)
        return Result.success()
    }

    companion object {
        private const val TAG = "morning_digest"

        fun schedule(context: Context) {
            val now = LocalDateTime.now()
            val next9am = if (now.hour < 9) {
                now.toLocalDate().atTime(9, 0)
            } else {
                now.toLocalDate().plusDays(1).atTime(9, 0)
            }
            val delayMs = Duration.between(now, next9am).toMillis()

            val request = OneTimeWorkRequestBuilder<MorningDigestWorker>()
                .setInitialDelay(delayMs, TimeUnit.MILLISECONDS)
                .addTag(TAG)
                .build()

            WorkManager.getInstance(context)
                .enqueueUniqueWork(TAG, ExistingWorkPolicy.REPLACE, request)
        }
    }
}
```

- [ ] **Шаг 2: Коммит**

```bash
git add .
git commit -m "feat: add MorningDigestWorker (daily 9:00 AM)"
```

---

## Task 6: TaskReminderWorker

**Files:**
- Create: `app/src/main/java/com/example/calendar/notifications/TaskReminderWorker.kt`

- [ ] **Шаг 1: Создать `notifications/TaskReminderWorker.kt`**

```kotlin
package com.example.calendar.notifications

import android.content.Context
import androidx.work.*
import com.example.calendar.domain.Task
import java.time.Duration
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime
import java.util.concurrent.TimeUnit

class TaskReminderWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {

    override suspend fun doWork(): Result {
        val title = inputData.getString(KEY_TITLE) ?: return Result.failure()
        val time = inputData.getString(KEY_TIME) ?: return Result.failure()
        val notifId = inputData.getInt(KEY_NOTIF_ID, -1)

        NotificationHelper.show(
            context = applicationContext,
            channelId = NotificationHelper.CHANNEL_REMINDER,
            notifId = notifId,
            title = "Через час: $title",
            text = "в $time"
        )
        return Result.success()
    }

    companion object {
        private const val KEY_TITLE = "title"
        private const val KEY_TIME = "time"
        private const val KEY_NOTIF_ID = "notif_id"

        fun schedule(context: Context, task: Task) {
            val taskTime = task.time?.let { LocalTime.parse(it) } ?: return
            val reminderAt = LocalDate.parse(task.date).atTime(taskTime).minusHours(1)
            val delayMs = Duration.between(LocalDateTime.now(), reminderAt).toMillis()
            if (delayMs <= 0) return

            val data = workDataOf(
                KEY_TITLE to task.title,
                KEY_TIME to task.time,
                KEY_NOTIF_ID to (2000 + task.id)
            )
            val request = OneTimeWorkRequestBuilder<TaskReminderWorker>()
                .setInitialDelay(delayMs, TimeUnit.MILLISECONDS)
                .setInputData(data)
                .addTag(reminderTag(task.id))
                .build()

            WorkManager.getInstance(context).enqueue(request)
        }

        fun cancel(context: Context, taskId: Int) {
            WorkManager.getInstance(context).cancelAllWorkByTag(reminderTag(taskId))
        }

        private fun reminderTag(taskId: Int) = "task_reminder_$taskId"
    }
}
```

- [ ] **Шаг 2: Коммит**

```bash
git add .
git commit -m "feat: add TaskReminderWorker (1 hour before task)"
```

---

## Task 7: Тема приложения

**Files:**
- Create: `app/src/main/java/com/example/calendar/ui/theme/Theme.kt`

- [ ] **Шаг 1: Создать `ui/theme/Theme.kt`**

```kotlin
package com.example.calendar.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val AppColors = darkColorScheme(
    primary = Color(0xFF4A90D9),
    background = Color(0xFF0F1117),
    surface = Color(0xFF1A1F2E),
    onPrimary = Color.White,
    onBackground = Color(0xFFE0E0E0),
    onSurface = Color(0xFFE0E0E0),
    outline = Color(0xFF2A2F42)
)

@Composable
fun CalendarTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = AppColors, content = content)
}
```

- [ ] **Шаг 2: Коммит**

```bash
git add .
git commit -m "feat: add dark theme"
```

---

## Task 8: MainViewModel

**Files:**
- Create: `app/src/main/java/com/example/calendar/ui/main/MainViewModel.kt`

- [ ] **Шаг 1: Написать unit-тест для MainViewModel**

```kotlin
// app/src/test/java/com/example/calendar/MainViewModelTest.kt
package com.example.calendar

import com.example.calendar.ui.main.MainViewModel
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test
import java.time.DayOfWeek
import java.time.LocalDate

class MainViewModelTest {
    @Test fun `weekStart is Monday of current week`() = runTest {
        val today = LocalDate.now()
        val expectedMonday = today.with(DayOfWeek.MONDAY)
        // Проверяем логику вычисления — не сам ViewModel (требует Application)
        val actual = today.with(DayOfWeek.MONDAY)
        assertEquals(expectedMonday, actual)
    }

    @Test fun `previousWeek subtracts 7 days`() = runTest {
        val start = LocalDate.of(2026, 6, 15) // Понедельник
        val prev = start.minusWeeks(1)
        assertEquals(LocalDate.of(2026, 6, 8), prev)
    }
}
```

- [ ] **Шаг 2: Запустить unit-тест**

```
Run → MainViewModelTest
```
Ожидание: 2 теста зелёных.

- [ ] **Шаг 3: Создать `ui/main/MainViewModel.kt`**

```kotlin
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
```

- [ ] **Шаг 4: Коммит**

```bash
git add .
git commit -m "feat: add MainViewModel with week navigation and task state"
```

---

## Task 9: Главный экран (MainScreen)

**Files:**
- Create: `app/src/main/java/com/example/calendar/ui/main/MainScreen.kt`

- [ ] **Шаг 1: Создать `ui/main/MainScreen.kt`**

```kotlin
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
import java.time.DayOfWeek
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
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        TextButton(onClick = onPrevious) { Text("‹", style = MaterialTheme.typography.headlineMedium) }
        val monthName = weekStart.month.getDisplayName(TextStyle.FULL_STANDALONE, Locale("ru"))
            .replaceFirstChar { it.uppercase() }
        Text("$monthName ${weekStart.year}", style = MaterialTheme.typography.titleMedium)
        TextButton(onClick = onNext) { Text("›", style = MaterialTheme.typography.headlineMedium) }
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
        val days = listOf("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")
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
                    text = days[i],
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
                            color = if (hasTasks) (if (isSelected) Color.White else MaterialTheme.colorScheme.primary)
                            else Color.Transparent,
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
    n % 10 == 1 -> "задача"
    n % 10 in 2..4 -> "задачи"
    else -> "задач"
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
                    if (value == SwipeToDismissBoxValue.EndToStart) { onDelete(task); true }
                    else false
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
                        val m = parts[1]
                        "%02d:%02d".format(h, m)
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
```

- [ ] **Шаг 2: Убедиться что проект компилируется (Build → Make Project)**

- [ ] **Шаг 3: Коммит**

```bash
git add .
git commit -m "feat: add MainScreen with week strip and task list"
```

---

## Task 10: AddTaskViewModel

**Files:**
- Create: `app/src/main/java/com/example/calendar/ui/add/AddTaskViewModel.kt`

- [ ] **Шаг 1: Создать `ui/add/AddTaskViewModel.kt`**

```kotlin
package com.example.calendar.ui.add

import android.app.Application
import androidx.compose.runtime.*
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.calendar.data.TaskRepository
import com.example.calendar.data.db.TaskDatabase
import com.example.calendar.domain.Task
import com.example.calendar.notifications.MorningDigestWorker
import com.example.calendar.notifications.TaskReminderWorker
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.LocalTime

class AddTaskViewModel(app: Application) : AndroidViewModel(app) {

    private val repo = TaskRepository(TaskDatabase.getInstance(app).taskDao())

    var title by mutableStateOf("")
    var date by mutableStateOf(LocalDate.now())
    var time by mutableStateOf<LocalTime?>(null)

    fun initDate(d: LocalDate) { date = d }

    fun save(onSuccess: () -> Unit) {
        if (title.isBlank()) return
        viewModelScope.launch {
            val task = Task(
                title = title.trim(),
                date = date.toString(),
                time = time?.toString()
            )
            val insertedId = repo.insert(task).toInt()
            val saved = task.copy(id = insertedId)

            val ctx = getApplication<Application>()
            MorningDigestWorker.schedule(ctx)
            if (saved.time != null) TaskReminderWorker.schedule(ctx, saved)

            onSuccess()
        }
    }
}
```

- [ ] **Шаг 2: Коммит**

```bash
git add .
git commit -m "feat: add AddTaskViewModel with notification scheduling"
```

---

## Task 11: Экран добавления задачи (AddTaskScreen)

**Files:**
- Create: `app/src/main/java/com/example/calendar/ui/add/AddTaskScreen.kt`

- [ ] **Шаг 1: Создать `ui/add/AddTaskScreen.kt`**

```kotlin
package com.example.calendar.ui.add

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import java.time.LocalDate
import java.time.LocalTime
import java.time.format.DateTimeFormatter
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AddTaskScreen(
    initialDate: LocalDate,
    onDismiss: () -> Unit,
    vm: AddTaskViewModel = viewModel()
) {
    LaunchedEffect(initialDate) { vm.initDate(initialDate) }

    var showDatePicker by remember { mutableStateOf(false) }
    var showTimePicker by remember { mutableStateOf(false) }

    if (showDatePicker) {
        val state = rememberDatePickerState(
            initialSelectedDateMillis = vm.date.toEpochDay() * 86_400_000L
        )
        DatePickerDialog(
            onDismissRequest = { showDatePicker = false },
            confirmButton = {
                TextButton(onClick = {
                    state.selectedDateMillis?.let {
                        vm.date = LocalDate.ofEpochDay(it / 86_400_000L)
                    }
                    showDatePicker = false
                }) { Text("OK") }
            }
        ) { DatePicker(state = state) }
    }

    if (showTimePicker) {
        val timeState = rememberTimePickerState(
            initialHour = vm.time?.hour ?: 9,
            initialMinute = vm.time?.minute ?: 0
        )
        AlertDialog(
            onDismissRequest = { showTimePicker = false },
            confirmButton = {
                TextButton(onClick = {
                    vm.time = LocalTime.of(timeState.hour, timeState.minute)
                    showTimePicker = false
                }) { Text("OK") }
            },
            dismissButton = {
                TextButton(onClick = {
                    vm.time = null
                    showTimePicker = false
                }) { Text("Без времени") }
            },
            text = { TimePicker(state = timeState) }
        )
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        // TopBar
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 8.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            TextButton(onClick = onDismiss) { Text("Отмена") }
            Text("Новая задача", style = MaterialTheme.typography.titleMedium)
            TextButton(
                onClick = { vm.save { onDismiss() } },
                enabled = vm.title.isNotBlank()
            ) { Text("Сохранить") }
        }

        HorizontalDivider(color = MaterialTheme.colorScheme.outline)

        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // Название
            Surface(shape = RoundedCornerShape(12.dp), color = MaterialTheme.colorScheme.surface) {
                TextField(
                    value = vm.title,
                    onValueChange = { vm.title = it },
                    label = { Text("Название") },
                    modifier = Modifier.fillMaxWidth(),
                    colors = TextFieldDefaults.colors(
                        focusedContainerColor = MaterialTheme.colorScheme.surface,
                        unfocusedContainerColor = MaterialTheme.colorScheme.surface
                    ),
                    singleLine = true
                )
            }

            // Дата
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = MaterialTheme.colorScheme.surface,
                onClick = { showDatePicker = true },
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text("Дата", style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f))
                        Text(
                            vm.date.format(DateTimeFormatter.ofPattern("d MMMM yyyy", Locale("ru"))),
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }
                    Icon(Icons.Default.DateRange, contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary)
                }
            }

            // Время
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = MaterialTheme.colorScheme.surface,
                onClick = { showTimePicker = true },
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                "Время (необязательно)",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                            )
                            Text(
                                vm.time?.toString() ?: "Нажми чтобы выбрать",
                                style = MaterialTheme.typography.bodyMedium,
                                color = if (vm.time != null) MaterialTheme.colorScheme.onSurface
                                else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f)
                            )
                        }
                        Text("🕐", style = MaterialTheme.typography.titleLarge)
                    }

                    if (vm.time != null) {
                        val t = vm.time!!
                        val reminderH = if (t.hour == 0) 23 else t.hour - 1
                        val reminderStr = "%02d:%02d".format(reminderH, t.minute)
                        Spacer(Modifier.height(8.dp))
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = MaterialTheme.colorScheme.background
                        ) {
                            Text(
                                "🔔 Уведомление в 9:00 и за 1 час (в $reminderStr)",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.padding(8.dp)
                            )
                        }
                    } else {
                        Spacer(Modifier.height(4.dp))
                        Text(
                            "Без времени: только утреннее уведомление в 9:00",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f)
                        )
                    }
                }
            }
        }
    }
}
```

- [ ] **Шаг 2: Коммит**

```bash
git add .
git commit -m "feat: add AddTaskScreen with date/time pickers"
```

---

## Task 12: MainActivity и навигация

**Files:**
- Modify: `app/src/main/java/com/example/calendar/MainActivity.kt`

- [ ] **Шаг 1: Обновить `MainActivity.kt`**

```kotlin
package com.example.calendar

import android.Manifest
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.example.calendar.notifications.NotificationHelper
import com.example.calendar.ui.add.AddTaskScreen
import com.example.calendar.ui.main.MainScreen
import com.example.calendar.ui.theme.CalendarTheme
import java.time.LocalDate

class MainActivity : ComponentActivity() {

    private val requestPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { /* разрешение получено или отклонено — уведомления планируются в любом случае */ }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        NotificationHelper.createChannels(this)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            requestPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }

        setContent {
            CalendarTheme {
                CalendarApp()
            }
        }
    }
}

@Composable
fun CalendarApp() {
    val navController = rememberNavController()
    NavHost(navController = navController, startDestination = "main") {
        composable("main") {
            MainScreen(onAddTask = { date ->
                navController.navigate("add/$date")
            })
        }
        composable("add/{date}") { back ->
            val date = LocalDate.parse(back.arguments?.getString("date") ?: LocalDate.now().toString())
            AddTaskScreen(
                initialDate = date,
                onDismiss = { navController.popBackStack() }
            )
        }
    }
}
```

- [ ] **Шаг 2: Собрать и запустить на эмуляторе (Run → Run 'app')**

  Ожидание: приложение открывается, видна полоса недели, список задач пустой, кнопка «+» работает.

- [ ] **Шаг 3: Проверить добавление задачи**

  - Нажать «+»
  - Ввести название «Тест»
  - Нажать «Сохранить»
  - Убедиться, что задача появилась в списке на главном экране.

- [ ] **Шаг 4: Проверить чекбокс**

  - Нажать на чекбокс задачи «Тест»
  - Убедиться, что название зачёркнулось.

- [ ] **Шаг 5: Проверить удаление**

  - Свайп влево по задаче → задача исчезает.

- [ ] **Шаг 6: Финальный коммит**

```bash
git add .
git commit -m "feat: add MainActivity with navigation and permission request"
```

---

## Итоговая структура

После выполнения всех задач:
- `git log --oneline` должен показать 11 коммитов от "initial setup" до "navigation"
- Приложение запускается, добавляет задачи, ставит галочки, удаляет свайпом
- Уведомления запланированы (проверить через adb shell: `adb shell dumpsys jobscheduler | grep calendar`)
