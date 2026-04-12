from flask import Flask, render_template, request, redirect, url_for, session, abort
import sqlite3
import os
import secrets
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Постоянный секретный ключ: генерируется один раз и сохраняется в файл
_SECRET_KEY_FILE = 'secret_key.txt'
if os.path.exists(_SECRET_KEY_FILE):
    with open(_SECRET_KEY_FILE) as f:
        app.secret_key = f.read().strip()
else:
    _key = secrets.token_hex(32)
    with open(_SECRET_KEY_FILE, 'w') as f:
        f.write(_key)
    app.secret_key = _key

DATABASE = 'store.db'
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with get_db() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )''')
        # Если таблица users уже существует без колонки role, добавляем её
        columns = [row[1] for row in db.execute("PRAGMA table_info(users)")]
        if 'role' not in columns:
            db.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
        db.execute('''CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            user_id TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            total REAL NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (username),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )''')

        # Добавляем начальные товары, если таблица пустая
        if not db.execute('SELECT COUNT(*) FROM products').fetchone()[0]:
            products = [
                (1, 'Футболка', 1200, 'Удобная хлопковая футболка.'),
                (2, 'Кофта', 2500, 'Теплая кофта для прохладной погоды.'),
                (3, 'Кеды', 4500, 'Стильные кеды для повседневной носки.'),
                (4, 'Рюкзак', 3200, 'Прочный рюкзак для города и путешествий.')
            ]
            db.executemany('INSERT INTO products (id, name, price, description) VALUES (?, ?, ?, ?)', products)

        if not db.execute('SELECT COUNT(*) FROM users WHERE username = ?', (ADMIN_USERNAME,)).fetchone()[0]:
            db.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                       (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD), 'admin'))

        # Миграция: хэшируем пароли, которые ещё хранятся в открытом виде
        for u in db.execute("SELECT username, password FROM users").fetchall():
            pw = u['password']
            if not (pw.startswith('pbkdf2:') or pw.startswith('scrypt:') or pw.startswith('argon2')):
                db.execute("UPDATE users SET password = ? WHERE username = ?",
                           (generate_password_hash(pw), u['username']))


def get_products():
    with get_db() as db:
        return db.execute('SELECT * FROM products ORDER BY id').fetchall()

def get_product(product_id):
    with get_db() as db:
        return db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()

def get_user(username):
    with get_db() as db:
        return db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

def get_all_users(search=None):
    with get_db() as db:
        if search:
            query = f"%{search}%"
            return db.execute('SELECT username, role FROM users WHERE username LIKE ? ORDER BY username', (query,)).fetchall()
        return db.execute('SELECT username, role FROM users ORDER BY username').fetchall()

def create_user(username, password, role='user'):
    with get_db() as db:
        db.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                   (username, generate_password_hash(password), role))


def update_user_password(username, password):
    with get_db() as db:
        db.execute('UPDATE users SET password = ? WHERE username = ?',
                   (generate_password_hash(password), username))


def update_user_role(username, role):
    with get_db() as db:
        db.execute('UPDATE users SET role = ? WHERE username = ?', (role, username))


def delete_user(username):
    with get_db() as db:
        db.execute('DELETE FROM users WHERE username = ?', (username,))


def count_admins():
    with get_db() as db:
        return db.execute('SELECT COUNT(*) FROM users WHERE role = ?', ('admin',)).fetchone()[0]


def get_user_orders(username):
    with get_db() as db:
        return db.execute('''
            SELECT o.*, p.name, p.price
            FROM orders o
            JOIN products p ON o.product_id = p.id
            WHERE o.user_id = ?
            ORDER BY o.created_at DESC
        ''', (username,)).fetchall()


def create_order(user_id, product_id, quantity, total):
    with get_db() as db:
        db.execute('INSERT INTO orders (user_id, product_id, quantity, total, created_at) VALUES (?, ?, ?, ?, ?)',
                   (user_id, product_id, quantity, total, datetime.now().isoformat()))

def update_product(product_id, name, price, description):
    with get_db() as db:
        db.execute('UPDATE products SET name = ?, price = ?, description = ? WHERE id = ?',
                   (name, price, description, product_id))

def delete_product(product_id):
    with get_db() as db:
        db.execute('DELETE FROM products WHERE id = ?', (product_id,))

def add_product(name, price, description):
    with get_db() as db:
        cursor = db.execute('INSERT INTO products (name, price, description) VALUES (?, ?, ?)',
                           (name, price, description))
        return cursor.lastrowid

# Инициализируем базу данных при запуске
init_db()


# ── CSRF ────────────────────────────────────────────────────────────────────

def get_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']

app.jinja_env.globals['csrf_token'] = get_csrf_token

@app.before_request
def csrf_protect():
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        token = session.get('csrf_token')
        form_token = request.form.get('csrf_token')
        if not token or not form_token or token != form_token:
            abort(403)


# ── Корзина ──────────────────────────────────────────────────────────────────

def get_cart():
    return session.setdefault("cart", {})


def save_cart(cart):
    session["cart"] = cart


def cart_totals(cart):
    items = []
    total = 0
    for product_id, qty in cart.items():
        product = get_product(int(product_id))
        if product:
            subtotal = product['price'] * qty
            total += subtotal
            items.append({"product": dict(product), "quantity": qty, "subtotal": subtotal})
    return items, total


@app.route("/")
def index():
    return render_template("index.html", products=get_products())


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = get_product(product_id)
    if not product:
        return redirect(url_for("index"))
    return render_template("product.html", product=dict(product))


@app.route("/cart")
def cart():
    cart = get_cart()
    items, total = cart_totals(cart)
    return render_template("cart.html", items=items, total=total)


@app.route("/cart/add", methods=["POST"])
def add_to_cart():
    product_id = request.form.get("product_id")
    quantity = int(request.form.get("quantity", 1))
    cart = get_cart()
    cart[product_id] = cart.get(product_id, 0) + quantity
    save_cart(cart)
    return redirect(url_for("cart"))


@app.route("/cart/remove/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):
    cart = get_cart()
    cart.pop(str(product_id), None)
    save_cart(cart)
    return redirect(url_for("cart"))


def current_user():
    return session.get("user")


def login_user(username, role):
    session["user"] = username
    session["role"] = role


def logout_user():
    session.pop("user", None)
    session.pop("role", None)


def is_admin():
    return session.get("role") == 'admin'


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            error = "Введите имя пользователя и пароль."
        else:
            user = get_user(username)
            if not user or not check_password_hash(user['password'], password):
                error = "Неверный логин или пароль."
            else:
                login_user(username, user['role'])
                return redirect(url_for("index"))
    return render_template("login.html", error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if not username or not password or not confirm:
            error = "Заполните все поля."
        elif get_user(username):
            error = "Пользователь с таким именем уже существует."
        elif password != confirm:
            error = "Пароли не совпадают."
        else:
            create_user(username, password, 'user')
            login_user(username, 'user')
            return redirect(url_for("index"))
    return render_template("register.html", error=error)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/admin")
def admin():
    if not is_admin():
        return redirect(url_for("index"))
    products = get_products()
    return render_template("admin.html", products=products)


@app.route("/admin/add", methods=["GET", "POST"])
def admin_add():
    if not is_admin():
        return redirect(url_for("index"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price = float(request.form.get("price", 0))
        description = request.form.get("description", "").strip()
        if name and price > 0:
            add_product(name, price, description)
            return redirect(url_for("admin"))
    return render_template("admin_add.html")


@app.route("/admin/edit/<int:product_id>", methods=["GET", "POST"])
def admin_edit(product_id):
    if not is_admin():
        return redirect(url_for("index"))
    product = get_product(product_id)
    if not product:
        return redirect(url_for("admin"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price = float(request.form.get("price", 0))
        description = request.form.get("description", "").strip()
        if name and price > 0:
            update_product(product_id, name, price, description)
            return redirect(url_for("admin"))
    return render_template("admin_edit.html", product=dict(product))


@app.route("/admin/delete/<int:product_id>", methods=["POST"])
def admin_delete(product_id):
    if not is_admin():
        return redirect(url_for("index"))
    delete_product(product_id)
    return redirect(url_for("admin"))


@app.route("/admin/users")
def admin_users():
    if not is_admin():
        return redirect(url_for("index"))
    search = request.args.get('search', '').strip()
    users = get_all_users(search) if search else get_all_users()
    return render_template("admin_users.html", users=users, current_user=current_user(), search=search)


@app.route("/admin/users/add", methods=["GET", "POST"])
def admin_user_add():
    if not is_admin():
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        role = request.form.get('role', 'user')
        if not username or not password or not confirm:
            error = 'Заполните все поля.'
        elif password != confirm:
            error = 'Пароли не совпадают.'
        elif get_user(username):
            error = 'Пользователь с таким именем уже существует.'
        elif role not in ('user', 'admin'):
            error = 'Неверная роль.'
        else:
            create_user(username, password, role)
            return redirect(url_for('admin_users'))
    return render_template('admin_user_add.html', error=error)


@app.route("/admin/users/<username>/role", methods=["POST"])
def admin_user_role(username):
    if not is_admin():
        return redirect(url_for("index"))
    if username == current_user():
        return redirect(url_for("admin_users"))
    role = request.form.get("role")
    if role in ('user', 'admin'):
        update_user_role(username, role)
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<username>/delete", methods=["POST"])
def admin_user_delete(username):
    if not is_admin():
        return redirect(url_for("index"))
    if username == current_user():
        return redirect(url_for("admin_users"))
    if get_user(username) and count_admins() > 1:
        delete_user(username)
    return redirect(url_for("admin_users"))


@app.route("/profile", methods=["GET", "POST"])
def profile():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    orders = get_user_orders(user)
    error = None
    success = None

    if request.method == "POST":
        old_password = request.form.get("old_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        current = get_user(user)

        if not old_password or not new_password or not confirm_password:
            error = "Заполните все поля."
        elif not check_password_hash(current['password'], old_password):
            error = "Старый пароль неверен."
        elif new_password != confirm_password:
            error = "Пароли не совпадают."
        else:
            update_user_password(user, new_password)
            success = "Пароль успешно изменён."

    return render_template("profile.html", username=user, orders=orders, error=error, success=success)


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    cart = get_cart()
    items, total = cart_totals(cart)
    if request.method == "POST":
        for item in items:
            create_order(user, item['product']['id'], item['quantity'], item['subtotal'])
        session.pop("cart", None)
        return render_template("checkout.html", total=total, success=True)
    return render_template("checkout.html", items=items, total=total, success=False)


if __name__ == "__main__":
    app.run(debug=True)
