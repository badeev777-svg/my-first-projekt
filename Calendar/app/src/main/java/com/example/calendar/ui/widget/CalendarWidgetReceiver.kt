package com.example.calendar.ui.widget

import android.content.Context
import android.content.Intent
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.GlanceAppWidgetReceiver
import androidx.glance.appwidget.updateAll
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class CalendarWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = CalendarWidget()

    override fun onReceive(context: Context, intent: Intent) {
        super.onReceive(context, intent)
        if (intent.action == Intent.ACTION_DATE_CHANGED) {
            CoroutineScope(Dispatchers.IO).launch {
                CalendarWidget().updateAll(context)
            }
        }
    }
}
