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
