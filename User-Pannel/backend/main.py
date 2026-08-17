from datetime import datetime, timezone
from functools import wraps
import os
import re

import bcrypt
from bson import ObjectId
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from pymongo import MongoClient
from pymongo.errors import PyMongoError


load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, '..', 'frontend')
ADMIN_DIR = os.path.join(BASE_DIR, '..', '..', 'Admin', 'frontend')
LOGIN_DIR = os.path.join(BASE_DIR, '..', '..', 'Login')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR,
    static_url_path='/static',
)
app.secret_key = os.getenv('SECRET_KEY', 'styleaccess-local-development-key')
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://127.0.0.1:27017')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'styleaccess_dev')
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=4000)
db = client[MONGO_DB_NAME]
users_col = db['users']
products_col = db['products']
orders_col = db['orders']


DEFAULT_PRODUCTS = [
    {
        '_id': 'signature-01',
        'name': 'The Regent Blazer',
        'price': 8490,
        'compareAt': 9990,
        'category': 'Tailoring',
        'description': 'A softly structured blazer in a breathable wool blend, finished with horn-style buttons.',
        'imageUrl': '/static/images/regent-blazer.jpg',
        'badge': 'Bestseller',
        'sizes': ['S', 'M', 'L', 'XL'],
        'stock': 18,
        'rating': 4.9,
    },
    {
        '_id': 'signature-02',
        'name': 'Portofino Linen Shirt',
        'price': 3490,
        'compareAt': 0,
        'category': 'Shirts',
        'description': 'Lightweight premium linen with a relaxed collar and a clean, considered drape.',
        'imageUrl': '/static/images/portofino-shirt.jpg',
        'badge': 'New',
        'sizes': ['S', 'M', 'L', 'XL', 'XXL'],
        'stock': 24,
        'rating': 4.8,
    },
    {
        '_id': 'signature-03',
        'name': 'Mayfair Pleated Trouser',
        'price': 4290,
        'compareAt': 4990,
        'category': 'Tailoring',
        'description': 'A refined straight-leg trouser with a single pleat and an adjustable side waist.',
        'imageUrl': '/static/images/mayfair-trouser.jpg',
        'badge': 'Limited',
        'sizes': ['30', '32', '34', '36', '38'],
        'stock': 9,
        'rating': 4.7,
    },
    {
        '_id': 'signature-04',
        'name': 'Belgravia Overcoat',
        'price': 12990,
        'compareAt': 14990,
        'category': 'Outerwear',
        'description': 'A timeless double-breasted overcoat cut from a warm brushed wool blend.',
        'imageUrl': '/static/images/belgravia-coat.jpg',
        'badge': 'Editor\'s pick',
        'sizes': ['S', 'M', 'L', 'XL'],
        'stock': 12,
        'rating': 4.9,
    },
    {
        '_id': 'signature-05',
        'name': 'Chelsea Knit Polo',
        'price': 3890,
        'compareAt': 0,
        'category': 'Knitwear',
        'description': 'Fine-gauge cotton knit with a neat open collar—polished enough for every plan.',
        'imageUrl': '/static/images/chelsea-knit.jpg',
        'badge': '',
        'sizes': ['S', 'M', 'L', 'XL'],
        'stock': 20,
        'rating': 4.6,
    },
    {
        '_id': 'signature-06',
        'name': 'Oxford Club Shirt',
        'price': 2990,
        'compareAt': 0,
        'category': 'Shirts',
        'description': 'A dependable cotton Oxford with a crisp collar and an easy all-day finish.',
        'imageUrl': '/static/images/oxford-shirt.jpg',
        'badge': '',
        'sizes': ['S', 'M', 'L', 'XL', 'XXL'],
        'stock': 32,
        'rating': 4.8,
    },
    {
        '_id': 'signature-07',
        'name': 'Weekender Suede Jacket',
        'price': 9990,
        'compareAt': 11990,
        'category': 'Outerwear',
        'description': 'Supple faux suede, tonal hardware and a clean silhouette built for cool evenings.',
        'imageUrl': '/static/images/weekender-jacket.jpg',
        'badge': 'Online exclusive',
        'sizes': ['S', 'M', 'L', 'XL'],
        'stock': 7,
        'rating': 4.7,
    },
    {
        '_id': 'signature-08',
        'name': 'Sunday Merino Crew',
        'price': 4590,
        'compareAt': 0,
        'category': 'Knitwear',
        'description': 'An exceptionally soft merino crewneck designed as an effortless year-round layer.',
        'imageUrl': '/static/images/merino-crew.jpg',
        'badge': 'Core collection',
        'sizes': ['S', 'M', 'L', 'XL'],
        'stock': 16,
        'rating': 4.9,
    },
]


def serialize_document(value):
    if isinstance(value, list):
        return [serialize_document(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize_document(item) for key, item in value.items()}
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def normalize_product(product):
    item = serialize_document(dict(product))
    raw_sizes = item.get('sizes', ['S', 'M', 'L', 'XL'])
    if isinstance(raw_sizes, str):
        raw_sizes = [size.strip() for size in raw_sizes.split(',') if size.strip()]
    item.update({
        '_id': str(item.get('_id', item.get('name', 'product'))),
        'price': float(item.get('price', 0)),
        'compareAt': float(item.get('compareAt') or 0),
        'category': item.get('category') or 'Essentials',
        'description': item.get('description') or 'A refined StyleAccess essential, made for repeat wear.',
        'imageUrl': item.get('imageUrl') or DEFAULT_PRODUCTS[0]['imageUrl'],
        'badge': item.get('badge') or '',
        'sizes': raw_sizes or ['One size'],
        'stock': int(item.get('stock', 10) or 0),
        'rating': float(item.get('rating', 4.8) or 4.8),
    })
    return item


def get_products_from_db():
    try:
        products = list(products_col.find())
    except PyMongoError:
        products = []
    return [normalize_product(product) for product in products] if products else DEFAULT_PRODUCTS


def find_product(name):
    normalized_name = (name or '').strip().lower()
    return next((item for item in get_products_from_db() if item['name'].lower() == normalized_name), None)


def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    try:
        user = users_col.find_one({'_id': ObjectId(user_id)})
    except (PyMongoError, ValueError):
        return None
    if not user:
        return None
    return {
        'name': user.get('name', 'Customer'),
        'email': user.get('email', ''),
        'role': user.get('role', 'user'),
    }


def get_cart_summary():
    cart = session.get('cart', {})
    items = []
    for name, cart_item in cart.items():
        product = find_product(name) or {}
        items.append({
            'name': name,
            'price': float(cart_item.get('price', 0)),
            'qty': int(cart_item.get('qty', 1)),
            'imageUrl': product.get('imageUrl', DEFAULT_PRODUCTS[0]['imageUrl']),
            'category': product.get('category', 'StyleAccess'),
        })
    total = sum(item['price'] * item['qty'] for item in items)
    return {'items': items, 'total': total, 'count': sum(item['qty'] for item in items)}


def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            next_path = request.full_path.rstrip('?') if request.query_string else request.path
            return redirect(url_for('login_page', next=next_path))
        return function(*args, **kwargs)
    return wrapper


def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401
        if user.get('role') != 'admin':
            return jsonify({'error': 'Forbidden'}), 403
        return function(*args, **kwargs)
    return wrapper


@app.route('/login')
def login_page():
    return send_from_directory(LOGIN_DIR, 'Login.html')


@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get('name', '')).strip()
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', ''))
    if len(name) < 2 or not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return jsonify({'error': 'Enter a valid name and email address.'}), 400
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters.'}), 400
    try:
        if users_col.find_one({'email': email}):
            return jsonify({'error': 'An account already exists for this email.'}), 400
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        users_col.insert_one({
            'name': name,
            'email': email,
            'password': hashed,
            'role': 'user',
            'created_at': datetime.now(timezone.utc),
        })
    except PyMongoError:
        return jsonify({'error': 'We could not create your account. Please try again.'}), 503
    return jsonify({'message': 'Account created'}), 201


@app.route('/api/login', methods=['POST'])
def login_api():
    data = request.get_json(silent=True) or {}
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', ''))
    try:
        user = users_col.find_one({'email': email})
    except PyMongoError:
        return jsonify({'error': 'Sign in is temporarily unavailable.'}), 503
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password']):
        return jsonify({'error': 'The email or password is incorrect.'}), 401
    session.clear()
    session['user_id'] = str(user['_id'])
    return jsonify({
        'name': user.get('name', ''),
        'email': user.get('email', ''),
        'role': user.get('role', 'user'),
    })


@app.route('/api/logout', methods=['POST'])
def logout_api():
    session.clear()
    return jsonify({'message': 'Logged out'})


@app.route('/api/me')
def me():
    user = get_current_user()
    return jsonify(user) if user else (jsonify({'error': 'Unauthorized'}), 401)


@app.route('/api/products')
def get_products():
    return jsonify(get_products_from_db())


@app.route('/api/cart')
def cart_api():
    return jsonify(get_cart_summary())


@app.route('/api/admin/catalog')
@admin_required
def admin_catalog():
    try:
        products = [normalize_product(item) for item in products_col.find()]
    except PyMongoError:
        return jsonify({'error': 'Could not load inventory.'}), 503
    return jsonify(products)


@app.route('/api/admin/dashboard')
@admin_required
def admin_dashboard_data():
    try:
        products = list(products_col.find())
        orders = list(orders_col.find().sort('created_at', -1).limit(8))
        order_count = orders_col.count_documents({})
    except PyMongoError:
        return jsonify({'error': 'Could not load dashboard data.'}), 503
    return jsonify({
        'productCount': len(products),
        'stockCount': sum(int(product.get('stock', 0) or 0) for product in products),
        'orderCount': order_count,
        'catalogValue': sum(float(product.get('price', 0)) * int(product.get('stock', 0) or 0) for product in products),
        'orders': serialize_document(orders),
    })


@app.route('/api/admin/products', methods=['POST'])
@admin_required
def add_product():
    data = request.get_json(silent=True) or {}
    name = str(data.get('name', '')).strip()
    try:
        price = float(data.get('price', 0))
    except (TypeError, ValueError):
        price = 0
    if not name or price <= 0:
        return jsonify({'error': 'Product name and a valid price are required.'}), 400
    product = {
        'name': name,
        'price': price,
        'compareAt': float(data.get('compareAt') or 0),
        'category': str(data.get('category') or 'Essentials').strip(),
        'description': str(data.get('description') or '').strip(),
        'imageUrl': str(data.get('imageUrl') or '').strip(),
        'badge': str(data.get('badge') or '').strip(),
        'sizes': data.get('sizes') or ['S', 'M', 'L', 'XL'],
        'stock': max(0, int(data.get('stock') or 0)),
        'rating': 4.8,
        'created_at': datetime.now(timezone.utc),
    }
    try:
        result = products_col.insert_one(product)
    except PyMongoError:
        return jsonify({'error': 'Could not save the product.'}), 503
    product['_id'] = str(result.inserted_id)
    return jsonify(normalize_product(product)), 201


@app.route('/api/admin/products/<pid>', methods=['DELETE'])
@admin_required
def delete_product(pid):
    try:
        result = products_col.delete_one({'_id': ObjectId(pid)})
    except (PyMongoError, ValueError):
        return jsonify({'error': 'Could not delete this product.'}), 400
    if not result.deleted_count:
        return jsonify({'error': 'Product not found.'}), 404
    return jsonify({'message': 'Product deleted'})


@app.route('/api/admin/products/<pid>', methods=['PUT'])
@admin_required
def update_product(pid):
    data = request.get_json(silent=True) or {}
    allowed = {'name', 'price', 'compareAt', 'category', 'description', 'imageUrl', 'badge', 'sizes', 'stock'}
    update = {key: data[key] for key in allowed if key in data}
    if 'price' in update:
        update['price'] = float(update['price'])
    if 'compareAt' in update:
        update['compareAt'] = float(update['compareAt'] or 0)
    if 'stock' in update:
        update['stock'] = max(0, int(update['stock'] or 0))
    try:
        result = products_col.update_one({'_id': ObjectId(pid)}, {'$set': update})
    except (PyMongoError, ValueError, TypeError):
        return jsonify({'error': 'Could not update this product.'}), 400
    if not result.matched_count:
        return jsonify({'error': 'Product not found.'}), 404
    return jsonify({'message': 'Product updated'})


@app.route('/admin')
def admin_dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('login_page'))
    if user.get('role') != 'admin':
        return redirect(url_for('home'))
    return send_from_directory(ADMIN_DIR, 'index.html')


@app.route('/')
def home():
    session.setdefault('cart', {})
    view = request.args.get('view', 'home')
    if view == 'account' and 'user_id' not in session:
        return redirect(url_for('login_page', next=request.full_path.rstrip('?')))
    search_query = request.args.get('search', '').strip().lower()
    products = get_products_from_db()
    if search_query:
        products = [
            product for product in products
            if search_query in product['name'].lower()
            or search_query in product['category'].lower()
            or search_query in product['description'].lower()
        ]
    cart_summary = get_cart_summary()
    user = get_current_user()
    orders = []
    if view == 'account':
        try:
            raw_orders = orders_col.find({'user_id': ObjectId(session['user_id'])}).sort('created_at', -1).limit(10)
            orders = serialize_document(list(raw_orders))
        except (PyMongoError, ValueError):
            orders = []
    return render_template(
        'index.html',
        products=products,
        cart=session['cart'],
        cart_summary=cart_summary,
        total=cart_summary['total'],
        view=view,
        user=user,
        orders=orders,
        search_query=request.args.get('search', ''),
    )


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    data = request.get_json(silent=True) if request.is_json else request.form
    name = str((data or {}).get('name', '')).strip()
    product = find_product(name)
    if not product:
        return jsonify({'error': 'This product is no longer available.'}), 404
    cart = session.get('cart', {})
    if name in cart:
        cart[name]['qty'] = min(10, int(cart[name].get('qty', 1)) + 1)
    else:
        cart[name] = {'price': float(product['price']), 'qty': 1}
    session['cart'] = cart
    session.modified = True
    if request.is_json:
        return jsonify(get_cart_summary())
    return redirect(url_for('home'))


@app.route('/update_cart', methods=['POST'])
def update_cart():
    data = request.get_json(silent=True) or request.form
    name = str(data.get('name', '')).strip()
    action = data.get('action', 'set')
    cart = session.get('cart', {})
    if name not in cart:
        return jsonify({'error': 'Item not found in your bag.'}), 404
    current_qty = int(cart[name].get('qty', 1))
    if action == 'increase':
        quantity = current_qty + 1
    elif action == 'decrease':
        quantity = current_qty - 1
    else:
        try:
            quantity = int(data.get('qty', current_qty))
        except (TypeError, ValueError):
            quantity = current_qty
    if quantity <= 0:
        del cart[name]
    else:
        cart[name]['qty'] = min(10, quantity)
    session['cart'] = cart
    session.modified = True
    return jsonify(get_cart_summary())


@app.route('/buy_now', methods=['POST'])
def buy_now():
    data = request.get_json(silent=True) if request.is_json else request.form
    name = str((data or {}).get('name', '')).strip()
    product = find_product(name)
    if not product:
        return jsonify({'error': 'This product is no longer available.'}), 404
    session['checkout'] = {
        'items': [{
            'name': product['name'],
            'price': product['price'],
            'qty': 1,
            'imageUrl': product['imageUrl'],
            'category': product['category'],
        }],
        'total': product['price'],
    }
    session.modified = True
    return jsonify({'message': 'Ready for checkout', 'redirect': url_for('payment_page')})


@app.route('/checkout_cart')
@login_required
def checkout_cart():
    cart_summary = get_cart_summary()
    if not cart_summary['items']:
        return redirect(url_for('home'))
    session['checkout'] = {'items': cart_summary['items'], 'total': cart_summary['total']}
    session.modified = True
    return redirect(url_for('payment_page'))


@app.route('/payment')
@login_required
def payment_page():
    checkout = session.get('checkout')
    if not checkout:
        return redirect(url_for('checkout_cart'))
    return render_template('payment.html', checkout=checkout, user=get_current_user())


@app.route('/remove_item', methods=['POST'])
def remove_item():
    data = request.get_json(silent=True) if request.is_json else request.form
    name = str((data or {}).get('name', '')).strip()
    cart = session.get('cart', {})
    cart.pop(name, None)
    session['cart'] = cart
    session.modified = True
    if request.is_json:
        return jsonify(get_cart_summary())
    return redirect('/?view=cart')


@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    checkout = session.get('checkout')
    if not checkout or not checkout.get('items'):
        return redirect(url_for('home'))
    address = {
        'full_name': request.form.get('full_name', '').strip(),
        'line1': request.form.get('line1', '').strip(),
        'line2': request.form.get('line2', '').strip(),
        'city': request.form.get('city', '').strip(),
        'state': request.form.get('state', '').strip(),
        'zip': request.form.get('zip', '').strip(),
        'phone': request.form.get('phone', '').strip(),
    }
    payment_method = request.form.get('payment_method', 'cod')
    payment_details = {}
    if payment_method == 'upi':
        payment_details['upi_id'] = request.form.get('upi_id', '').strip()
    elif payment_method == 'card':
        card_num = re.sub(r'\D', '', request.form.get('card_number', ''))
        payment_details['card_last4'] = card_num[-4:]
    order = {
        'user_id': ObjectId(session['user_id']),
        'items': checkout['items'],
        'total': float(checkout['total']),
        'shipping_address': address,
        'payment_method': payment_method,
        'payment_details': payment_details,
        'status': 'confirmed',
        'created_at': datetime.now(timezone.utc),
    }
    try:
        result = orders_col.insert_one(order)
    except PyMongoError:
        return render_template(
            'payment.html',
            checkout=checkout,
            user=get_current_user(),
            checkout_error='We could not place your order. Please try again.',
        ), 503
    session.pop('checkout', None)
    session['cart'] = {}
    session['order_success'] = str(result.inserted_id)[-8:].upper()
    session.modified = True
    return redirect('/?view=account&order=success')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


if __name__ == '__main__':
    app.run(debug=True, port=5050, use_reloader=False)
