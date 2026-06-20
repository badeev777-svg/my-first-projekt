package com.example.calendar

import android.Manifest
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.example.calendar.notifications.MorningDigestWorker
import com.example.calendar.notifications.NotificationHelper
import com.example.calendar.ui.add.AddTaskScreen
import com.example.calendar.ui.main.MainScreen
import com.example.calendar.ui.theme.CalendarTheme
import java.time.LocalDate

class MainActivity : ComponentActivity() {

    private val requestNotificationPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { /* permission result handled silently */ }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        NotificationHelper.createChannels(this)
        MorningDigestWorker.schedule(this)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            requestNotificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }

        setContent {
            CalendarTheme {
                CalendarApp()
            }
        }
    }
}

@Composable
private fun CalendarApp() {
    val navController = rememberNavController()

    NavHost(navController = navController, startDestination = "main") {
        composable("main") {
            MainScreen(
                onAddTask = { date ->
                    navController.navigate("add/${date}")
                }
            )
        }
        composable(
            route = "add/{date}",
            arguments = listOf(navArgument("date") { type = NavType.StringType })
        ) { backStackEntry ->
            val dateArg = backStackEntry.arguments?.getString("date")
                ?: LocalDate.now().toString()
            AddTaskScreen(
                dateArg = dateArg,
                onBack = { navController.popBackStack() }
            )
        }
    }
}
