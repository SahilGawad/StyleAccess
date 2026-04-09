from flask import Flask, render_template, request, redirect, session, url_for, jsonify, send_from_directory
from pymongo import MongoClient
import bcrypt
from bson import ObjectId
from dotenv import load_dotenv
import os

# ------------------ Load ENV ------------------
load_dotenv()

# ------------------ App Setup ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
template_path = os.path.join(BASE_DIR, '..', 'frontend')
admin_template_path = os.path.join(BASE_DIR, '..', '..', 'Admin', 'frontend')

app = Flask(__name__, template_folder=template_path)
app.secret_key = 'secret123'

# ------------------ MongoDB (FIXED) ------------------
MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'styleaccess_dev')

# ❌ Stop if URI missing
if not MONGO_URI:
    raise Exception("❌ MONGO_URI not found in .env file")

print("✅ Using Mongo URI:", MONGO_URI)

client = MongoClient(MONGO_URI)

# ✅ Test connection
try:
    client.admin.command('ping')
    print("✅ Connected to MongoDB Atlas successfully")
except Exception as e:
    print("❌ MongoDB connection failed:", e)

db = client[MONGO_DB_NAME]

users_col = db['users']
products_col = db['products']
orders_col = db['orders']

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
    price = float(request.form.get('price'))

    cart = session.get('cart', {})
    if name in cart:
        cart[name]['qty'] += 1
    else:
        cart[name] = {"price": price, "qty": 1}

    session['cart'] = cart
    session.modified = True
    return redirect(url_for('home'))

@app.route('/buy_now', methods=['POST'])
@login_required
def buy_now():
    try:
        # Accept either JSON (fetch) or form-encoded submissions.
        data = {}

        # If the request's Content-Type is application/json (or compatible), parse JSON safely.
        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            # Prefer form data when present (regular HTML forms / xhr form submissions)
            if request.form:
                data = request.form.to_dict()
            else:
                # As a last resort, attempt to parse the raw body as JSON even if the header is missing/wrong.
                try:
                    raw = request.get_data(as_text=True)
                    if raw:
                        import json
                        data = json.loads(raw)
                    else:
                        data = {}
                except Exception:
                    data = {}

        # Extract fields with safe fallbacks
        name = data.get('name') if isinstance(data, dict) else None
        price_raw = data.get('price') if isinstance(data, dict) else 0
        try:
            price = float(price_raw or 0)
        except Exception:
            price = 0.0

        cart_item = {
            'name': name,
            'price': price,
            'qty': 1
        }

        # Save a one-item checkout in session and respond with JSON including redirect URL
        session['checkout'] = {
            'items': [cart_item],
            'total': price
        }
        session.modified = True

        return jsonify({'message': 'OK', 'redirect': url_for('payment_page')})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/payment')
@login_required
def payment_page():
    # Render payment page. If no explicit one-item checkout exists,
    # fall back to full cart.
    checkout = session.get('checkout')
    if not checkout:
        cart = session.get('cart', {})
        if not cart:
            return redirect(url_for('home'))
        items = [{'name': name, 'price': item['price'], 'qty': item['qty']} for name, item in cart.items()]
        total = sum(i['price'] * i['qty'] for i in items)
        checkout = {'items': items, 'total': total}
        session['checkout'] = checkout

    user = users_col.find_one({'_id': ObjectId(session['user_id'])})
    user_data = {
        "name": user['name'],
        "email": user['email'],
        "role": user['role']
    }

    return render_template('payment.html', checkout=checkout, user=user_data)


# --- Temporary test endpoint (no auth) to debug buy_now handling locally ---
@app.route('/_test_buy_now', methods=['POST'])
def _test_buy_now():
    try:
        data = {}
        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            if request.form:
                data = request.form.to_dict()
            else:
                try:
                    raw = request.get_data(as_text=True)
                    if raw:
                        import json
                        data = json.loads(raw)
                    else:
                        data = {}
                except Exception:
                    data = {}

        name = data.get('name') if isinstance(data, dict) else None
        price_raw = data.get('price') if isinstance(data, dict) else 0
        try:
            price = float(price_raw or 0)
        except Exception:
            price = 0.0

        return jsonify({'received': {'name': name, 'price': price}})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


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
    # Build order from session checkout or cart
    checkout = session.get('checkout')
    if checkout:
        items = checkout.get('items', [])
        total = checkout.get('total', 0.0)
    else:
        cart = session.get('cart', {})
        items = [{'name': name, 'price': item['price'], 'qty': item['qty']} for name, item in cart.items()]
        total = sum(i['price'] * i['qty'] for i in items)

    # Address
    address = {
        'full_name': request.form.get('full_name'),
        'line1': request.form.get('line1'),
        'line2': request.form.get('line2'),
        'city': request.form.get('city'),
        'state': request.form.get('state'),
        'zip': request.form.get('zip'),
        'phone': request.form.get('phone')
    }

    payment_method = request.form.get('payment_method')
    payment_details = {}
    if payment_method == 'upi':
        payment_details['upi_id'] = request.form.get('upi_id')
    elif payment_method == 'gift':
        payment_details['voucher_code'] = request.form.get('voucher_code')
    elif payment_method == 'card':
        card_num = request.form.get('card_number') or ''
        payment_details['card_last4'] = card_num[-4:]

    try:
        user_id = ObjectId(session['user_id'])
    except Exception:
        user_id = None

    order = {
        'user_id': user_id,
        'items': items,
        'total': float(total),
        'shipping_address': address,
        'payment_method': payment_method,
        'payment_details': payment_details,
        'status': 'placed'
    }

    orders_col.insert_one(order)

    # cleanup
    session.pop('checkout', None)
    session['cart'] = {}
    session.modified = True

    return redirect('/')

# ------------------ LOGOUT ------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ------------------ RUN ------------------
if __name__ == '__main__':
    app.run(debug=True, port=5050, use_reloader=False)