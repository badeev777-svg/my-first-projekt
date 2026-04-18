from flask import Flask, render_template, redirect, url_for, session, request

app = Flask(__name__)
app.secret_key = "replace-this-with-a-secret-key"

products = [
    {
        "id": "1",
        "name": "Умная колонка",
        "price": 4990,
        "description": "Громкий звук, голосовое управление и стильный корпус.",
    },
    {
        "id": "2",
        "name": "Наушники",
        "price": 3290,
        "description": "Комфортная посадка, шумоподавление и долгий заряд.",
    },
    {
        "id": "3",
        "name": "Фитнес-браслет",
        "price": 2590,
        "description": "Учет шагов, пульса и уведомления со смартфона.",
    },
    {
        "id": "4",
        "name": "Внешний аккумулятор",
        "price": 1890,
        "description": "Быстрая зарядка и удобный размер для сумки.",
    },
]


def get_cart():
    return session.setdefault("cart", {})


def cart_items():
    cart = get_cart()
    items = []
    total = 0
    for product in products:
        quantity = cart.get(product["id"], 0)
        if quantity:
            subtotal = product["price"] * quantity
            total += subtotal
            items.append({**product, "quantity": quantity, "subtotal": subtotal})
    return items, total


@app.route("/")
def index():
    cart = get_cart()
    cart_count = sum(cart.values())
    return render_template("index.html", products=products, cart_count=cart_count)


@app.route("/add-to-cart/<product_id>")
def add_to_cart(product_id):
    cart = get_cart()
    cart[product_id] = cart.get(product_id, 0) + 1
    session["cart"] = cart
    return redirect(url_for("cart"))


@app.route("/remove-from-cart/<product_id>")
def remove_from_cart(product_id):
    cart = get_cart()
    if product_id in cart:
        cart.pop(product_id)
        session["cart"] = cart
    return redirect(url_for("cart"))


@app.route("/cart")
def cart():
    items, total = cart_items()
    cart_count = sum(get_cart().values())
    return render_template("cart.html", items=items, total=total, cart_count=cart_count)


@app.route("/clear-cart")
def clear_cart():
    session["cart"] = {}
    return redirect(url_for("cart"))


if __name__ == "__main__":
    app.run(debug=True)
