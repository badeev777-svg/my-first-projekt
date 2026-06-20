package com.example.calendar

import android.Manifest
import android.content.Intent
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
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

    companion object {
        const val EXTRA_DATE = "extra_date"
        const val EXTRA_ADD  = "extra_add"
    }

    private val requestNotificationPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { /* permission result handled silently */ }

    private var navController: NavHostController? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        NotificationHelper.createChannels(this)
        MorningDigestWorker.schedule(this)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            requestNotificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }

        setContent {
            CalendarTheme {
                CalendarApp(
                    startDate = intent.getStringExtra(EXTRA_DATE),
                    startAdd  = intent.getBooleanExtra(EXTRA_ADD, false),
                    onNavReady = { navController = it }
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        val date = intent.getStringExtra(EXTRA_DATE) ?: return
        val add  = intent.getBooleanExtra(EXTRA_ADD, false)
        val nav  = navController ?: return
        if (add) {
            nav.navigate("add/$date") { launchSingleTop = true }
        } else {
            nav.navigate("main") { popUpTo("main") { inclusive = true } }
        }
    }
}

@Composable
private fun CalendarApp(
    startDate: String?,
    startAdd: Boolean,
    onNavReady: (NavHostController) -> Unit
) {
    val navController = rememberNavController()
    onNavReady(navController)

    val initialRoute = when {
        startAdd && startDate != null -> "add/$startDate"
        else -> "main"
    }

    NavHost(navController = navController, startDestination = initialRoute) {
        composable("main") {
            MainScreen(
                onAddTask = { date -> navController.navigate("add/$date") }
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
                onBack  = { navController.popBackStack() }
            )
        }
    }
}
