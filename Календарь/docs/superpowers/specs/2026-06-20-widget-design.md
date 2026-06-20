# Home Screen Widget — Design Spec

## Overview

Android home screen widget for the Calendar app. Shows the current week strip and today's tasks with a crystal rose photo as the full background. Built with Jetpack Glance (Compose-based widget API).

---

## Visual Design

**Size:** 4×4 (large widget, spans most of the screen width)

**Background:** `rose.jpg` (crystal red rose photo) fills the entire widget via `ContentScale.Crop`. A gradient overlay darkens the top 55% heavily (text readable) and fades to near-transparent at the bottom (rose clearly visible).

Gradient: `top→bottom: rgba(5,0,15,0.90) → rgba(10,0,20,0.65) → rgba(0,0,0,0.15)`

**Theme:** Follows system (light/dark). In practice the gradient + rose works well in both — no explicit light branch needed.

**Layout (top to bottom):**
1. Week strip — 7 day columns, selected day highlighted in `#e05c7a`
2. Date label row — "СЕГОДНЯ / 20 июня" on the left, pink `+` FAB on the right
3. Divider line
4. Task list — up to 5 tasks; each row: checkbox + title + optional time subtitle

**Empty state:** Single centered label "Нет задач на этот день"

---

## Interactions

| Element | Action |
|---------|--------|
| Day column in week strip | Updates widget's selected date (stored in DataStore via GlanceStateDefinition); widget recomposes with tasks for that day |
| Checkbox on task | Toggles `task.isDone` in Room DB; refreshes widget |
| Task title tap | Opens `MainActivity` with the task's date as Intent extra (`EXTRA_DATE`) |
| `+` button | Opens `MainActivity` with the task's date and `EXTRA_ADD=true` so NavHost navigates to `add/{date}` |

---

## Architecture

### Files

| Path | Description |
|------|-------------|
| `ui/widget/CalendarWidgetReceiver.kt` | `GlanceAppWidgetReceiver` subclass — registers widget with Android |
| `ui/widget/CalendarWidget.kt` | `GlanceAppWidget` — composable UI, rose background, week strip, task list |
| `ui/widget/WidgetActionCallback.kt` | `ActionCallback` implementations for: toggle done, navigate to date, navigate to add |
| `res/drawable/rose.jpg` | Crystal rose photo (copy of the brainstorm asset) |
| `AndroidManifest.xml` | `<receiver>` entry + `appwidget-provider` metadata |
| `res/xml/widget_info.xml` | `AppWidgetProviderInfo`: minWidth/Height for 4×4, updatePeriodMillis=0 |

### Data Flow

```
Room DB (TaskDao)
    ↓  Flow<List<Task>>  (collected in CalendarWidget.Content)
CalendarWidget
    ↓  GlanceStateDefinition (DataStore)  — stores selectedDate: String
    ↑  WidgetActionCallback.SelectDate
         → GlanceAppWidgetManager.updateAll()

User taps checkbox
    → WidgetActionCallback.ToggleDone
        → TaskRepository.toggleDone(id)
        → GlanceAppWidgetManager.updateAll()

User taps task / + button
    → actionStartActivity<MainActivity>(Bundle(EXTRA_DATE, EXTRA_ADD))
```

### State

`GlanceStateDefinition` backed by DataStore Preferences:
- `KEY_SELECTED_DATE: String` — ISO date "2026-06-20", defaults to today

Widget refreshes on:
- `AppWidgetManager.ACTION_APPWIDGET_UPDATE` (system)
- After every `WidgetActionCallback` that mutates data

### Glance Composable Structure

```
Box (fillMaxSize) {
    Image(rose.jpg, contentScale = Crop)          // background
    Box(gradient overlay)                          // darkens top, fades bottom
    Column(padding 14.dp) {
        WeekStrip(weekDays, selectedDate)
        DateHeader(selectedDate, onAddClick)
        Divider
        TaskList(tasks)                            // up to 5 rows
        if (tasks.isEmpty) EmptyLabel
    }
}
```

---

## Manifest & Widget Info

`res/xml/widget_info.xml`:
```xml
<appwidget-provider
    android:minWidth="250dp"
    android:minHeight="250dp"
    android:targetCellWidth="4"
    android:targetCellHeight="4"
    android:updatePeriodMillis="0"
    android:resizeMode="horizontal|vertical"
    android:widgetCategory="home_screen" />
```

`AndroidManifest.xml` receiver:
```xml
<receiver android:name=".ui.widget.CalendarWidgetReceiver" android:exported="true">
    <intent-filter>
        <action android:name="android.appwidget.action.APPWIDGET_UPDATE"/>
    </intent-filter>
    <meta-data
        android:name="android.appwidget.provider"
        android:resource="@xml/widget_info"/>
</receiver>
```

---

## Dependencies to Add

```toml
# libs.versions.toml
glance = "1.1.0"
glance-appwidget = { module = "androidx.glance:glance-appwidget", version.ref = "glance" }
glance-material3 = { module = "androidx.glance:glance-material3", version.ref = "glance" }
```

```kotlin
// app/build.gradle.kts
implementation(libs.glance.appwidget)
implementation(libs.glance.material3)
```

---

## Out of Scope

- Widget configuration screen (no settings activity)
- Multiple widget sizes (only 4×4)
- Light-mode-specific rose styling (gradient handles both themes)
