from flask import Flask, render_template, request, redirect, session, url_for
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
template_path = os.path.join(BASE_DIR, '..', 'frontend')

app = Flask(__name__, template_folder=template_path)
app.secret_key = 'secret123'

products = [
    {"name": "Luxury Watch", "price": 2499, "icon": "⌚"},
    {"name": "Stylish Shades", "price": 999, "icon": "🕶️"},
    {"name": "Office Bag", "price": 1850, "icon": "💼"}
]

@app.route('/')
def home():
    if 'cart' not in session:
        session['cart'] = {}

    view = request.args.get('view', 'home')   # 🔥 control page
    search_query = request.args.get('search', '').lower()

    # Search filter
    if search_query:
        filtered_products = [p for p in products if search_query in p['name'].lower()]
    else:
        filtered_products = products

    cart = session['cart']
    total = sum(item['price'] * item['qty'] for item in cart.values())

    return render_template(
        'index.html',
        products=filtered_products,
        cart=cart,
        total=total,
        view=view
    )


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    name = request.form.get('name')
    price = int(request.form.get('price'))

    cart = session.get('cart', {})

    if name in cart:
        cart[name]['qty'] += 1
    else:
        cart[name] = {"price": price, "qty": 1}

    session['cart'] = cart
    session.modified = True

    return redirect(url_for('home'))


@app.route('/remove_item', methods=['POST'])
def remove_item():
    name = request.form.get('name')
    cart = session.get('cart', {})

    if name in cart:
        del cart[name]

    session['cart'] = cart
    session.modified = True

    return redirect(url_for('home', view='cart'))


@app.route('/place_order', methods=['POST'])
def place_order():
    session['cart'] = {}
    session.modified = True

    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)