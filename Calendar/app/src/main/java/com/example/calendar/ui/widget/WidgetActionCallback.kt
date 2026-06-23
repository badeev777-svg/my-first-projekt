package com.example.calendar.ui.widget

import android.content.Context
import android.content.Intent
import androidx.glance.GlanceId
import androidx.glance.action.ActionParameters
import androidx.glance.appwidget.action.ActionCallback
import androidx.glance.appwidget.state.updateAppWidgetState
import androidx.glance.appwidget.updateAll
import androidx.glance.state.PreferencesGlanceStateDefinition
import com.example.calendar.MainActivity
import com.example.calendar.data.TaskRepository
import com.example.calendar.data.db.TaskDatabase

val KEY_DATE    = ActionParameters.Key<String>("selected_date")
val KEY_TASK_ID = ActionParameters.Key<Int>("task_id")

class SelectDateCallback : ActionCallback {
    override suspend fun onAction(context: Context, glanceId: GlanceId, parameters: ActionParameters) {
        val date = parameters[KEY_DATE] ?: return
        updateAppWidgetState(context, PreferencesGlanceStateDefinition, glanceId) { prefs ->
            prefs.toMutablePreferences().apply { set(CalendarWidget.KEY_SELECTED_DATE, date) }
        }
        CalendarWidget().update(context, glanceId)
    }
}

class ToggleDoneCallback : ActionCallback {
    override suspend fun onAction(context: Context, glanceId: GlanceId, parameters: ActionParameters) {
        val id = parameters[KEY_TASK_ID] ?: return
        val repo = TaskRepository(TaskDatabase.getInstance(context).taskDao())
        repo.toggleDone(id)
        CalendarWidget().updateAll(context)
    }
}

class OpenDateCallback : ActionCallback {
    override suspend fun onAction(context: Context, glanceId: GlanceId, parameters: ActionParameters) {
        val date = parameters[KEY_DATE] ?: return
        context.startActivity(
            Intent(context, MainActivity::class.java).apply {
                putExtra(MainActivity.EXTRA_DATE, date)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
            }
        )
    }
}

class DeleteTaskCallback : ActionCallback {
    override suspend fun onAction(context: Context, glanceId: GlanceId, parameters: ActionParameters) {
        val id = parameters[KEY_TASK_ID] ?: return
        val repo = TaskRepository(TaskDatabase.getInstance(context).taskDao())
        repo.deleteById(id)
        CalendarWidget().updateAll(context)
    }
}

class AddTaskCallback : ActionCallback {
    override suspend fun onAction(context: Context, glanceId: GlanceId, parameters: ActionParameters) {
        val date = parameters[KEY_DATE] ?: return
        context.startActivity(
            Intent(context, MainActivity::class.java).apply {
                putExtra(MainActivity.EXTRA_DATE, date)
                putExtra(MainActivity.EXTRA_ADD, true)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
            }
        )
    }
}
