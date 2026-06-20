package com.example.calendar.ui.widget

import android.content.Context
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.GlanceTheme
import androidx.glance.Image
import androidx.glance.ImageProvider
import androidx.glance.action.actionParametersOf
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.action.actionRunCallback
import androidx.glance.appwidget.cornerRadius
import androidx.glance.appwidget.provideContent
import androidx.glance.background
import androidx.glance.layout.Alignment
import androidx.glance.layout.Box
import androidx.glance.layout.Column
import androidx.glance.layout.ContentScale
import androidx.glance.layout.Row
import androidx.glance.layout.Spacer
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.fillMaxWidth
import androidx.glance.layout.height
import androidx.glance.layout.padding
import androidx.glance.layout.size
import androidx.glance.layout.width
import androidx.glance.layout.defaultWeight
import androidx.glance.state.GlanceStateDefinition
import androidx.glance.state.PreferencesGlanceStateDefinition
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextDecoration
import androidx.glance.text.TextStyle
import androidx.glance.unit.ColorProvider
import com.example.calendar.R
import com.example.calendar.data.TaskRepository
import com.example.calendar.data.db.TaskDatabase
import com.example.calendar.domain.Task
import java.time.DayOfWeek
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.format.TextStyle as JTextStyle
import java.util.Locale

class CalendarWidget : GlanceAppWidget() {

    override val stateDefinition: GlanceStateDefinition<*> = PreferencesGlanceStateDefinition

    companion object {
        val KEY_SELECTED_DATE = stringPreferencesKey("selected_date")
    }

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        val repo = TaskRepository(TaskDatabase.getInstance(context).taskDao())
        val prefs = currentState<androidx.datastore.preferences.core.Preferences>(context, id)
        val dateStr = prefs[KEY_SELECTED_DATE] ?: LocalDate.now().toString()
        val tasks = repo.getTasksForDateOnce(LocalDate.parse(dateStr))

        provideContent {
            WidgetContent(dateStr, tasks)
        }
    }
}

@androidx.glance.GlanceComposable
@androidx.compose.runtime.Composable
private fun WidgetContent(selectedDate: String, tasks: List<Task>) {
    val date = LocalDate.parse(selectedDate)
    val weekStart = date.with(DayOfWeek.MONDAY)
    val days = (0..6).map { weekStart.plusDays(it.toLong()) }

    val pink      = ColorProvider(Color(0xFFE05C7A))
    val white     = ColorProvider(Color(0xFFFFFFFF))
    val dimWhite  = ColorProvider(Color(0xFFBBBBBB))

    Box(
        modifier = GlanceModifier
            .fillMaxSize()
            .background(ImageProvider(R.drawable.widget_bg))
            .cornerRadius(20)
    ) {
        Column(
            modifier = GlanceModifier
                .fillMaxSize()
                .padding(horizontal = 14.dp, vertical = 12.dp)
        ) {
            // Week strip
            Row(modifier = GlanceModifier.fillMaxWidth()) {
                days.forEachIndexed { index, day ->
                    val isSelected = day == date
                    val dayName = day.dayOfWeek
                        .getDisplayName(JTextStyle.SHORT, Locale("ru"))
                        .lowercase()
                        .take(2)

                    Box(
                        modifier = GlanceModifier
                            .defaultWeight()
                            .height(46.dp)
                            .background(
                                if (isSelected) pink
                                else ColorProvider(Color(0x33FFFFFF))
                            )
                            .cornerRadius(10)
                            .clickable(
                                actionRunCallback<SelectDateCallback>(
                                    actionParametersOf(KEY_DATE to day.toString())
                                )
                            ),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Text(
                                dayName,
                                style = TextStyle(
                                    color = if (isSelected) ColorProvider(Color(0xFFFFD0DB)) else dimWhite,
                                    fontSize = 9.sp
                                )
                            )
                            Text(
                                day.dayOfMonth.toString(),
                                style = TextStyle(
                                    color = white,
                                    fontSize = 13.sp,
                                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal
                                )
                            )
                        }
                    }
                    if (index < 6) Spacer(GlanceModifier.width(3.dp))
                }
            }

            Spacer(GlanceModifier.height(10.dp))

            // Date header + add button
            Row(
                modifier = GlanceModifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = GlanceModifier.defaultWeight()) {
                    val isToday = date == LocalDate.now()
                    Text(
                        if (isToday) "СЕГОДНЯ"
                        else date.dayOfWeek.getDisplayName(JTextStyle.FULL, Locale("ru")).uppercase(),
                        style = TextStyle(color = pink, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                    )
                    Text(
                        date.format(DateTimeFormatter.ofPattern("d MMMM", Locale("ru"))),
                        style = TextStyle(color = dimWhite, fontSize = 11.sp)
                    )
                }
                Box(
                    modifier = GlanceModifier
                        .size(28.dp)
                        .background(pink)
                        .cornerRadius(50)
                        .clickable(
                            actionRunCallback<AddTaskCallback>(
                                actionParametersOf(KEY_DATE to date.toString())
                            )
                        ),
                    contentAlignment = Alignment.Center
                ) {
                    Text("+", style = TextStyle(color = white, fontSize = 18.sp))
                }
            }

            Spacer(GlanceModifier.height(8.dp))

            // Divider
            Box(
                modifier = GlanceModifier
                    .fillMaxWidth()
                    .height(1.dp)
                    .background(ColorProvider(Color(0x33FFFFFF)))
            ) {}

            Spacer(GlanceModifier.height(8.dp))

            // Task list
            if (tasks.isEmpty()) {
                Text(
                    "Нет задач на этот день",
                    style = TextStyle(color = dimWhite, fontSize = 12.sp)
                )
            } else {
                tasks.take(5).forEach { task ->
                    TaskRow(task, date.toString())
                    Spacer(GlanceModifier.height(6.dp))
                }
            }
        }
    }
}

@androidx.glance.GlanceComposable
@androidx.compose.runtime.Composable
private fun TaskRow(task: Task, dateStr: String) {
    val pink      = ColorProvider(Color(0xFFE05C7A))
    val textColor = if (task.isDone) ColorProvider(Color(0xFF555555)) else ColorProvider(Color(0xFFEEEEEE))
    val subtextColor = ColorProvider(Color(0xFF999999))

    Row(
        modifier = GlanceModifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = GlanceModifier
                .size(16.dp)
                .cornerRadius(4)
                .clickable(
                    actionRunCallback<ToggleDoneCallback>(
                        actionParametersOf(KEY_TASK_ID to task.id)
                    )
                ),
            contentAlignment = Alignment.Center
        ) {
            Text(
                if (task.isDone) "✓" else "□",
                style = TextStyle(
                    color = if (task.isDone) ColorProvider(Color(0xFF888888)) else pink,
                    fontSize = if (task.isDone) 11.sp else 14.sp
                )
            )
        }

        Spacer(GlanceModifier.width(8.dp))

        Column(
            modifier = GlanceModifier
                .defaultWeight()
                .clickable(
                    actionRunCallback<OpenDateCallback>(
                        actionParametersOf(KEY_DATE to dateStr)
                    )
                )
        ) {
            Text(
                task.title,
                style = TextStyle(
                    color = textColor,
                    fontSize = 12.sp,
                    textDecoration = if (task.isDone) TextDecoration.LineThrough else TextDecoration.None
                ),
                maxLines = 1
            )
            if (task.time != null) {
                Text(
                    task.time,
                    style = TextStyle(color = subtextColor, fontSize = 10.sp)
                )
            }
        }
    }
}
