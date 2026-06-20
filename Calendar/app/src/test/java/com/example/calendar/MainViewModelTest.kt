package com.example.calendar

import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test
import java.time.DayOfWeek
import java.time.LocalDate

class MainViewModelTest {

    @Test fun `with DayOfWeek MONDAY gives correct week start from Friday`() = runTest {
        // A Friday should map back to its Monday
        val friday = LocalDate.of(2026, 6, 19)       // known Friday
        val expected = LocalDate.of(2026, 6, 15)      // known Monday of that week
        val actual = friday.with(DayOfWeek.MONDAY)
        assertEquals(expected, actual)
    }

    @Test fun `previousWeek subtracts 7 days`() = runTest {
        val start = LocalDate.of(2026, 6, 15) // Monday
        val prev = start.minusWeeks(1)
        assertEquals(LocalDate.of(2026, 6, 8), prev)
    }
}
