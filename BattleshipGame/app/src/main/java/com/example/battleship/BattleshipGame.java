package com.example.battleship;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public class BattleshipGame {

    public enum ShotResult { HIT, MISS, ALREADY_SHOT }

    public static final int GRID_SIZE = 10;

    // Cell states
    public static final int WATER = 0;
    public static final int SHIP = 1;
    public static final int HIT = 2;
    public static final int MISS = 3;

    private int[][] playerBoard = new int[GRID_SIZE][GRID_SIZE];
    private int[][] enemyBoard = new int[GRID_SIZE][GRID_SIZE];
    private int[][] enemyVisible = new int[GRID_SIZE][GRID_SIZE];

    private boolean playerTurn = true;
    private boolean gameOver = false;

    private int playerShipsRemaining;
    private int enemyShipsRemaining;

    private final Random random = new Random();

    // Smart AI: list of adjacent cells to try after a hit
    private final List<int[]> huntTargets = new ArrayList<>();

    public void initialize() {
        playerBoard = new int[GRID_SIZE][GRID_SIZE];
        enemyBoard = new int[GRID_SIZE][GRID_SIZE];
        enemyVisible = new int[GRID_SIZE][GRID_SIZE];
        playerTurn = true;
        gameOver = false;
        huntTargets.clear();

        // Classic Russian battleship ships: 1x4, 2x3, 3x2, 4x1
        int[] ships = {4, 3, 3, 2, 2, 2, 1, 1, 1, 1};

        placeShipsRandomly(playerBoard, ships);
        placeShipsRandomly(enemyBoard, ships);

        playerShipsRemaining = countShipCells(playerBoard);
        enemyShipsRemaining = countShipCells(enemyBoard);
    }

    private int countShipCells(int[][] board) {
        int count = 0;
        for (int[] row : board)
            for (int cell : row)
                if (cell == SHIP) count++;
        return count;
    }

    private void placeShipsRandomly(int[][] board, int[] ships) {
        for (int size : ships) {
            boolean placed = false;
            int attempts = 0;
            while (!placed && attempts < 1000) {
                attempts++;
                boolean horizontal = random.nextBoolean();
                int row = random.nextInt(GRID_SIZE);
                int col = random.nextInt(GRID_SIZE);

                if (canPlace(board, row, col, size, horizontal)) {
                    placeShip(board, row, col, size, horizontal);
                    placed = true;
                }
            }
        }
    }

    private boolean canPlace(int[][] board, int row, int col, int size, boolean horizontal) {
        for (int i = 0; i < size; i++) {
            int r = horizontal ? row : row + i;
            int c = horizontal ? col + i : col;

            if (r >= GRID_SIZE || c >= GRID_SIZE) return false;

            // Check cell and all surrounding cells (no touching ships)
            for (int dr = -1; dr <= 1; dr++) {
                for (int dc = -1; dc <= 1; dc++) {
                    int nr = r + dr, nc = c + dc;
                    if (nr >= 0 && nr < GRID_SIZE && nc >= 0 && nc < GRID_SIZE) {
                        if (board[nr][nc] == SHIP) return false;
                    }
                }
            }
        }
        return true;
    }

    private void placeShip(int[][] board, int row, int col, int size, boolean horizontal) {
        for (int i = 0; i < size; i++) {
            int r = horizontal ? row : row + i;
            int c = horizontal ? col + i : col;
            board[r][c] = SHIP;
        }
    }

    public ShotResult playerShoot(int row, int col) {
        if (enemyVisible[row][col] == HIT || enemyVisible[row][col] == MISS) {
            return ShotResult.ALREADY_SHOT;
        }

        if (enemyBoard[row][col] == SHIP) {
            enemyBoard[row][col] = HIT;
            enemyVisible[row][col] = HIT;
            enemyShipsRemaining--;
            if (enemyShipsRemaining <= 0) gameOver = true;
            return ShotResult.HIT;
        } else {
            enemyVisible[row][col] = MISS;
            playerTurn = false;
            return ShotResult.MISS;
        }
    }

    public ShotResult computerShoot() {
        int row, col;

        // Smart AI: if we have hunt targets (adjacent to a hit), try them first
        while (!huntTargets.isEmpty()) {
            int[] target = huntTargets.remove(0);
            row = target[0];
            col = target[1];
            if (row < 0 || row >= GRID_SIZE || col < 0 || col >= GRID_SIZE) continue;
            if (playerBoard[row][col] == HIT || playerBoard[row][col] == MISS) continue;

            if (playerBoard[row][col] == SHIP) {
                playerBoard[row][col] = HIT;
                playerShipsRemaining--;
                if (playerShipsRemaining <= 0) gameOver = true;
                // Add adjacent cells for further hunting
                addHuntTargets(row, col);
                return ShotResult.HIT;
            } else {
                playerBoard[row][col] = MISS;
                playerTurn = true;
                return ShotResult.MISS;
            }
        }

        // Random shot
        do {
            row = random.nextInt(GRID_SIZE);
            col = random.nextInt(GRID_SIZE);
        } while (playerBoard[row][col] == HIT || playerBoard[row][col] == MISS);

        if (playerBoard[row][col] == SHIP) {
            playerBoard[row][col] = HIT;
            playerShipsRemaining--;
            if (playerShipsRemaining <= 0) gameOver = true;
            addHuntTargets(row, col);
            return ShotResult.HIT;
        } else {
            playerBoard[row][col] = MISS;
            playerTurn = true;
            return ShotResult.MISS;
        }
    }

    private void addHuntTargets(int row, int col) {
        huntTargets.add(new int[]{row - 1, col});
        huntTargets.add(new int[]{row + 1, col});
        huntTargets.add(new int[]{row, col - 1});
        huntTargets.add(new int[]{row, col + 1});
    }

    public int[][] getPlayerBoard() { return playerBoard; }
    public int[][] getEnemyBoard() { return enemyVisible; }
    public boolean isPlayerTurn() { return playerTurn; }
    public boolean isGameOver() { return gameOver; }
}
