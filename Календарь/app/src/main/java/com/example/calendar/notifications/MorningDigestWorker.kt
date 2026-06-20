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

        // Reschedule for tomorrow 9:00
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
