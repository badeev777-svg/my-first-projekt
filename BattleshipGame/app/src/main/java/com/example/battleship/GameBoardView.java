package com.example.battleship;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.util.AttributeSet;
import android.view.MotionEvent;
import android.view.View;

public class GameBoardView extends View {

    private int[][] board;
    private boolean showShips;
    private OnCellClickListener listener;

    private final Paint waterPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint shipPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint hitPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint missPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint gridPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint symbolPaint = new Paint(Paint.ANTI_ALIAS_FLAG);

    // Computed in onDraw, used in onTouchEvent
    private float cellSize;
    private float offsetX;
    private float offsetY;

    public interface OnCellClickListener {
        void onCellClick(int row, int col);
    }

    public GameBoardView(Context context) {
        super(context);
        init();
    }

    public GameBoardView(Context context, AttributeSet attrs) {
        super(context, attrs);
        init();
    }

    public GameBoardView(Context context, AttributeSet attrs, int defStyleAttr) {
        super(context, attrs, defStyleAttr);
        init();
    }

    private void init() {
        waterPaint.setColor(Color.parseColor("#1E88E5"));
        waterPaint.setStyle(Paint.Style.FILL);

        shipPaint.setColor(Color.parseColor("#546E7A"));
        shipPaint.setStyle(Paint.Style.FILL);

        hitPaint.setColor(Color.parseColor("#E53935"));
        hitPaint.setStyle(Paint.Style.FILL);

        missPaint.setColor(Color.parseColor("#90CAF9"));
        missPaint.setStyle(Paint.Style.FILL);

        gridPaint.setColor(Color.parseColor("#FFFFFF"));
        gridPaint.setStyle(Paint.Style.STROKE);
        gridPaint.setStrokeWidth(1.5f);

        symbolPaint.setColor(Color.WHITE);
        symbolPaint.setTextAlign(Paint.Align.CENTER);
        symbolPaint.setFakeBoldText(true);
    }

    public void setBoard(int[][] board, boolean showShips) {
        this.board = board;
        this.showShips = showShips;
        invalidate();
    }

    public void setOnCellClickListener(OnCellClickListener listener) {
        this.listener = listener;
    }

    @Override
    protected void onDraw(Canvas canvas) {
        if (board == null) return;

        int n = BattleshipGame.GRID_SIZE;
        cellSize = Math.min(getWidth(), getHeight()) / (float) n;
        offsetX = (getWidth() - cellSize * n) / 2f;
        offsetY = (getHeight() - cellSize * n) / 2f;

        symbolPaint.setTextSize(cellSize * 0.55f);

        for (int row = 0; row < n; row++) {
            for (int col = 0; col < n; col++) {
                float left = offsetX + col * cellSize;
                float top = offsetY + row * cellSize;
                float right = left + cellSize;
                float bottom = top + cellSize;

                int cell = board[row][col];
                Paint fill;

                if (cell == BattleshipGame.HIT) {
                    fill = hitPaint;
                } else if (cell == BattleshipGame.MISS) {
                    fill = missPaint;
                } else if (cell == BattleshipGame.SHIP && showShips) {
                    fill = shipPaint;
                } else {
                    fill = waterPaint;
                }

                canvas.drawRect(left + 1, top + 1, right - 1, bottom - 1, fill);
                canvas.drawRect(left, top, right, bottom, gridPaint);

                float cx = left + cellSize / 2f;
                float cy = top + cellSize / 2f - (symbolPaint.ascent() + symbolPaint.descent()) / 2f;

                if (cell == BattleshipGame.HIT) {
                    canvas.drawText("X", cx, cy, symbolPaint);
                } else if (cell == BattleshipGame.MISS) {
                    symbolPaint.setColor(Color.parseColor("#1565C0"));
                    canvas.drawText(".", cx, cy, symbolPaint);
                    symbolPaint.setColor(Color.WHITE);
                }
            }
        }
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        if (event.getAction() == MotionEvent.ACTION_UP && listener != null) {
            int col = (int) ((event.getX() - offsetX) / cellSize);
            int row = (int) ((event.getY() - offsetY) / cellSize);
            int n = BattleshipGame.GRID_SIZE;
            if (row >= 0 && row < n && col >= 0 && col < n) {
                listener.onCellClick(row, col);
            }
        }
        return true;
    }
}
