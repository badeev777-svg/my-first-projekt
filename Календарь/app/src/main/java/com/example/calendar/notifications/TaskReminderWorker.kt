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
