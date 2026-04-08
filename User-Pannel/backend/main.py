from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from pymongo import MongoClient
import bcrypt
from bson import ObjectId
from flask import send_from_directory
import os

# ------------------ App Setup ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
template_path = os.path.join(BASE_DIR, '..', 'frontend')
admin_template_path = os.path.join(BASE_DIR, '..', '..', 'Admin', 'frontend')

app = Flask(__name__, template_folder=template_path)
app.secret_key = 'secret123'

# ------------------ MongoDB ------------------
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://127.0.0.1:27017')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'styleaccess_dev')
client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
users_col = db['users']
products_col = db['products']

# ------------------ Helpers ------------------
def parse_json(data):
    if isinstance(data, list):
        return [parse_json(item) for item in data]
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, ObjectId):
                data[k] = str(v)
        return data
    return data

def login_required(f):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def admin_required(f):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        user = users_col.find_one({'_id': ObjectId(session['user_id'])})
        if not user or user.get('role') != 'admin':
            return jsonify({'error': 'Forbidden'}), 403
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# ------------------ Auth Pages ------------------
@app.route('/login')
def login_page():
    login_dir = os.path.join(BASE_DIR, '..', '..', 'Login')
    return send_from_directory(login_dir, 'Login.html')

# ------------------ Auth APIs ------------------
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if users_col.find_one({'email': data['email']}):
        return jsonify({'error': 'Email exists'}), 400

    hashed = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())

    users_col.insert_one({
        'name': data['name'],
        'email': data['email'],
        'password': hashed,
        'role': data.get('role', 'user')
    })

    return jsonify({'message': 'Registered'}), 201

@app.route('/api/login', methods=['POST'])
def login_api():
    data = request.json
    user = users_col.find_one({'email': data['email']})

    if not user or not bcrypt.checkpw(data['password'].encode('utf-8'), user['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    session['user_id'] = str(user['_id'])

    return jsonify({
        'name': user['name'],
        'email': user['email'],
        'role': user['role']
    })

@app.route('/api/logout', methods=['POST'])
def logout_api():
    session.clear()
    return jsonify({'message': 'Logged out'})

@app.route('/api/me')
def me():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = users_col.find_one({'_id': ObjectId(session['user_id'])})

    return jsonify({
        'name': user['name'],
        'email': user['email'],
        'role': user['role']
    })

# ------------------ Products ------------------
@app.route('/api/products')
def get_products():
    return jsonify(parse_json(list(products_col.find())))

@app.route('/api/admin/products', methods=['POST'])
@admin_required
def add_product():
    data = request.json

    products_col.insert_one({
        'name': data['name'],
        'price': float(data['price']),
        'category': data.get('category', ''),
        'description': data.get('description', ''),
        'imageUrl': data.get('imageUrl', '')
    })

    return jsonify({'message': 'Added'})

@app.route('/api/admin/products/<pid>', methods=['DELETE'])
@admin_required
def delete_product(pid):
    products_col.delete_one({'_id': ObjectId(pid)})
    return jsonify({'message': 'Deleted'})

@app.route('/api/admin/products/<pid>', methods=['PUT'])
@admin_required
def update_product(pid):
    data = request.json

    products_col.update_one(
        {'_id': ObjectId(pid)},
        {'$set': data}
    )

    return jsonify({'message': 'Updated'})

# ------------------ Admin Page ------------------
@app.route('/admin')
@admin_required
def admin_dashboard():
    return send_from_directory(admin_template_path, 'index.html')

# ------------------ USER DASHBOARD ------------------
def get_products_from_db():
    products = list(products_col.find())
    if not products:
        return [
            {"name": "Watch", "price": 999, "icon": "⌚"},
            {"name": "Sunglasses", "price": 799, "icon": "🕶️"}
        ]
    return [{"name": p['name'], "price": p['price'], "icon": "📦"} for p in products]

@app.route('/')
@login_required
def home():
    if 'cart' not in session:
        session['cart'] = {}

    view = request.args.get('view', 'home')
    search_query = request.args.get('search', '').lower()

    products = get_products_from_db()

    if search_query:
        products = [p for p in products if search_query in p['name'].lower()]

    cart = session['cart']
    total = sum(item['price'] * item['qty'] for item in cart.values())

    # ✅ FIX: Fetch user from MongoDB
    user = users_col.find_one({'_id': ObjectId(session['user_id'])})

    user_data = {
        "name": user['name'],
        "email": user['email'],
        "role": user['role']
    }

    return render_template(
        'index.html',
        products=products,
        cart=cart,
        total=total,
        view=view,
        user=user_data
    )

# ------------------ CART ------------------
@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    name = request.form.get('name')
    price_str = request.form.get('price')
    print(f"DEBUG: price_str = {price_str}")   # should print '1099.0'
    price = float(price_str)       
    cart = session.get('cart', {})
    if name in cart:
        cart[name]['qty'] += 1
    else:
        cart[name] = {"price": price, "qty": 1}
    session['cart'] = cart
    session.modified = True
    return redirect(url_for('home'))

@app.route('/remove_item', methods=['POST'])
@login_required
def remove_item():
    name = request.form.get('name')

    cart = session.get('cart', {})
    if name in cart:
        del cart[name]

    session['cart'] = cart
    return redirect('/?view=cart')

@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    session['cart'] = {}
    return redirect('/')

# ------------------ LOGOUT ------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ------------------ RUN ------------------
if __name__ == '__main__':
    app.run(debug=True, port=5050, use_reloader=False)