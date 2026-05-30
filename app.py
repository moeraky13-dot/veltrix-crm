"""
VELTRIX CRM — منصة التجارة الإلكترونية الذكية
Backend: Python + Flask | Database: SQLite | Frontend: HTML + CSS + JS
"""
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, g
)
import sqlite3
import sys
import os
import socket
import secrets
import random
import string
import re
from datetime import datetime
from functools import wraps
from database import get_db, hash_password, verify_password, init_db
from i18n import normalize_lang, translate, category_label, DEFAULT_LANG

# تجنب UnicodeEncodeError عند الطباعة (عربي/رموز) على وحدة تحكم Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ===== إنشاء التطبيق =====
app = Flask(__name__)
app.secret_key = 'veltrix-super-secret-key-2026-xK9!mN#pQ'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB


def _current_lang():
    return getattr(g, 'lang', session.get('lang', DEFAULT_LANG))


@app.before_request
def load_language():
    lang = session.get('lang')
    if not lang:
        lang = request.accept_languages.best_match(['ar', 'en']) or DEFAULT_LANG
    g.lang = normalize_lang(lang)
    session['lang'] = g.lang


@app.route('/set-lang/<lang>')
def set_language(lang):
    session['lang'] = normalize_lang(lang)
    return redirect(request.referrer or url_for('index'))


# ===== دوال مساعدة =====

def login_required(f):
    """ديكوريتور: يشترط تسجيل الدخول"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash(translate(_current_lang(), 'flash_login_required'), 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """ديكوريتور: يشترط صلاحية المسؤول"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash(translate(_current_lang(), 'flash_admin_login'), 'warning')
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash(translate(_current_lang(), 'flash_no_permission'), 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    """الحصول على بيانات المستخدم الحالي"""
    if 'user_id' not in session:
        return None
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    db.close()
    return user


def get_cart_count():
    """عدد منتجات السلة للمستخدم الحالي"""
    if 'user_id' not in session:
        return 0
    db = get_db()
    count = db.execute(
        "SELECT COALESCE(SUM(quantity),0) FROM cart_items WHERE user_id=?",
        (session['user_id'],)
    ).fetchone()[0]
    db.close()
    return count


def start_user_session(user, remember=False):
    """فتح جلسة للمستخدم بعد تسجيل الدخول."""
    session.permanent = bool(remember)
    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['is_admin'] = bool(user['is_admin'])


def make_category_slug(text):
    """تحويل نص إلى slug لاتيني للفئات."""
    text = (text or '').strip().lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text).strip('-')
    return text or 'category'


def get_categories(active_only=True):
    """قائمة فئات المتجر من قاعدة البيانات (ترتيب + عدد المنتجات)."""
    db = get_db()
    where = "WHERE c.is_active=1" if active_only else ""
    cats = db.execute(f"""
        SELECT c.*, COUNT(p.id) as products_count
        FROM categories c
        LEFT JOIN products p ON p.category_id = c.id AND p.is_active=1
        {where}
        GROUP BY c.id
        ORDER BY c.sort_order ASC, c.name ASC
    """).fetchall()
    db.close()
    return cats


def category_display_image(category):
    """صورة الفئة من قاعدة البيانات أو الافتراضي."""
    url = category['image_url'] if category['image_url'] else None
    return url or get_category_image(category['slug'])


def generate_order_number():
    """توليد رقم طلب فريد"""
    prefix = 'ORD'
    date_part = datetime.now().strftime('%y%m%d')
    rand_part = ''.join(random.choices(string.digits, k=4))
    return f"{prefix}-{date_part}-{rand_part}"


def get_product_icon(name):
    """الحصول على أيقونة مناسبة للمنتج حسب اسمه"""
    name_lower = name.lower()
    if any(x in name_lower for x in ['iphone', 'galaxy s', 'galaxy note', 'ipad']):
        return '📱'
    elif any(x in name_lower for x in ['macbook', 'laptop', 'dell', 'lenovo', 'hp ', 'asus']):
        return '💻'
    elif any(x in name_lower for x in ['airpods', 'wh-', 'headphone', 'earbuds', 'sennheiser']):
        return '🎧'
    elif any(x in name_lower for x in ['watch', 'ساعة']):
        return '⌚'
    elif any(x in name_lower for x in ['camera', 'canon', 'nikon', 'sony a', 'كاميرا']):
        return '📷'
    elif any(x in name_lower for x in ['mouse', 'keyboard', 'logitech', 'ماوس']):
        return '🖱️'
    else:
        return '📦'


def get_category_image(slug):
    """إرجاع صورة حقيقية مناسبة للفئة"""
    category_images = {
        'smartphones': 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=500&q=80',
        'laptops': 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=500&q=80',
        'headphones': 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=500&q=80',
        'cameras': 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=500&q=80',
        'accessories': 'https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=500&q=80',
        'smartwatches': 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=500&q=80',
    }
    return category_images.get(slug, category_images['accessories'])


# Context processor يحقن المتغيرات لجميع القوالب
@app.context_processor
def inject_globals():
    lang = _current_lang()
    return {
        'current_user': get_current_user(),
        'cart_count': get_cart_count(),
        'all_categories': get_categories(),
        'get_icon': get_product_icon,
        'get_category_image': get_category_image,
        'category_display_image': category_display_image,
        'now': datetime.now(),
        'current_lang': lang,
        'is_rtl': lang == 'ar',
        '_': lambda key, **kw: translate(lang, key, **kw),
        'category_label': lambda cat: category_label(lang, cat),
    }


# ============================================================
#  ██████╗  ██████╗ ██╗   ██╗████████╗███████╗███████╗
#  ██╔══██╗██╔═══██╗██║   ██║╚══██╔══╝██╔════╝██╔════╝
#  ██████╔╝██║   ██║██║   ██║   ██║   █████╗  ███████╗
#  ██╔══██╗██║   ██║██║   ██║   ██║   ██╔══╝  ╚════██║
#  ██║  ██║╚██████╔╝╚██████╔╝   ██║   ███████╗███████║
#  ╚═╝  ╚═╝ ╚═════╝  ╚═════╝    ╚═╝   ╚══════╝╚══════╝
#
#  المسارات الرئيسية (صفحات المستخدم)
# ============================================================

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    db = get_db()
    featured = db.execute(
        "SELECT * FROM products WHERE is_featured=1 AND is_active=1 ORDER BY sales_count DESC LIMIT 8"
    ).fetchall()
    best_sellers = db.execute(
        "SELECT * FROM products WHERE is_active=1 ORDER BY sales_count DESC LIMIT 6"
    ).fetchall()
    new_arrivals = db.execute(
        "SELECT * FROM products WHERE is_active=1 ORDER BY created_at DESC LIMIT 4"
    ).fetchall()
    categories = get_categories()
    return render_template('index.html',
                           featured=featured, best_sellers=best_sellers,
                           new_arrivals=new_arrivals, categories=categories)


# ============================================================
#  المصادقة (Auth)
# ============================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember')

        if not email or not password:
            flash(translate(_current_lang(), 'flash_login_empty'), 'danger')
            return render_template('login.html')

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

        if user and verify_password(password, user['password_hash']):
            if not user['is_active']:
                flash(translate(_current_lang(), 'flash_banned'), 'danger')
                db.close()
                return render_template('login.html')

            start_user_session(user, remember=remember)

            db.execute("UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE id=?", (user['id'],))
            db.commit()
            db.close()

            flash(translate(_current_lang(), 'flash_welcome', name=user['name']) + ' 👋', 'success')
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('admin_dashboard') if user['is_admin'] else url_for('index'))
        else:
            db.close()
            flash(translate(_current_lang(), 'flash_login_fail'), 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()

        lang = _current_lang()
        errors = []
        if len(name) < 3:
            errors.append(translate(lang, 'flash_name_short'))
        if '@' not in email:
            errors.append(translate(lang, 'flash_email_invalid'))
        if len(password) < 8:
            errors.append(translate(lang, 'flash_password_short'))
        if password != confirm:
            errors.append(translate(lang, 'flash_password_mismatch'))

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('register.html')

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            flash(translate(lang, 'flash_email_exists'), 'danger')
            db.close()
            return render_template('register.html')

        db.execute(
            "INSERT INTO users (name, email, password_hash, phone) VALUES (?,?,?,?)",
            (name, email, hash_password(password), phone)
        )
        db.commit()
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        db.close()

        start_user_session(user)
        flash(translate(lang, 'flash_register_ok', name=name) + ' 🎉', 'success')
        return redirect(url_for('index'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    lang = session.get('lang', DEFAULT_LANG)
    session.clear()
    session['lang'] = normalize_lang(lang)
    flash(translate(lang, 'flash_logout'), 'info')
    return redirect(url_for('index'))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = get_current_user()
    db = get_db()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        old_pw = request.form.get('old_password', '')
        new_pw = request.form.get('new_password', '')

        if new_pw:
            if not verify_password(old_pw, user['password_hash']):
                flash('كلمة المرور الحالية غير صحيحة', 'danger')
                db.close()
                return render_template('profile.html', user=user)
            if len(new_pw) < 8:
                flash('كلمة المرور الجديدة 8 أحرف على الأقل', 'danger')
                db.close()
                return render_template('profile.html', user=user)
            db.execute(
                "UPDATE users SET name=?, phone=?, address=?, password_hash=? WHERE id=?",
                (name, phone, address, hash_password(new_pw), session['user_id'])
            )
        else:
            db.execute(
                "UPDATE users SET name=?, phone=?, address=? WHERE id=?",
                (name, phone, address, session['user_id'])
            )
        db.commit()
        session['user_name'] = name
        flash('تم تحديث بياناتك ✅', 'success')
        user = db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()

    orders_count = db.execute(
        "SELECT COUNT(*) FROM orders WHERE user_id=?", (session['user_id'],)
    ).fetchone()[0]
    total_spent = db.execute(
        "SELECT COALESCE(SUM(total),0) FROM orders WHERE user_id=? AND status!='cancelled'",
        (session['user_id'],)
    ).fetchone()[0]
    db.close()

    return render_template('profile.html', user=user,
                           orders_count=orders_count, total_spent=total_spent)


# ============================================================
#  المنتجات (Products)
# ============================================================

@app.route('/products')
def products():
    """قائمة المنتجات مع بحث وفلترة"""
    page = request.args.get('page', 1, type=int)
    per_page = 12
    q = request.args.get('q', '').strip()
    category_slug = request.args.get('category', '')
    sort = request.args.get('sort', 'popular')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)

    db = get_db()

    # بناء الاستعلام ديناميكياً
    where_clauses = ["p.is_active=1"]
    params = []

    current_category = None
    if category_slug:
        current_category = db.execute(
            "SELECT * FROM categories WHERE slug=?", (category_slug,)
        ).fetchone()
        if current_category:
            where_clauses.append("p.category_id=?")
            params.append(current_category['id'])

    if q:
        where_clauses.append("(p.name LIKE ? OR p.description LIKE ? OR p.brand LIKE ?)")
        params.extend([f'%{q}%', f'%{q}%', f'%{q}%'])

    if min_price is not None:
        where_clauses.append("p.price >= ?")
        params.append(min_price)
    if max_price is not None:
        where_clauses.append("p.price <= ?")
        params.append(max_price)

    where_sql = " AND ".join(where_clauses)

    order_map = {
        'popular': 'p.sales_count DESC',
        'newest': 'p.created_at DESC',
        'price_asc': 'p.price ASC',
        'price_desc': 'p.price DESC',
    }
    order_sql = order_map.get(sort, 'p.sales_count DESC')

    total = db.execute(
        f"SELECT COUNT(*) FROM products p WHERE {where_sql}", params
    ).fetchone()[0]

    offset = (page - 1) * per_page
    items = db.execute(
        f"SELECT p.*, c.name as cat_name, c.slug as cat_slug FROM products p "
        f"LEFT JOIN categories c ON c.id=p.category_id "
        f"WHERE {where_sql} ORDER BY {order_sql} LIMIT ? OFFSET ?",
        params + [per_page, offset]
    ).fetchall()

    categories = get_categories()
    db.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template('products.html',
                           items=items, total=total,
                           page=page, total_pages=total_pages,
                           q=q, sort=sort, category_slug=category_slug,
                           current_category=current_category,
                           categories=categories,
                           min_price=min_price, max_price=max_price)


@app.route('/product/<int:pid>')
def product_detail(pid):
    """صفحة تفاصيل المنتج"""
    db = get_db()
    product = db.execute(
        "SELECT p.*, c.name as cat_name, c.slug as cat_slug "
        "FROM products p LEFT JOIN categories c ON c.id=p.category_id "
        "WHERE p.id=? AND p.is_active=1", (pid,)
    ).fetchone()

    if not product:
        db.close()
        flash('المنتج غير موجود', 'danger')
        return redirect(url_for('products'))

    # زيادة المشاهدات
    db.execute("UPDATE products SET views_count=views_count+1 WHERE id=?", (pid,))
    db.commit()

    # منتجات مشابهة من نفس الفئة
    similar = []
    if product['category_id']:
        similar = db.execute(
            "SELECT * FROM products WHERE category_id=? AND id!=? AND is_active=1 "
            "ORDER BY sales_count DESC LIMIT 4",
            (product['category_id'], pid)
        ).fetchall()

    # جلب التقييمات
    reviews = db.execute("""
        SELECT r.*, u.name as user_name
        FROM reviews r JOIN users u ON u.id=r.user_id
        WHERE r.product_id=? ORDER BY r.created_at DESC
    """, (pid,)).fetchall()
    avg_rating = db.execute(
        "SELECT ROUND(AVG(rating),1) FROM reviews WHERE product_id=?", (pid,)
    ).fetchone()[0] or 0
    user_reviewed = False
    if session.get("user_id"):
        user_reviewed = bool(db.execute(
            "SELECT id FROM reviews WHERE product_id=? AND user_id=?",
            (pid, session["user_id"])
        ).fetchone())
    db.close()
    return render_template("product_detail.html", product=product, similar=similar, reviews=reviews, avg_rating=avg_rating, user_reviewed=user_reviewed)


# ============================================================
#  سلة التسوق (Cart)
# ============================================================

@app.route('/cart')
@login_required
def cart():
    """عرض السلة"""
    db = get_db()
    items = db.execute("""
        SELECT ci.*, p.name, p.price, p.stock, p.brand, p.image,
               (ci.quantity * p.price) as subtotal
        FROM cart_items ci
        JOIN products p ON p.id=ci.product_id
        WHERE ci.user_id=?
    """, (session['user_id'],)).fetchall()
    db.close()

    subtotal = sum(i['subtotal'] for i in items)
    shipping = 0 if subtotal >= 500 else (50 if subtotal > 0 else 0)
    grand_total = subtotal + shipping

    return render_template('cart.html', items=items,
                           subtotal=subtotal, shipping=shipping, grand_total=grand_total)


@app.route('/cart/add/<int:pid>', methods=['POST'])
@login_required
def cart_add(pid):
    """إضافة منتج للسلة"""
    qty = int(request.form.get('quantity', 1))
    db = get_db()
    product = db.execute(
        "SELECT * FROM products WHERE id=? AND is_active=1", (pid,)
    ).fetchone()

    if not product:
        flash('المنتج غير متاح', 'danger')
        db.close()
        return redirect(url_for('products'))

    if product['stock'] < qty:
        flash(f"المخزون المتاح: {product['stock']} فقط", 'warning')
        db.close()
        return redirect(url_for('product_detail', pid=pid))

    existing = db.execute(
        "SELECT * FROM cart_items WHERE user_id=? AND product_id=?",
        (session['user_id'], pid)
    ).fetchone()

    if existing:
        new_qty = existing['quantity'] + qty
        if new_qty > product['stock']:
            flash(f"لا يمكن إضافة أكثر من {product['stock']} قطعة", 'warning')
        else:
            db.execute(
                "UPDATE cart_items SET quantity=? WHERE id=?",
                (new_qty, existing['id'])
            )
            flash(f"تم تحديث الكمية في السلة ✅", 'success')
    else:
        db.execute(
            "INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?,?,?)",
            (session['user_id'], pid, qty)
        )
        flash(f"تمت إضافة \"{product['name']}\" للسلة 🛒", 'success')

    db.commit()
    db.close()
    return redirect(url_for('cart'))


@app.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def cart_update(item_id):
    """تحديث كمية منتج في السلة"""
    qty = int(request.form.get('quantity', 1))
    db = get_db()
    item = db.execute(
        "SELECT ci.*, p.stock FROM cart_items ci JOIN products p ON p.id=ci.product_id "
        "WHERE ci.id=? AND ci.user_id=?", (item_id, session['user_id'])
    ).fetchone()

    if item:
        if qty <= 0:
            db.execute("DELETE FROM cart_items WHERE id=?", (item_id,))
            flash('تم حذف المنتج من السلة', 'info')
        elif qty > item['stock']:
            flash(f"الكمية المتاحة: {item['stock']}", 'warning')
        else:
            db.execute("UPDATE cart_items SET quantity=? WHERE id=?", (qty, item_id))
        db.commit()
    db.close()
    return redirect(url_for('cart'))


@app.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def cart_remove(item_id):
    """حذف منتج من السلة"""
    db = get_db()
    db.execute(
        "DELETE FROM cart_items WHERE id=? AND user_id=?",
        (item_id, session['user_id'])
    )
    db.commit()
    db.close()
    flash('تم حذف المنتج من السلة', 'info')
    return redirect(url_for('cart'))


# ============================================================
#  الطلبات (Orders)
# ============================================================

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """صفحة إتمام الطلب"""
    db = get_db()
    items = db.execute("""
        SELECT ci.*, p.name, p.price, p.stock, p.brand,
               (ci.quantity * p.price) as subtotal
        FROM cart_items ci JOIN products p ON p.id=ci.product_id
        WHERE ci.user_id=?
    """, (session['user_id'],)).fetchall()

    if not items:
        flash('السلة فارغة!', 'warning')
        db.close()
        return redirect(url_for('products'))

    subtotal = sum(i['subtotal'] for i in items)
    shipping = 0 if subtotal >= 500 else 50
    total = subtotal + shipping

    user = get_current_user()

    if request.method == 'POST':
        name = request.form.get('shipping_name', '').strip()
        phone = request.form.get('shipping_phone', '').strip()
        address = request.form.get('shipping_address', '').strip()
        city = request.form.get('shipping_city', '').strip()
        notes = request.form.get('notes', '').strip()

        if not all([name, phone, address, city]):
            flash('يرجى تعبئة جميع حقول الشحن', 'danger')
            db.close()
            return render_template('checkout.html', items=items,
                                   subtotal=subtotal, shipping=shipping,
                                   total=total, user=user)

        # التحقق من المخزون
        for item in items:
            if item['stock'] < item['quantity']:
                flash(f"المخزون غير كافٍ: {item['name']}", 'danger')
                db.close()
                return redirect(url_for('cart'))

        order_num = generate_order_number()
        db.execute("""
            INSERT INTO orders
            (order_number, user_id, status, shipping_name, shipping_phone,
             shipping_address, shipping_city, notes, subtotal, shipping_cost, total)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (order_num, session['user_id'], 'pending',
              name, phone, address, city, notes, subtotal, shipping, total))
        order_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        for item in items:
            db.execute("""
                INSERT INTO order_items
                (order_id, product_id, quantity, price, product_name)
                VALUES (?,?,?,?,?)
            """, (order_id, item['product_id'], item['quantity'],
                  item['price'], item['name']))
            db.execute(
                "UPDATE products SET stock=stock-?, sales_count=sales_count+? WHERE id=?",
                (item['quantity'], item['quantity'], item['product_id'])
            )

        db.execute("DELETE FROM cart_items WHERE user_id=?", (session['user_id'],))
        db.commit()
        db.close()

        flash(f"تم تقديم طلبك بنجاح! رقم الطلب: {order_num} 🎉", 'success')
        return redirect(url_for('order_detail', oid=order_id))

    db.close()
    return render_template('checkout.html', items=items,
                           subtotal=subtotal, shipping=shipping,
                           total=total, user=user)


@app.route('/my-orders')
@login_required
def my_orders():
    """طلبات المستخدم"""
    db = get_db()
    orders = db.execute(
        "SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC",
        (session['user_id'],)
    ).fetchall()
    db.close()
    return render_template('my_orders.html', orders=orders)


@app.route('/order/<int:oid>')
@login_required
def order_detail(oid):
    """تفاصيل طلب"""
    db = get_db()
    order = db.execute(
        "SELECT * FROM orders WHERE id=? AND user_id=?",
        (oid, session['user_id'])
    ).fetchone()
    if not order:
        flash('الطلب غير موجود', 'danger')
        db.close()
        return redirect(url_for('my_orders'))

    items = db.execute(
        "SELECT * FROM order_items WHERE order_id=?", (oid,)
    ).fetchall()
    db.close()
    return render_template('order_detail.html', order=order, items=items)


# ============================================================
#  لوحة التحكم (Admin)
# ============================================================

@app.route('/admin')
@admin_required
def admin_dashboard():
    """لوحة التحكم الرئيسية"""
    db = get_db()

    total_users = db.execute("SELECT COUNT(*) FROM users WHERE is_admin=0").fetchone()[0]
    total_orders = db.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    total_products = db.execute("SELECT COUNT(*) FROM products WHERE is_active=1").fetchone()[0]
    total_revenue = db.execute(
        "SELECT COALESCE(SUM(total),0) FROM orders WHERE status!='cancelled'"
    ).fetchone()[0]
    pending_count = db.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0]

    top_products = db.execute(
        "SELECT * FROM products WHERE is_active=1 ORDER BY sales_count DESC LIMIT 5"
    ).fetchall()

    recent_orders = db.execute("""
        SELECT o.*, u.name as user_name, u.email as user_email
        FROM orders o JOIN users u ON u.id=o.user_id
        ORDER BY o.created_at DESC LIMIT 8
    """).fetchall()

    recent_users = db.execute(
        "SELECT * FROM users WHERE is_admin=0 ORDER BY created_at DESC LIMIT 5"
    ).fetchall()

    low_stock = db.execute(
        "SELECT * FROM products WHERE stock <= 5 AND is_active=1 ORDER BY stock ASC"
    ).fetchall()

    orders_by_status = db.execute(
        "SELECT status, COUNT(*) as cnt FROM orders GROUP BY status"
    ).fetchall()

    # إيرادات آخر 7 أيام
    revenue_7days = db.execute("""
        SELECT DATE(created_at) as day, SUM(total) as revenue
        FROM orders WHERE status!='cancelled'
        AND created_at >= DATE('now', '-7 days')
        GROUP BY DATE(created_at) ORDER BY day
    """).fetchall()

    db.close()
    return render_template('admin/dashboard.html',
                           total_users=total_users, total_orders=total_orders,
                           total_products=total_products, total_revenue=total_revenue,
                           pending_count=pending_count, top_products=top_products,
                           recent_orders=recent_orders, recent_users=recent_users,
                           low_stock=low_stock, orders_by_status=orders_by_status,
                           revenue_7days=revenue_7days)


# ===== إدارة الفئات =====

@app.route('/admin/categories')
@admin_required
def admin_categories():
    categories = get_categories(active_only=False)
    return render_template('admin/categories.html', categories=categories)


@app.route('/admin/categories/add', methods=['GET', 'POST'])
@admin_required
def admin_add_category():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        slug = make_category_slug(request.form.get('slug', '').strip() or name)
        icon = request.form.get('icon', '📦').strip() or '📦'
        description = request.form.get('description', '').strip()
        image_url = request.form.get('image_url', '').strip()
        sort_order = request.form.get('sort_order', 0, type=int)
        is_active = 1 if request.form.get('is_active') else 0

        if len(name) < 2:
            flash('اسم الفئة مطلوب', 'danger')
            return render_template('admin/category_form.html', category=None)

        db = get_db()
        if db.execute("SELECT id FROM categories WHERE slug=?", (slug,)).fetchone():
            db.close()
            flash('هذا المعرّف (slug) مستخدم مسبقاً', 'danger')
            return render_template('admin/category_form.html', category=None)

        db.execute("""
            INSERT INTO categories (name, slug, icon, description, image_url, sort_order, is_active, is_system)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        """, (name, slug, icon, description, image_url, sort_order, is_active))
        db.commit()
        db.close()
        flash(f'تمت إضافة الفئة "{name}"', 'success')
        return redirect(url_for('admin_categories'))

    return render_template('admin/category_form.html', category=None)


@app.route('/admin/categories/edit/<int:cid>', methods=['GET', 'POST'])
@admin_required
def admin_edit_category(cid):
    db = get_db()
    category = db.execute("SELECT * FROM categories WHERE id=?", (cid,)).fetchone()
    if not category:
        db.close()
        flash('الفئة غير موجودة', 'danger')
        return redirect(url_for('admin_categories'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        icon = request.form.get('icon', '📦').strip() or '📦'
        description = request.form.get('description', '').strip()
        image_url = request.form.get('image_url', '').strip()
        sort_order = request.form.get('sort_order', 0, type=int)
        is_active = 1 if request.form.get('is_active') else 0

        if len(name) < 2:
            flash('اسم الفئة مطلوب', 'danger')
            db.close()
            return render_template('admin/category_form.html', category=category)

        slug = category['slug']
        if not category['is_system']:
            slug = make_category_slug(request.form.get('slug', '').strip() or name)
            other = db.execute(
                "SELECT id FROM categories WHERE slug=? AND id!=?", (slug, cid)
            ).fetchone()
            if other:
                db.close()
                flash('هذا المعرّف (slug) مستخدم مسبقاً', 'danger')
                return render_template('admin/category_form.html', category=category)

        db.execute("""
            UPDATE categories
            SET name=?, slug=?, icon=?, description=?, image_url=?, sort_order=?, is_active=?
            WHERE id=?
        """, (name, slug, icon, description, image_url, sort_order, is_active, cid))
        db.commit()
        db.close()
        flash('تم حفظ الفئة', 'success')
        return redirect(url_for('admin_categories'))

    db.close()
    return render_template('admin/category_form.html', category=category)


@app.route('/admin/categories/delete/<int:cid>', methods=['POST'])
@admin_required
def admin_delete_category(cid):
    db = get_db()
    category = db.execute("SELECT * FROM categories WHERE id=?", (cid,)).fetchone()
    if not category:
        db.close()
        flash('الفئة غير موجودة', 'danger')
        return redirect(url_for('admin_categories'))

    if category['is_system']:
        db.close()
        flash('لا يمكن حذف فئة النظام الأساسية — يمكنك إخفاؤها فقط', 'warning')
        return redirect(url_for('admin_categories'))

    count = db.execute(
        "SELECT COUNT(*) FROM products WHERE category_id=?", (cid,)
    ).fetchone()[0]
    if count > 0:
        db.close()
        flash(f'لا يمكن الحذف: {count} منتج مرتبط بهذه الفئة', 'danger')
        return redirect(url_for('admin_categories'))

    db.execute("DELETE FROM categories WHERE id=?", (cid,))
    db.commit()
    db.close()
    flash('تم حذف الفئة', 'success')
    return redirect(url_for('admin_categories'))


# ===== إدارة المنتجات =====

@app.route('/admin/products')
@admin_required
def admin_products():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '')
    per_page = 15
    db = get_db()
    where = "WHERE 1=1"
    params = []
    if q:
        where += " AND (p.name LIKE ? OR p.brand LIKE ?)"
        params.extend([f'%{q}%', f'%{q}%'])

    total = db.execute(f"SELECT COUNT(*) FROM products p {where}", params).fetchone()[0]
    offset = (page - 1) * per_page
    items = db.execute(
        f"SELECT p.*, c.name as cat_name FROM products p "
        f"LEFT JOIN categories c ON c.id=p.category_id "
        f"{where} ORDER BY p.created_at DESC LIMIT ? OFFSET ?",
        params + [per_page, offset]
    ).fetchall()
    categories = get_categories(active_only=False)
    db.close()
    total_pages = (total + per_page - 1) // per_page
    return render_template('admin/products.html', items=items, categories=categories,
                           q=q, page=page, total_pages=total_pages, total=total)


@app.route('/admin/products/add', methods=['GET', 'POST'])
@admin_required
def admin_add_product():
    db = get_db()
    categories = get_categories(active_only=False)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', type=float)
        old_price_str = request.form.get('old_price', '').strip()
        old_price = float(old_price_str) if old_price_str else None
        stock = request.form.get('stock', 0, type=int)
        brand = request.form.get('brand', '').strip()
        category_id = request.form.get('category_id', type=int)
        is_featured = 1 if request.form.get('is_featured') else 0

        if not name or not price:
            flash('الاسم والسعر مطلوبان', 'danger')
            db.close()
            return render_template('admin/product_form.html', categories=categories, product=None)

        db.execute("""
            INSERT INTO products (name, description, price, old_price, stock, brand, category_id, is_featured)
            VALUES (?,?,?,?,?,?,?,?)
        """, (name, description, price, old_price, stock, brand, category_id, is_featured))
        db.commit()
        db.close()
        flash(f'تمت إضافة المنتج "{name}" ✅', 'success')
        return redirect(url_for('admin_products'))

    db.close()
    return render_template('admin/product_form.html', categories=categories, product=None)


@app.route('/admin/products/edit/<int:pid>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(pid):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    categories = get_categories(active_only=False)

    if not product:
        db.close()
        flash('المنتج غير موجود', 'danger')
        return redirect(url_for('admin_products'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', type=float)
        old_price_str = request.form.get('old_price', '').strip()
        old_price = float(old_price_str) if old_price_str else None
        stock = request.form.get('stock', 0, type=int)
        brand = request.form.get('brand', '').strip()
        category_id = request.form.get('category_id', type=int)
        is_featured = 1 if request.form.get('is_featured') else 0
        is_active = 1 if request.form.get('is_active') else 0

        db.execute("""
            UPDATE products SET name=?, description=?, price=?, old_price=?,
            stock=?, brand=?, category_id=?, is_featured=?, is_active=?,
            updated_at=CURRENT_TIMESTAMP WHERE id=?
        """, (name, description, price, old_price, stock, brand,
              category_id, is_featured, is_active, pid))
        db.commit()
        db.close()
        flash(f'تم تحديث المنتج ✅', 'success')
        return redirect(url_for('admin_products'))

    db.close()
    return render_template('admin/product_form.html', categories=categories, product=product)


@app.route('/admin/products/delete/<int:pid>', methods=['POST'])
@admin_required
def admin_delete_product(pid):
    db = get_db()
    db.execute("UPDATE products SET is_active=0 WHERE id=?", (pid,))
    db.commit()
    db.close()
    flash('تم حذف المنتج', 'info')
    return redirect(url_for('admin_products'))


# ===== إدارة الطلبات =====

@app.route('/admin/orders')
@admin_required
def admin_orders():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    per_page = 15
    db = get_db()

    where = "WHERE 1=1"
    params = []
    if status_filter:
        where += " AND o.status=?"
        params.append(status_filter)

    total = db.execute(f"SELECT COUNT(*) FROM orders o {where}", params).fetchone()[0]
    offset = (page - 1) * per_page
    orders = db.execute(
        f"SELECT o.*, u.name as user_name FROM orders o "
        f"JOIN users u ON u.id=o.user_id "
        f"{where} ORDER BY o.created_at DESC LIMIT ? OFFSET ?",
        params + [per_page, offset]
    ).fetchall()
    db.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template('admin/orders.html', orders=orders,
                           status_filter=status_filter,
                           page=page, total_pages=total_pages)


@app.route('/admin/orders/<int:oid>')
@admin_required
def admin_order_detail(oid):
    db = get_db()
    order = db.execute(
        "SELECT o.*, u.name as user_name, u.email as user_email, u.phone as user_phone "
        "FROM orders o JOIN users u ON u.id=o.user_id WHERE o.id=?", (oid,)
    ).fetchone()
    items = db.execute(
        "SELECT oi.*, p.brand FROM order_items oi "
        "LEFT JOIN products p ON p.id=oi.product_id WHERE oi.order_id=?", (oid,)
    ).fetchall()
    db.close()
    return render_template('admin/order_detail.html', order=order, items=items)


@app.route('/admin/orders/<int:oid>/status', methods=['POST'])
@admin_required
def admin_update_order_status(oid):
    new_status = request.form.get('status')
    admin_notes = request.form.get('admin_notes', '').strip()
    valid = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled']

    if new_status in valid:
        db = get_db()
        db.execute(
            "UPDATE orders SET status=?, admin_notes=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (new_status, admin_notes, oid)
        )
        db.commit()
        db.close()
        flash('تم تحديث حالة الطلب ✅', 'success')

    return redirect(url_for('admin_order_detail', oid=oid))


# ===== إدارة العملاء (CRM) =====

@app.route('/admin/customers')
@admin_required
def admin_customers():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '')
    per_page = 20
    db = get_db()

    where = "WHERE is_admin=0"
    params = []
    if q:
        where += " AND (name LIKE ? OR email LIKE ?)"
        params.extend([f'%{q}%', f'%{q}%'])

    total = db.execute(f"SELECT COUNT(*) FROM users {where}", params).fetchone()[0]
    offset = (page - 1) * per_page
    customers = db.execute(
        f"SELECT u.*, "
        f"(SELECT COUNT(*) FROM orders o WHERE o.user_id=u.id) as orders_count, "
        f"(SELECT COALESCE(SUM(o2.total),0) FROM orders o2 WHERE o2.user_id=u.id AND o2.status!='cancelled') as total_spent "
        f"FROM users u {where} ORDER BY u.created_at DESC LIMIT ? OFFSET ?",
        params + [per_page, offset]
    ).fetchall()
    db.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template('admin/customers.html', customers=customers,
                           q=q, page=page, total_pages=total_pages, total=total)


@app.route('/admin/customers/<int:uid>')
@admin_required
def admin_customer_detail(uid):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    orders = db.execute(
        "SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC", (uid,)
    ).fetchall()
    purchased = db.execute("""
        SELECT oi.product_name, oi.price, SUM(oi.quantity) as total_qty,
               SUM(oi.quantity * oi.price) as total_amount
        FROM order_items oi
        JOIN orders o ON o.id=oi.order_id
        WHERE o.user_id=? AND o.status!='cancelled'
        GROUP BY oi.product_name ORDER BY total_qty DESC
    """, (uid,)).fetchall()
    db.close()
    return render_template('admin/customer_detail.html',
                           user=user, orders=orders, purchased=purchased)


@app.route('/admin/customers/<int:uid>/toggle', methods=['POST'])
@admin_required
def admin_toggle_customer(uid):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    new_status = 0 if user['is_active'] else 1
    db.execute("UPDATE users SET is_active=? WHERE id=?", (new_status, uid))
    db.commit()
    db.close()
    status_text = 'مفعّل' if new_status else 'محظور'
    flash(f"تم تغيير حالة الحساب إلى: {status_text}", 'info')
    return redirect(url_for('admin_customers'))


# ============================================================
#  معالجة الأخطاء
# ============================================================

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404,
                           message='الصفحة غير موجودة'), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403,
                           message='ليس لديك صلاحية الوصول'), 403


@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', code=500,
                           message='خطأ في الخادم، يرجى المحاولة لاحقاً'), 500


# ============================================================
#  تشغيل التطبيق
# ============================================================

@app.template_global()
def enumerate(iterable, start=0):
    """تعريف enumerate لـ Jinja"""
    return __builtins__['enumerate'](iterable, start) if isinstance(__builtins__, dict) else __import__('builtins').enumerate(iterable, start)

# ديكوريتور إضافي للـ context_processor لإضافة pending_orders_count
@app.context_processor
def inject_pending():
    count = 0
    if session.get('is_admin'):
        try:
            db = get_db()
            count = db.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0]
            db.close()
        except Exception:
            pass
    return {'pending_orders_count': count}


if __name__ == '__main__':
    # إنشاء قاعدة البيانات عند أول تشغيل
    init_db()
    local_ip = "127.0.0.1"
    try:
        # الحصول على عنوان الشبكة المحلية الفعلي للجهاز
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
    except Exception:
        pass

    local_site_url = "http://127.0.0.1:5000"
    phone_site_url = f"http://{local_ip}:5000"
    print("\n" + "="*55)
    print(f"  🚀  VELTRIX CRM (هذا الجهاز): {local_site_url}")
    print(f"  📱  رابط الهاتف (نفس الواي فاي): {phone_site_url}")
    print("  👤  المسؤول : abdallah2k@gmail.com")
    print("  🔑  كلمة المرور: abdallah2k")
    print(f"  📦  لوحة التحكم: {phone_site_url}/admin")
    print("="*55 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)

# ============================================================
#  تقارير المبيعات
# ============================================================

@app.route('/admin/reports')
@admin_required
def admin_reports():
    db = get_db()

    # إجمالي الإيرادات
    total_revenue = db.execute(
        "SELECT COALESCE(SUM(total),0) FROM orders WHERE status!='cancelled'"
    ).fetchone()[0]

    # إيرادات آخر 30 يوم يومياً
    revenue_30days = db.execute("""
        SELECT DATE(created_at) as day, SUM(total) as revenue, COUNT(*) as cnt
        FROM orders WHERE status!='cancelled'
        AND created_at >= DATE('now', '-30 days')
        GROUP BY DATE(created_at) ORDER BY day
    """).fetchall()

    # أفضل المنتجات مبيعاً
    top_products = db.execute("""
        SELECT p.name, p.price, p.sales_count,
               COALESCE(SUM(oi.quantity * oi.price), 0) as revenue
        FROM products p
        LEFT JOIN order_items oi ON oi.product_id = p.id
        LEFT JOIN orders o ON o.id = oi.order_id AND o.status != 'cancelled'
        WHERE p.is_active=1
        GROUP BY p.id ORDER BY p.sales_count DESC LIMIT 10
    """).fetchall()

    # توزيع الأوردرات بالحالة
    orders_by_status = db.execute(
        "SELECT status, COUNT(*) as cnt FROM orders GROUP BY status"
    ).fetchall()

    # إيرادات كل شهر آخر 6 شهور
    revenue_monthly = db.execute("""
        SELECT strftime('%Y-%m', created_at) as month,
               SUM(total) as revenue, COUNT(*) as cnt
        FROM orders WHERE status!='cancelled'
        AND created_at >= DATE('now', '-6 months')
        GROUP BY month ORDER BY month
    """).fetchall()

    # أكثر العملاء شراءً
    top_customers = db.execute("""
        SELECT u.name, u.email, COUNT(o.id) as orders_count,
               COALESCE(SUM(o.total),0) as total_spent
        FROM users u
        JOIN orders o ON o.user_id = u.id AND o.status != 'cancelled'
        GROUP BY u.id ORDER BY total_spent DESC LIMIT 5
    """).fetchall()

    db.close()
    return render_template('admin/reports.html',
                           total_revenue=total_revenue,
                           revenue_30days=revenue_30days,
                           top_products=top_products,
                           orders_by_status=orders_by_status,
                           revenue_monthly=revenue_monthly,
                           top_customers=top_customers)


# ============================================================
#  نظام التقييمات
# ============================================================

@app.route('/product/<int:pid>/review', methods=['POST'])
@login_required
def add_review(pid):
    rating = int(request.form.get('rating', 0))
    comment = request.form.get('comment', '').strip()
    lang = _current_lang()
    if rating < 1 or rating > 5:
        flash('تقييم غير صحيح', 'danger')
        return redirect(url_for('product_detail', pid=pid))
    db = get_db()
    # تأكد إن المنتج موجود
    product = db.execute("SELECT id FROM products WHERE id=?", (pid,)).fetchone()
    if not product:
        db.close()
        flash('المنتج غير موجود', 'danger')
        return redirect(url_for('products'))
    # منع التقييم المكرر
    existing = db.execute(
        "SELECT id FROM reviews WHERE product_id=? AND user_id=?",
        (pid, session['user_id'])
    ).fetchone()
    if existing:
        flash('قمت بتقييم هذا المنتج من قبل', 'warning')
        db.close()
        return redirect(url_for('product_detail', pid=pid))
    db.execute(
        "INSERT INTO reviews (product_id, user_id, rating, comment) VALUES (?,?,?,?)",
        (pid, session['user_id'], rating, comment)
    )
    db.commit()
    db.close()
    flash('شكراً! تم إضافة تقييمك', 'success')
    return redirect(url_for('product_detail', pid=pid))


@app.route('/admin/reviews')
@admin_required
def admin_reviews():
    db = get_db()
    reviews = db.execute("""
        SELECT r.*, u.name as user_name, p.name as product_name
        FROM reviews r
        JOIN users u ON u.id = r.user_id
        JOIN products p ON p.id = r.product_id
        ORDER BY r.created_at DESC
    """).fetchall()
    db.close()
    return render_template('admin/reviews.html', reviews=reviews)


@app.route('/admin/reviews/<int:rid>/delete', methods=['POST'])
@admin_required
def delete_review(rid):
    db = get_db()
    db.execute("DELETE FROM reviews WHERE id=?", (rid,))
    db.commit()
    db.close()
    flash('تم حذف التقييم', 'success')
    return redirect(url_for('admin_reviews'))

