from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Toy Store-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Toy Store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ─── Set your seller/admin email here ────────────────────────────────────────
ADMIN_EMAIL = 'admin@toystore.com'   # ← change this to your email
# ─────────────────────────────────────────────────────────────────────────────

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to continue.'
login_manager.login_message_category = 'info'

# ─── MODELS ───────────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    cart_items = db.relationship('CartItem', backref='user', lazy=True, cascade='all, delete-orphan')
    addresses = db.relationship('Address', backref='user', lazy=True, cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    original_price = db.Column(db.Float)
    image_filename = db.Column(db.String(250), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    rating = db.Column(db.Float, default=4.0)
    reviews_count = db.Column(db.Integer, default=0)
    in_stock = db.Column(db.Boolean, default=True)
    cart_items = db.relationship('CartItem', backref='product', lazy=True)


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)


class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    street = db.Column(db.String(250), nullable=False)
    city = db.Column(db.String(80), nullable=False)
    state = db.Column(db.String(80), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    is_default = db.Column(db.Boolean, default=False)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    delivery_info = db.Column(db.Text, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    shipping = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(30), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_name = db.Column(db.String(150), nullable=False)
    product_image = db.Column(db.String(250))
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ─── CONTEXT PROCESSOR ────────────────────────────────────────────────────────

@app.context_processor
def inject_cart_count():
    if current_user.is_authenticated:
        cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    else:
        cart_count = sum(session.get('cart', {}).values())
    return dict(cart_count=cart_count)


# ─── IMAGE SERVING ────────────────────────────────────────────────────────────

@app.route('/images/<path:filename>')
def product_image(filename):
    images_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images')
    return send_from_directory(images_dir, filename)


# ─── HOME ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    featured = Product.query.filter_by(in_stock=True).limit(8).all()
    categories = db.session.query(Product.category).distinct().all()
    categories = [c[0] for c in categories]
    return render_template('index.html', featured=featured, categories=categories)


# ─── PRODUCTS ─────────────────────────────────────────────────────────────────

@app.route('/products')
def products():
    category = request.args.get('category', '')
    search = request.args.get('q', '')
    query = Product.query.filter_by(in_stock=True)
    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    all_products = query.all()
    categories = db.session.query(Product.category).distinct().all()
    categories = [c[0] for c in categories]
    return render_template('products.html', products=all_products, categories=categories,
                           selected_category=category, search=search)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    related = Product.query.filter_by(category=product.category).filter(Product.id != product_id).limit(4).all()
    return render_template('product_detail.html', product=product, related=related)


# ─── AUTH ─────────────────────────────────────────────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not all([name, email, password, confirm]):
            flash('All fields are required.', 'error')
        elif password != confirm:
            flash('Passwords do not match.', 'error')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
        elif User.query.filter_by(email=email).first():
            flash('Email already registered. Please log in.', 'error')
        else:
            user = User(name=name, email=email)
            user.set_password(password)
            if email == ADMIN_EMAIL:
                user.is_admin = True
            db.session.add(user)
            db.session.commit()
            # Merge guest session cart into new account
            guest_cart = session.pop('cart', {})
            login_user(user)
            for pid_str, qty in guest_cart.items():
                pid = int(pid_str)
                db.session.add(CartItem(user_id=user.id, product_id=pid, quantity=qty))
            if guest_cart:
                db.session.commit()
            flash(f'Welcome, {name}! Your account has been created.', 'success')
            return redirect(url_for('index'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            # Merge guest session cart into DB before logging in
            guest_cart = session.pop('cart', {})
            login_user(user, remember=request.form.get('remember'))
            for pid_str, qty in guest_cart.items():
                pid = int(pid_str)
                existing = CartItem.query.filter_by(user_id=user.id, product_id=pid).first()
                if existing:
                    existing.quantity += qty
                else:
                    db.session.add(CartItem(user_id=user.id, product_id=pid, quantity=qty))
            if guest_cart:
                db.session.commit()
            flash(f'Welcome back, {user.name}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# ─── CART ─────────────────────────────────────────────────────────────────────

def _session_cart_items():
    """Return list of (product, quantity) tuples from session cart."""
    cart = session.get('cart', {})
    items = []
    for pid_str, qty in cart.items():
        product = Product.query.get(int(pid_str))
        if product:
            items.append({'product': product, 'quantity': qty,
                          'id': None, 'session_key': pid_str})
    return items


@app.route('/cart')
def cart():
    if current_user.is_authenticated:
        items = CartItem.query.filter_by(user_id=current_user.id).all()
        subtotal = sum(i.product.price * i.quantity for i in items)
        shipping = 0 if subtotal >= 499 else 49
        return render_template('cart.html', items=items, subtotal=subtotal,
                               shipping=shipping, total=subtotal + shipping,
                               is_guest=False)
    else:
        raw = session.get('cart', {})
        items = []
        for pid_str, qty in raw.items():
            p = Product.query.get(int(pid_str))
            if p:
                items.append(type('GuestItem', (), {
                    'id': None, 'product': p, 'quantity': qty,
                    'session_key': pid_str
                })())
        subtotal = sum(i.product.price * i.quantity for i in items)
        shipping = 0 if subtotal >= 499 else 49
        return render_template('cart.html', items=items, subtotal=subtotal,
                               shipping=shipping, total=subtotal + shipping,
                               is_guest=True)


@app.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 1))
    if current_user.is_authenticated:
        existing = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
        if existing:
            existing.quantity += quantity
        else:
            db.session.add(CartItem(user_id=current_user.id, product_id=product_id, quantity=quantity))
        db.session.commit()
    else:
        cart = session.get('cart', {})
        key = str(product_id)
        cart[key] = cart.get(key, 0) + quantity
        session['cart'] = cart
        session.modified = True
    flash(f'"{product.name}" added to cart!', 'success')
    next_page = request.form.get('next') or request.referrer or url_for('products')
    return redirect(next_page)


@app.route('/cart/update/<int:item_id>', methods=['POST'])
def update_cart(item_id):
    quantity = int(request.form.get('quantity', 1))
    if current_user.is_authenticated:
        item = CartItem.query.get_or_404(item_id)
        if item.user_id == current_user.id:
            if quantity <= 0:
                db.session.delete(item)
            else:
                item.quantity = quantity
            db.session.commit()
    else:
        cart = session.get('cart', {})
        key = str(item_id)  # item_id is actually product_id for guest
        if quantity <= 0:
            cart.pop(key, None)
        else:
            cart[key] = quantity
        session['cart'] = cart
        session.modified = True
    return redirect(url_for('cart'))


@app.route('/cart/remove/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    if current_user.is_authenticated:
        item = CartItem.query.get_or_404(item_id)
        if item.user_id == current_user.id:
            db.session.delete(item)
            db.session.commit()
    else:
        cart = session.get('cart', {})
        cart.pop(str(item_id), None)
        session['cart'] = cart
        session.modified = True
    flash('Item removed from cart.', 'info')
    return redirect(url_for('cart'))


# ─── CHECKOUT ─────────────────────────────────────────────────────────────────

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        flash('Your cart is empty.', 'info')
        return redirect(url_for('products'))

    addresses = Address.query.filter_by(user_id=current_user.id).all()
    subtotal = sum(item.product.price * item.quantity for item in items)
    shipping = 0 if subtotal >= 499 else 49
    total = subtotal + shipping

    if request.method == 'POST':
        address_id = request.form.get('address_id')
        if address_id == 'new' or not address_id:
            full_name = request.form.get('full_name', '').strip()
            phone = request.form.get('phone', '').strip()
            street = request.form.get('street', '').strip()
            city = request.form.get('city', '').strip()
            state = request.form.get('state', '').strip()
            pincode = request.form.get('pincode', '').strip()
            if not all([full_name, phone, street, city, state, pincode]):
                flash('Please fill in all address fields.', 'error')
                return render_template('checkout.html', items=items, addresses=addresses,
                                       subtotal=subtotal, shipping=shipping, total=total)
            save_addr = request.form.get('save_address')
            if save_addr:
                addr = Address(user_id=current_user.id, full_name=full_name, phone=phone,
                               street=street, city=city, state=state, pincode=pincode)
                db.session.add(addr)
                db.session.commit()
            delivery_info = f'{full_name}, {street}, {city}, {state} - {pincode} | Ph: {phone}'
        else:
            addr = Address.query.get(int(address_id))
            delivery_info = f'{addr.full_name}, {addr.street}, {addr.city}, {addr.state} - {addr.pincode}'

        # Capture order data BEFORE clearing the cart
        order_items_data = [{
            'name': i.product.name,
            'image': i.product.image_filename,
            'qty': i.quantity,
            'price': i.product.price
        } for i in items]

        # Save order to DB
        order = Order(
            user_id=current_user.id,
            delivery_info=delivery_info,
            subtotal=subtotal,
            shipping=shipping,
            total=total
        )
        db.session.add(order)
        db.session.flush()  # get order.id before commit
        for i in order_items_data:
            db.session.add(OrderItem(
                order_id=order.id,
                product_name=i['name'],
                product_image=i['image'],
                quantity=i['qty'],
                price=i['price']
            ))

        # Clear cart
        CartItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        return render_template('order_success.html', order_items=order_items_data, order_id=order.id,
                               delivery_info=delivery_info, total=total, subtotal=subtotal, shipping=shipping)

    return render_template('checkout.html', items=items, addresses=addresses,
                           subtotal=subtotal, shipping=shipping, total=total)


# ─── PROFILE ──────────────────────────────────────────────────────────────────

@app.route('/profile')
@login_required
def profile():
    addresses = Address.query.filter_by(user_id=current_user.id).all()
    return render_template('profile.html', addresses=addresses)


@app.route('/profile/address/add', methods=['POST'])
@login_required
def add_address():
    full_name = request.form.get('full_name', '').strip()
    phone = request.form.get('phone', '').strip()
    street = request.form.get('street', '').strip()
    city = request.form.get('city', '').strip()
    state = request.form.get('state', '').strip()
    pincode = request.form.get('pincode', '').strip()
    if all([full_name, phone, street, city, state, pincode]):
        addr = Address(user_id=current_user.id, full_name=full_name, phone=phone,
                       street=street, city=city, state=state, pincode=pincode)
        db.session.add(addr)
        db.session.commit()
        flash('Address added successfully.', 'success')
    else:
        flash('Please fill in all fields.', 'error')
    return redirect(url_for('profile'))


@app.route('/profile/address/delete/<int:addr_id>', methods=['POST'])
@login_required
def delete_address(addr_id):
    addr = Address.query.get_or_404(addr_id)
    if addr.user_id == current_user.id:
        db.session.delete(addr)
        db.session.commit()
        flash('Address removed.', 'info')
    return redirect(url_for('profile'))


# ─── ADMIN ────────────────────────────────────────────────────────────────────

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


@app.route('/admin')
@login_required
@admin_required
def admin():
    return redirect(url_for('admin_orders'))


@app.route('/admin/orders')
@login_required
@admin_required
def admin_orders():
    status_filter = request.args.get('status', '')
    query = Order.query.order_by(Order.created_at.desc())
    if status_filter:
        query = query.filter_by(status=status_filter)
    orders = query.all()
    total_revenue = sum(o.total for o in Order.query.all())
    pending_count = Order.query.filter_by(status='Pending').count()
    return render_template('admin_orders.html', orders=orders,
                           total_revenue=total_revenue,
                           pending_count=pending_count,
                           status_filter=status_filter)


@app.route('/admin/orders/<int:order_id>')
@login_required
@admin_required
def admin_order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('admin_order_detail.html', order=order)


@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
@login_required
@admin_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    if new_status in ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']:
        order.status = new_status
        db.session.commit()
        flash(f'Order #{order_id} marked as {new_status}.', 'success')
    return redirect(url_for('admin_orders'))


# ─── SEED DATA ────────────────────────────────────────────────────────────────


PRODUCTS = [
    {
        "name": "Soft Plush Teddy Bear",
        "description": "Adorable brown teddy bear with a classic checkered bow tie. Made from ultra-soft premium plush fabric, safe for all ages. Perfect as a gift or cuddle companion. Height: 30 cm.",
        "price": 499.00,
        "original_price": 799.00,
        "image": "WhatsApp Image 2026-03-03 at 11.40.24 PM.jpeg",
        "category": "Soft Toys",
        "rating": 4.7,
        "reviews": 128
    },
    {
        "name": "Spider-Man Titan Hero Action Figure",
        "description": "Marvel's Titan Hero Series Spider-Man action figure, 30 cm tall. Highly detailed movie-accurate design with articulated limbs. Comes in display packaging. Suitable for ages 4+.",
        "price": 799.00,
        "original_price": 1299.00,
        "image": "WhatsApp Image 2026-03-03 at 11.40.25 PM (1).jpeg",
        "category": "Action Figures",
        "rating": 4.6,
        "reviews": 214
    },
    {
        "name": "Little Tikes Lil' Rollin' Giraffe Ride-On",
        "description": "Bright yellow Little Tikes Go & Grow Lil' Rollin' Giraffe ride-on toy. Features foot-to-floor motion and stable four-wheel base for safe indoor/outdoor riding. Teal accent wheels. Recommended for ages 1–3.",
        "price": 2499.00,
        "original_price": 3999.00,
        "image": "WhatsApp Image 2026-03-03 at 11.40.25 PM (2) copy.jpeg",
        "category": "Ride-On Toys",
        "rating": 4.8,
        "reviews": 96
    },

    {
        "name": "Construction Truck Mega Toy Set",
        "description": "Action-packed play set featuring a large yellow carrier truck, mini excavator, cement mixer, dump truck and worker figurines. Durable ABS plastic with realistic detailing. Ages 3+.",
        "price": 1199.00,
        "original_price": 1799.00,
        "image": "WhatsApp Image 2026-03-03 at 11.40.25 PM.jpeg",
        "category": "Vehicle Toys",
        "rating": 4.5,
        "reviews": 85
    },
    {
        "name": "Little Tikes Crocodile Teeter Totter",
        "description": "Fun bright-green crocodile-shaped seesaw from Little Tikes. Sturdy plastic with non-slip foot pegs and comfortable handles. Supports two children simultaneously. Outdoor & indoor use. Ages 2–5.",
        "price": 3499.00,
        "original_price": 4999.00,
        "image": "WhatsApp Image 2026-03-03 at 11.40.26 PM (1).jpeg",
        "category": "Outdoor Toys",
        "rating": 4.6,
        "reviews": 302
    },
    {
        "name": "Dancing Cactus Singing Plush Toy",
        "description": "Adorable knitted cactus plush with googly eyes that wiggles and dances to music! Press its belly to activate songs and movements. USB rechargeable. Great sensory toy for toddlers. Height: 28 cm.",
        "price": 699.00,
        "original_price": 999.00,
        "image": "WhatsApp Image 2026-03-03 at 11.40.26 PM.jpeg",
        "category": "Electronic Toys",
        "rating": 4.7,
        "reviews": 73
    },
    {
        "name": "Musical Animal Piano Toy",
        "description": "Colourful toddler piano keyboard with large animal-themed keys and googly eyes. Plays melodies and animal sounds with light-up keys. Stimulates musical creativity and fine motor skills. Battery operated. Ages 1+.",
        "price": 849.00,
        "original_price": 1299.00,
        "image": "WhatsApp Image 2026-03-03 at 11.40.27 PM (1).jpeg",
        "category": "Electronic Toys",
        "rating": 4.5,
        "reviews": 148
    },
    {
        "name": "Spiral Car Ramp Racing Track Set",
        "description": "Multi-level spiral car ramp set in vibrant blue and orange. Includes 4 die-cast mini cars. Drop cars at the top and watch them race down the spiral! Develops hand-eye coordination. Ages 3+.",
        "price": 999.00,
        "original_price": 1499.00,
        "image": "WhatsApp Image 2026-03-03 at 11.40.27 PM.jpeg",
        "category": "Vehicle Toys",
        "rating": 4.4,
        "reviews": 189
    },
    {
        "name": "Duck Stacking Rings Toy",
        "description": "Classic stacking ring toy with a cheerful rubber duck topper. 6 colourful rings to stack in size order. Helps develop colour recognition, sorting skills and fine motor coordination. BPA-free. Ages 6 months+.",
        "price": 349.00,
        "original_price": 599.00,
        "image": "WhatsApp Image 2026-03-03 at 11.40.28 PM (1).jpeg",
        "category": "Learning Toys",
        "rating": 4.7,
        "reviews": 54
    },
    {
        "name": "Kids Ride-On UTV Off-Road Toy Car",
        "description": "Bold red motorised UTV ride-on vehicle with blue seats and grippy wheels. Battery-powered with forward/reverse control. Wide stable base for safety. Max weight: 25 kg. Recommended ages 3–6.",
        "price": 4999.00,
        "original_price": 6999.00,
        "image": "WhatsApp Image 2026-03-03 at 11.40.28 PM (2).jpeg",
        "category": "Ride-On Toys",
        "rating": 4.5,
        "reviews": 112
    },
    {
        "name": "Wooden Xylophone Musical Toy",
        "description": "8-key colourful wooden xylophone with two wooden mallets. Each key plays a clear, melodic note. Non-toxic paint, smooth edges, sturdy construction. Encourages musical exploration. Ages 18 months+.",
        "price": 449.00,
        "original_price": 699.00,
        "image": "WhatsApp Image 2026-03-03 at 11.40.28 PM.jpeg",
        "category": "Learning Toys",
        "rating": 4.6,
        "reviews": 231
    },
    {
        "name": "Pop-It Fidget Toy Set (5 Pieces)",
        "description": "Set of 5 silicone pop-it sensory fidget toys in fun shapes: Unicorn, Heart, Square, Hexagon and Circle. Satisfying to push and pop! Stress-relieving, washable and reusable. Great for all ages.",
        "price": 299.00,
        "original_price": 499.00,
        "image": "WhatsApp Image 2026-03-03 at 11.40.29 PM.jpeg",
        "category": "Fidget Toys",
        "rating": 4.8,
        "reviews": 178
    },
]


def seed_products():
    if Product.query.count() == 0:
        for p in PRODUCTS:
            product = Product(
                name=p['name'],
                description=p['description'],
                price=p['price'],
                original_price=p.get('original_price'),
                image_filename=p['image'],
                category=p['category'],
                rating=p['rating'],
                reviews_count=p['reviews'],
                in_stock=True
            )
            db.session.add(product)
        db.session.commit()
        print(f"✅ Seeded {len(PRODUCTS)} products.")


def update_products():
    """Sync DB products to PRODUCTS list, matching by image filename.
    Adds missing products, updates existing ones, and deletes removed ones."""
    product_map = {p['image']: p for p in PRODUCTS}
    existing = Product.query.all()
    existing_map = {p.image_filename: p for p in existing}

    # Delete products no longer in PRODUCTS list
    for img, db_product in existing_map.items():
        if img not in product_map:
            db.session.delete(db_product)

    # Update or insert
    for img, p in product_map.items():
        if img in existing_map:
            db_product = existing_map[img]
            db_product.name = p['name']
            db_product.description = p['description']
            db_product.price = p['price']
            db_product.original_price = p.get('original_price')
            db_product.category = p['category']
            db_product.rating = p['rating']
            db_product.reviews_count = p['reviews']
        else:
            db.session.add(Product(
                name=p['name'], description=p['description'],
                price=p['price'], original_price=p.get('original_price'),
                image_filename=p['image'], category=p['category'],
                rating=p['rating'], reviews_count=p['reviews'], in_stock=True
            ))

    db.session.commit()
    print(f"✅ Products synced: {len(PRODUCTS)} active.")


# ─── INIT DB (runs under gunicorn AND python app.py) ──────────────────────────

with app.app_context():
    db.create_all()
    seed_products()
    update_products()

if __name__ == '__main__':
    app.run(debug=True, port=5000)

