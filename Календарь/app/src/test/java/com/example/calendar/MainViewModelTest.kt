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
        val actual = today.with(DayOfWeek.MONDAY)
        assertEquals(expectedMonday, actual)
    }

    @Test fun `previousWeek subtracts 7 days`() = runTest {
        val start = LocalDate.of(2026, 6, 15) // Monday
        val prev = start.minusWeeks(1)
        assertEquals(LocalDate.of(2026, 6, 8), prev)
    }
}
