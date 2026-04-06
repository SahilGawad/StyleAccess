from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from pymongo import MongoClient
import bcrypt
from bson import ObjectId
from flask import send_from_directory
import os

# ------------------ App Setup ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
template_path = os.path.join(BASE_DIR, '..', 'frontend')          # User dashboard
admin_template_path = os.path.join(BASE_DIR, '..', '..', 'Admin', 'frontend')  # Admin dashboard

app = Flask(__name__, template_folder=template_path)
app.secret_key = 'secret123'   # change in production!

# MongoDB connection (use a separate DB to avoid conflicts)
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://127.0.0.1:27017')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'styleaccess_dev')
client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
users_col = db['users']
products_col = db['products']

# ------------------ Helper Functions ------------------
def parse_json(data):
    """Convert MongoDB documents to JSON‑serializable format."""
    if isinstance(data, list):
        return [parse_json(item) for item in data]
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, ObjectId):
                data[k] = str(v)
        return data
    return data

def login_required(f):
    """Decorator to protect routes that require authentication."""
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def admin_required(f):
    """Decorator for admin‑only API routes."""
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        user = users_col.find_one({'_id': ObjectId(session['user_id'])})
        if not user or user.get('role') != 'admin':
            return jsonify({'error': 'Forbidden'}), 403
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# ------------------ Authentication Routes (HTML pages) ------------------
@app.route('/login')
def login_page():
    # backend is in User-Pannel/backend; Login.html lives at project-root/Login
    login_dir = os.path.join(BASE_DIR, '..', '..', 'Login')
    return send_from_directory(login_dir, 'Login.html')
# ------------------ API Routes for Login/Register (used by frontend JS) ------------------
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    name = data.get('name')
    password = data.get('password')
    role = data.get('role', 'user')

    if users_col.find_one({'email': email}):
        return jsonify({'error': 'Email already exists'}), 400

    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    user_id = users_col.insert_one({
        'name': name,
        'email': email,
        'password': hashed,
        'role': role
    }).inserted_id
    return jsonify({'message': 'Registered', 'id': str(user_id)}), 201

@app.route('/api/login', methods=['POST'])
def login_api():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    user = users_col.find_one({'email': email})
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    session['user_id'] = str(user['_id'])
    session['user_role'] = user['role']
    return jsonify({
        'id': str(user['_id']),
        'name': user['name'],
        'email': user['email'],
        'role': user['role']
    }), 200

@app.route('/api/logout', methods=['POST'])
def logout_api():
    session.pop('user_id', None)
    session.pop('user_role', None)
    return jsonify({'message': 'Logged out'}), 200

@app.route('/api/me', methods=['GET'])
def me():
    """Return the currently authenticated user from session."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = users_col.find_one({'_id': ObjectId(session['user_id'])})
    if not user:
        session.clear()
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify({
        'id': str(user['_id']),
        'name': user.get('name', ''),
        'email': user.get('email', ''),
        'role': user.get('role', 'user')
    }), 200

# ------------------ Product API (public read, admin write) ------------------
@app.route('/api/products', methods=['GET'])
def get_products():
    """List all products (used by both user & admin dashboards)."""
    all_products = list(products_col.find({}))
    return jsonify(parse_json(all_products)), 200

@app.route('/api/admin/products', methods=['POST'])
@admin_required
def add_product():
    data = request.json
    required = ['name', 'price', 'category', 'description']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing fields'}), 400
    new_product = {
        'name': data['name'],
        'price': float(data['price']),
        'category': data['category'],
        'description': data['description'],
        'imageUrl': data.get('imageUrl', 'https://picsum.photos/id/20/300/200')
    }
    result = products_col.insert_one(new_product)
    return jsonify({'message': 'Product added', 'id': str(result.inserted_id)}), 201

@app.route('/api/admin/products/<pid>', methods=['PUT'])
@admin_required
def update_product(pid):
    data = request.json
    update_data = {}
    for field in ['name', 'price', 'category', 'description', 'imageUrl']:
        if field in data:
            update_data[field] = float(data[field]) if field == 'price' else data[field]
    products_col.update_one({'_id': ObjectId(pid)}, {'$set': update_data})
    return jsonify({'message': 'Updated'}), 200

@app.route('/api/admin/products/<pid>', methods=['DELETE'])
@admin_required
def delete_product(pid):
    products_col.delete_one({'_id': ObjectId(pid)})
    return jsonify({'message': 'Deleted'}), 200

# ------------------ Admin Dashboard HTML ------------------
@app.route('/admin')
@app.route('/admin-panel')
@admin_required
def admin_dashboard():
    """Serve the admin panel (CRUD interface)."""
    resp = send_from_directory(admin_template_path, 'index.html')
    resp.headers['X-Admin-Template-Path'] = os.path.normpath(admin_template_path)
    return resp

# ------------------ EXISTING USER DASHBOARD + CART (preserved) ------------------
def get_products_from_db():
    """Fetch products from MongoDB (fallback to hardcoded list if empty)."""
    products = list(products_col.find({}))
    if not products:
        # Hardcoded fallback (keeps your original products)
        return [
            {"name": "Luxury Watch", "price": 2499, "icon": "⌚"},
            {"name": "Stylish Shades", "price": 999, "icon": "🕶️"},
            {"name": "Office Bag", "price": 1850, "icon": "💼"}
        ]
    # Convert to format expected by the template
    return [{"name": p['name'], "price": p['price'], "icon": p.get('icon', '📦')} for p in products]

@app.route('/')
@login_required
def home():
    """User dashboard – shows products, cart, search (exactly as before)."""
    if 'cart' not in session:
        session['cart'] = {}

    view = request.args.get('view', 'home')
    search_query = request.args.get('search', '').lower()

    # Get products (now from MongoDB, but fallback preserves old behaviour)
    products = get_products_from_db()

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
@login_required
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
@login_required
def remove_item():
    name = request.form.get('name')
    cart = session.get('cart', {})
    if name in cart:
        del cart[name]
    session['cart'] = cart
    session.modified = True
    return redirect(url_for('home', view='cart'))

@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    session['cart'] = {}
    session.modified = True
    return redirect(url_for('home'))

# ------------------ LOGOUT ROUTE (for frontend link) ------------------
@app.route('/logout')
def logout():
    """Clear session and redirect to login page."""
    session.clear()                     # removes user_id, cart, etc.
    return redirect(url_for('login_page'))

# ------------------ Seed initial data (if collections empty) ------------------
def seed_data():
    if users_col.count_documents({}) == 0:
        admin_hash = bcrypt.hashpw(b'admin123', bcrypt.gensalt())
        user_hash = bcrypt.hashpw(b'user123', bcrypt.gensalt())
        users_col.insert_many([
            {'name': 'Demo User', 'email': 'user@broverse.com', 'password': user_hash, 'role': 'user'},
            {'name': 'Admin', 'email': 'admin@broverse.com', 'password': admin_hash, 'role': 'admin'}
        ])
    if products_col.count_documents({}) == 0:
        # Insert your original products into MongoDB so admin can edit them later
        products_col.insert_many([
            {'name': 'Luxury Watch', 'price': 2499, 'category': 'Watches', 'description': 'Elegant timepiece', 'icon': '⌚', 'imageUrl': 'https://picsum.photos/id/20/300/200'},
            {'name': 'Stylish Shades', 'price': 999, 'category': 'Eyewear', 'description': 'UV protection', 'icon': '🕶️', 'imageUrl': 'https://picsum.photos/id/22/300/200'},
            {'name': 'Office Bag', 'price': 1850, 'category': 'Bags', 'description': 'Durable leather', 'icon': '💼', 'imageUrl': 'https://picsum.photos/id/24/300/200'}
        ])

with app.app_context():
    seed_data()

if __name__ == '__main__':
    # Disable auto-reloader to avoid intermittent WinError 10038 on Windows.
    app.run(debug=True, port=5050, use_reloader=False)