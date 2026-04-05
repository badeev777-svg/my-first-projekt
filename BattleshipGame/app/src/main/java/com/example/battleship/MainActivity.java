package com.example.battleship;

import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.Button;
import android.widget.TextView;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;

public class MainActivity extends AppCompatActivity {

    private BattleshipGame game;
    private GameBoardView playerBoardView;
    private GameBoardView enemyBoardView;
    private TextView statusText;
    private final Handler handler = new Handler(Looper.getMainLooper());

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        playerBoardView = findViewById(R.id.playerBoard);
        enemyBoardView = findViewById(R.id.enemyBoard);
        statusText = findViewById(R.id.statusText);
        Button newGameButton = findViewById(R.id.newGameButton);

        newGameButton.setOnClickListener(v -> startNewGame());

        // Set click listener once — always uses current `game` field
        enemyBoardView.setOnCellClickListener((row, col) -> {
            if (game == null || !game.isPlayerTurn() || game.isGameOver()) return;

            BattleshipGame.ShotResult result = game.playerShoot(row, col);
            if (result == BattleshipGame.ShotResult.ALREADY_SHOT) return;

            enemyBoardView.invalidate();

            if (game.isGameOver()) {
                statusText.setText("Вы победили!");
                showGameOver("Вы победили! Все корабли противника потоплены!");
                return;
            }

            if (result == BattleshipGame.ShotResult.MISS) {
                statusText.setText("Мимо! Ход компьютера...");
                handler.postDelayed(this::computerTurn, 800);
            } else {
                statusText.setText("Попадание! Стреляйте ещё!");
            }
        });

        startNewGame();
    }

    private void startNewGame() {
        handler.removeCallbacksAndMessages(null);
        game = new BattleshipGame();
        game.initialize();

        playerBoardView.setBoard(game.getPlayerBoard(), true);
        enemyBoardView.setBoard(game.getEnemyBoard(), false);

        statusText.setText("Ваш ход! Нажмите на поле противника");
    }

    private void computerTurn() {
        if (game == null || game.isGameOver()) return;

        BattleshipGame.ShotResult result = game.computerShoot();
        playerBoardView.invalidate();

        if (game.isGameOver()) {
            statusText.setText("Компьютер победил!");
            showGameOver("Компьютер победил! Ваши корабли потоплены.");
            return;
        }

        if (result == BattleshipGame.ShotResult.MISS) {
            statusText.setText("Компьютер промахнулся. Ваш ход!");
        } else {
            statusText.setText("Компьютер попал! Стреляет снова...");
            handler.postDelayed(this::computerTurn, 800);
        }
    }

    private void showGameOver(String message) {
        new AlertDialog.Builder(this)
                .setTitle("Игра окончена")
                .setMessage(message)
                .setPositiveButton("Новая игра", (d, w) -> startNewGame())
                .setNegativeButton("Закрыть", null)
                .setCancelable(false)
                .show();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        handler.removeCallbacksAndMessages(null);
    }
}
