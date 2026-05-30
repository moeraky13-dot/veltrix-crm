"""
قاعدة البيانات - SQLite مباشر
إدارة الاتصال وإنشاء الجداول والبذر الأولي
"""
import sqlite3
import os
import hashlib
import secrets
import sys

# تجنب مشاكل ترميز الطرفية على ويندوز عند تشغيل init_db
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import shutil

# On Vercel, the filesystem is read-only except /tmp
_BUNDLED_DB = os.path.join(os.path.dirname(__file__), 'veltrix.db')
_TMP_DB = '/tmp/veltrix.db'

def _ensure_db_writable():
    """Copy the bundled DB to /tmp if not already there."""
    if not os.path.exists(_TMP_DB) and os.path.exists(_BUNDLED_DB):
        shutil.copy2(_BUNDLED_DB, _TMP_DB)

_ensure_db_writable()
DB_PATH = _TMP_DB if os.path.exists('/tmp') else _BUNDLED_DB

# الفئات الأساسية للمتجر (تُنشأ تلقائياً ويمكن تعديلها من لوحة التحكم)
STORE_CATEGORY_DEFAULTS = [
    {
        'name': 'هواتف ذكية',
        'slug': 'smartphones',
        'icon': '📱',
        'sort_order': 1,
        'image_url': 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=500&q=80',
    },
    {
        'name': 'لابتوب وحاسوب',
        'slug': 'laptops',
        'icon': '💻',
        'sort_order': 2,
        'image_url': 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=500&q=80',
    },
    {
        'name': 'سماعات',
        'slug': 'headphones',
        'icon': '🎧',
        'sort_order': 3,
        'image_url': 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=500&q=80',
    },
    {
        'name': 'كاميرات',
        'slug': 'cameras',
        'icon': '📷',
        'sort_order': 4,
        'image_url': 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=500&q=80',
    },
    {
        'name': 'إكسسوارات',
        'slug': 'accessories',
        'icon': '⌨️',
        'sort_order': 5,
        'image_url': 'https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=500&q=80',
    },
    {
        'name': 'ساعات ذكية',
        'slug': 'smartwatches',
        'icon': '⌚',
        'sort_order': 6,
        'image_url': 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=500&q=80',
    },
]


def get_db():
    """الحصول على اتصال بقاعدة البيانات"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # النتائج كـ dict
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str) -> str:
    """تشفير كلمة المرور"""
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 200000)
    return f"{salt}${hashed.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """التحقق من كلمة المرور"""
    try:
        salt, hashed = stored.split('$', 1)
        check = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 200000)
        return check.hex() == hashed
    except Exception:
        return False


def init_db():
    """إنشاء الجداول وإضافة البيانات الأولية"""
    conn = get_db()
    c = conn.cursor()

    # ===== جدول المستخدمين =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            phone TEXT DEFAULT '',
            address TEXT DEFAULT '',
            is_admin INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login DATETIME
        )
    """)

    # ===== جدول الفئات =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            icon TEXT DEFAULT '📦',
            description TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ===== جدول المنتجات =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            price REAL NOT NULL,
            old_price REAL,
            stock INTEGER DEFAULT 0,
            image TEXT DEFAULT 'default.jpg',
            brand TEXT DEFAULT '',
            category_id INTEGER,
            is_featured INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            sales_count INTEGER DEFAULT 0,
            views_count INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    """)

    # ===== جدول السلة =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS cart_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # ===== جدول الطلبات =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            shipping_name TEXT,
            shipping_phone TEXT,
            shipping_address TEXT,
            shipping_city TEXT,
            subtotal REAL DEFAULT 0,
            shipping_cost REAL DEFAULT 0,
            total REAL DEFAULT 0,
            notes TEXT DEFAULT '',
            admin_notes TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # ===== جدول عناصر الطلبات =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            product_name TEXT NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # ===== جدول التقييمات =====
    c.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            comment TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(product_id, user_id)
        )
    """)

    _migrate_categories_schema(c)
    sync_store_categories(c)
    conn.commit()

    # ===== بيانات أولية =====
    _seed_data(conn)
    update_missing_product_images(conn)
    update_known_product_images(conn)
    conn.commit()
    conn.close()
    print("قاعدة البيانات جاهزة!")


def _migrate_categories_schema(c):
    """ترقية جدول الفئات لنظام إدارة كامل."""
    cols = {row[1] for row in c.execute("PRAGMA table_info(categories)").fetchall()}
    if 'sort_order' not in cols:
        c.execute("ALTER TABLE categories ADD COLUMN sort_order INTEGER DEFAULT 0")
    if 'image_url' not in cols:
        c.execute("ALTER TABLE categories ADD COLUMN image_url TEXT DEFAULT ''")
    if 'is_active' not in cols:
        c.execute("ALTER TABLE categories ADD COLUMN is_active INTEGER DEFAULT 1")
    if 'is_system' not in cols:
        c.execute("ALTER TABLE categories ADD COLUMN is_system INTEGER DEFAULT 0")


def sync_store_categories(c):
    """ضمان وجود الفئات الست الأساسية — لا يمسح تعديلات المسؤول."""
    for cat in STORE_CATEGORY_DEFAULTS:
        row = c.execute(
            "SELECT id, sort_order, image_url FROM categories WHERE slug=?", (cat['slug'],)
        ).fetchone()
        if row:
            sort_order = row['sort_order'] if row['sort_order'] else cat['sort_order']
            image_url = row['image_url'] if row['image_url'] else cat['image_url']
            c.execute("""
                UPDATE categories
                SET sort_order=?, image_url=?, is_system=1
                WHERE slug=?
            """, (sort_order, image_url, cat['slug']))
        else:
            c.execute("""
                INSERT INTO categories (name, slug, icon, description, sort_order, image_url, is_active, is_system)
                VALUES (?, ?, ?, '', ?, ?, 1, 1)
            """, (cat['name'], cat['slug'], cat['icon'], cat['sort_order'], cat['image_url']))


# منتجات إضافية بأسعار معقولة (جنيه مصري) — تُضاف تلقائياً إن لم تكن موجودة
EXTRA_CATALOG_PRODUCTS = [
    # هواتف — فئة اقتصادية ومتوسطة
    ('Xiaomi Redmi Note 13', 'هاتف ذكي بشاشة AMOLED 6.67" وكاميرا 108MP وبطارية 5000mAh وشحن سريع 33W.', 6499, 7499, 40,
     'https://images.unsplash.com/photo-1598327275668-89b51a6837c9?auto=format&fit=crop&w=900&q=80', 'Xiaomi', 'smartphones', 1, 88),
    ('Samsung Galaxy A25', 'هاتف سامسونج بشاشة Super AMOLED وكاميرا ثلاثية وبطارية طويلة — خيار ممتاز بسعر مناسب.', 7999, 8999, 35,
     'https://images.unsplash.com/photo-1610945265064-75e5a7a2d701?auto=format&fit=crop&w=900&q=80', 'Samsung', 'smartphones', 1, 76),
    ('OPPO A78', 'هاتف OPPO بشاشة 90Hz وكاميرا 50MP وشحن سريع VOOC 67W — أداء يومي ممتاز.', 5999, None, 45,
     'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=900&q=80', 'OPPO', 'smartphones', 0, 54),
    ('Realme C55', 'هاتف اقتصادي بشاشة 90Hz وكاميرا 64MP وبطارية 5000mAh — أفضل قيمة مقابل السعر.', 4499, 5299, 60,
     'https://images.unsplash.com/photo-1565849901021-7fe2a3f7c0c5?auto=format&fit=crop&w=900&q=80', 'Realme', 'smartphones', 1, 112),
    ('Honor X9b', 'هاتف بشاشة Curved AMOLED مقاومة للكسر وكاميرا 108MP وبطارية 5800mAh.', 8999, 9999, 28,
     'https://images.unsplash.com/photo-1580910051074-3eb6948862fb?auto=format&fit=crop&w=900&q=80', 'Honor', 'smartphones', 0, 41),
    ('Google Pixel 8a', 'هاتف جوجل بكاميرا AI ممتازة وتحديثات أندرويد لـ 7 سنوات.', 14999, 16999, 15,
     'https://images.unsplash.com/photo-1592899677977-9c10ca588bbd?auto=format&fit=crop&w=900&q=80', 'Google', 'smartphones', 0, 29),
    ('Infinix Hot 40', 'هاتف اقتصادي بشاشة 120Hz ومعالج Helio G88 — مثالي للاستخدام اليومي.', 3999, 4599, 55,
     'https://images.unsplash.com/photo-1556656793-08538906a9f8?auto=format&fit=crop&w=900&q=80', 'Infinix', 'smartphones', 0, 67),
    # لابتوب
    ('Lenovo IdeaPad 3', 'لابتوب يومي بمعالج Ryzen 5 وذاكرة 8GB وSSD 512GB — مناسب للدراسة والعمل.', 18999, 20999, 20,
     'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=900&q=80', 'Lenovo', 'laptops', 1, 45),
    ('HP Pavilion 15', 'لابتوب HP بشاشة 15.6" FHD ومعالج Core i5 وكرت Intel Iris — أداء متوازن.', 22999, None, 14,
     'https://images.unsplash.com/photo-1588872657577-747ed45b8d37?auto=format&fit=crop&w=900&q=80', 'HP', 'laptops', 0, 38),
    ('ASUS VivoBook 15', 'لابتوب خفيف بشاشة OLED اختيارية ومعالج Ryzen 7 — تصميم أنيق وخفيف.', 17499, 19499, 16,
     'https://images.unsplash.com/photo-1587613865766-3f3c3f4c4b4e?auto=format&fit=crop&w=900&q=80', 'ASUS', 'laptops', 1, 52),
    ('Acer Aspire 5', 'لابتوب Acer بمعالج Core i5 وذاكرة 16GB وSSD 512GB — قيمة ممتازة للسعر.', 19999, None, 18,
     'https://images.unsplash.com/photo-1525547719328-7b8e8a4e2530?auto=format&fit=crop&w=900&q=80', 'Acer', 'laptops', 0, 33),
    ('MSI Modern 14', 'لابتوب رفيع للمحترفين بمعالج Core i7 وشاشة 14" FHD ووزن خفيف.', 24999, 26999, 10,
     'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=900&q=80', 'MSI', 'laptops', 0, 22),
    # سماعات
    ('JBL Tune 520BT', 'سماعة لاسلكية على الرأس بصوت JBL Pure Bass وبطارية 57 ساعة — سعر اقتصادي.', 899, 1199, 80,
     'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=900&q=80', 'JBL', 'headphones', 1, 156),
    ('Anker Soundcore Q20', 'سماعة بإلغاء ضوضاء هجين وبطارية 40 ساعة — راحة ممتازة للسفر.', 1299, 1599, 65,
     'https://images.unsplash.com/photo-1484704849700-f032a568e944?auto=format&fit=crop&w=900&q=80', 'Anker', 'headphones', 1, 98),
    ('Xiaomi Buds 4', 'سماعات أذن لاسلكية بإلغاء ضوضاء وصوت Hi-Fi وشحن سريع.', 1499, None, 70,
     'https://images.unsplash.com/photo-1590658268037-6bf21065a31b?auto=format&fit=crop&w=900&q=80', 'Xiaomi', 'headphones', 0, 87),
    ('Beats Studio Buds', 'سماعات Beats بصوت غني وإلغاء ضوضاء نشط ومقاومة للعرق.', 2499, 2999, 40,
     'https://images.unsplash.com/photo-1572569511254-d8f925fe2cbb?auto=format&fit=crop&w=900&q=80', 'Beats', 'headphones', 0, 64),
    ('Razer Barracuda X', 'سماعة ألعاب لاسلكية متعددة المنصات ببطارية 50 ساعة ومايك واضح.', 2199, None, 30,
     'https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?auto=format&fit=crop&w=900&q=80', 'Razer', 'headphones', 0, 41),
    # كاميرات
    ('GoPro HERO12', 'كاميرا أكشن 5.3K مع تثبيت HyperSmooth 6.0 ومقاومة للماء حتى 10م.', 12999, 14999, 12,
     'https://images.unsplash.com/photo-1526170375885-4d8ecf77bcea?auto=format&fit=crop&w=900&q=80', 'GoPro', 'cameras', 1, 48),
    ('Nikon Z30', 'كاميرا مرايا بدون مرآة خفيفة للمبتدئين وفيديو 4K UHD.', 18999, None, 8,
     'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=900&q=80', 'Nikon', 'cameras', 0, 19),
    ('Insta360 X3', 'كاميرا 360° للمحتوى والسفر بتثبيت FlowState وفيديو 5.7K.', 14999, 16999, 10,
     'https://images.unsplash.com/photo-1510127034890-ba27508e9f1c?auto=format&fit=crop&w=900&q=80', 'Insta360', 'cameras', 0, 27),
    ('DJI Osmo Pocket 3', 'كاميرا جيبية بمحور ثلاثي وتصوير 4K/120fps — مثالية للفلوجرز.', 11999, None, 9,
     'https://images.unsplash.com/photo-1495121553079-367614a1574e?auto=format&fit=crop&w=900&q=80', 'DJI', 'cameras', 1, 35),
    # إكسسوارات
    ('Anker PowerCore 20000', 'باور بانك 20000mAh بشحن سريع Power Delivery للهاتف واللابتوب.', 599, 799, 100,
     'https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?auto=format&fit=crop&w=900&q=80', 'Anker', 'accessories', 1, 203),
    ('Samsung شاحن 25W', 'شاحن سريع أصلي USB-C بقوة 25W متوافق مع سامسونج وآيفون.', 349, 449, 120,
     'https://images.unsplash.com/photo-1583863788434-e58a36330e0c?auto=format&fit=crop&w=900&q=80', 'Samsung', 'accessories', 0, 178),
    ('USB-C Hub 7-in-1', 'محول USB-C بـ HDMI وUSB 3.0 وقارئ SD — مناسب للابتوب الحديث.', 499, None, 85,
     'https://images.unsplash.com/photo-1625729142350-b135d7d6b833?auto=format&fit=crop&w=900&q=80', 'Baseus', 'accessories', 1, 134),
    ('Logitech K380', 'كيبورد بلوتوث خفيف متعدد الأجهزة — Mac/Windows/تابلت.', 899, 1099, 55,
     'https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=900&q=80', 'Logitech', 'accessories', 0, 91),
    ('Razer DeathAdder Essential', 'ماوس ألعاب بدقة 6400 DPI وتصميم مريح لليد اليمنى.', 649, 799, 75,
     'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=900&q=80', 'Razer', 'accessories', 0, 112),
    ('SanDisk Ultra 128GB', 'فلاشة USB 3.0 سعة 128GB بسرعة نقل عالية.', 299, 379, 150,
     'https://images.unsplash.com/photo-1625948515291-696cec0e32d2?auto=format&fit=crop&w=900&q=80', 'SanDisk', 'accessories', 0, 245),
    ('غطاء سيليكون iPhone', 'غطاء حماية ناعم بألوان متعددة متوافق iPhone 14/15.', 199, None, 200,
     'https://images.unsplash.com/photo-1601784551446-20c9e07cdbdb?auto=format&fit=crop&w=900&q=80', 'Generic', 'accessories', 0, 167),
    ('حامل لابتوب ألومنيوم', 'ستاند لابتوب قابل للتعديل بتهوية أفضل ووضعيات متعددة.', 449, 549, 60,
     'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=900&q=80', 'UGREEN', 'accessories', 0, 58),
    # ساعات ذكية
    ('Xiaomi Watch 2', 'ساعة ذكية بنظام Wear OS وGPS ومتابعة صحية شاملة.', 3499, 3999, 35,
     'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=900&q=80', 'Xiaomi', 'smartwatches', 1, 72),
    ('Amazfit GTR 4', 'ساعة رياضية ببطارية 14 يوم وGPS دقيق ومقاومة للماء 5ATM.', 4299, None, 28,
     'https://images.unsplash.com/photo-1579586337278-3befd40fd17a?auto=format&fit=crop&w=900&q=80', 'Amazfit', 'smartwatches', 0, 49),
    ('Huawei Watch Fit 3', 'ساعة رفيعة بشاشة AMOLED مستطيلة ومتابعة نوم ورياضة.', 2799, 3199, 42,
     'https://images.unsplash.com/photo-1434494878577-86c23bcb06b9?auto=format&fit=crop&w=900&q=80', 'Huawei', 'smartwatches', 1, 61),
    ('Redmi Watch 4', 'ساعة اقتصادية بشاشة كبيرة 1.97" وGPS وبطارية 20 يوم.', 1999, 2499, 50,
     'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=900&q=80', 'Redmi', 'smartwatches', 1, 95),
]

INITIAL_PRODUCT_IMAGES = {
    'iPhone 15 Pro Max': 'https://images.unsplash.com/photo-1695048133142-1a20484d2569?auto=format&fit=crop&w=900&q=80',
    'Samsung Galaxy S24 Ultra': 'https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?auto=format&fit=crop&w=900&q=80',
    'MacBook Pro M3': 'https://images.unsplash.com/photo-1541807084-5c52b6b3adef?auto=format&fit=crop&w=900&q=80',
    'Dell XPS 15': 'https://images.unsplash.com/photo-1593642632823-8f785ba67e45?auto=format&fit=crop&w=900&q=80',
    'Sony WH-1000XM5': 'https://images.unsplash.com/photo-1546435770-a3e426bf472b?auto=format&fit=crop&w=900&q=80',
    'AirPods Pro 2': 'https://images.unsplash.com/photo-1606220588913-b3aacb4d2f37?auto=format&fit=crop&w=900&q=80',
    'Sony A7 IV': 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=900&q=80',
    'Apple Watch Series 9': 'https://images.unsplash.com/photo-1434494878577-86c23bcb06b9?auto=format&fit=crop&w=900&q=80',
    'Logitech MX Master 3S': 'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=900&q=80',
    'iPad Pro M2': 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=900&q=80',
    'Samsung Galaxy Watch 6': 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=900&q=80',
    'Canon EOS R50': 'https://images.unsplash.com/photo-1510127034890-ba27508e9f1c?auto=format&fit=crop&w=900&q=80',
}

# صور fallback حقيقية حسب فئة المنتج
CATEGORY_FALLBACK_IMAGES = {cat['slug']: cat.get('image_url', '') for cat in STORE_CATEGORY_DEFAULTS}


def update_missing_product_images(conn):
    """
    استبدال أي منتج صوره 'default.jpg' بصوره حقيقية مناسبة.
    ده يعالج مشكلة المنتجات القديمة اللي اتسجلت بدون صورة حقيقية.
    """
    c = conn.cursor()

    name_image_map = {}
    name_image_map.update(INITIAL_PRODUCT_IMAGES)
    for row in EXTRA_CATALOG_PRODUCTS:
        # row: (name, desc, price, old_price, stock, image, brand, slug, featured, sales)
        name_image_map[row[0]] = row[5]

    fallback_accessories = CATEGORY_FALLBACK_IMAGES.get('accessories', '')

    missing = c.execute("""
        SELECT p.id, p.name, c.slug
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.image IS NULL OR p.image = '' OR p.image = 'default.jpg'
    """).fetchall()

    updated = 0
    for row in missing:
        pid = row['id']
        name = row['name']
        slug = row['slug']

        image_url = name_image_map.get(name)
        if not image_url:
            image_url = CATEGORY_FALLBACK_IMAGES.get(slug) or fallback_accessories

        if image_url and image_url != 'default.jpg':
            c.execute("UPDATE products SET image=? WHERE id=?", (image_url, pid))
            updated += 1

    return updated


LOCAL_PRODUCT_IMAGES = {
    # الصور اللي انت بعتها (حقيقية) داخل static/images/
    'Realme C55': '/static/images/product_uploads/realme-c55.png',
    'Samsung Galaxy A25': '/static/images/product_uploads/samsung-galaxy-a25.png',
    'Samsung شاحن 25W': '/static/images/product_uploads/samsung-charger-25w.png',
    'AirPods Pro 2': '/static/images/product_uploads/airpods-pro-2.png',
    'SanDisk Ultra 128GB': '/static/images/product_uploads/sandisk-ultra-64gb.png',
    'USB-C Hub 7-in-1': '/static/images/product_uploads/usb-c-hub-7in1.png',
}


def update_known_product_images(conn):
    """
    استبدال الصور المعروفة بموضعها داخل static/images (حتى لو كانت غير default.jpg).
    ده علشان الصور اللي انت بعتها تبقى ظاهرة في الكروت والموبايل.
    """
    c = conn.cursor()
    changes_before = conn.total_changes
    for name, image_url in LOCAL_PRODUCT_IMAGES.items():
        c.execute("UPDATE products SET image=? WHERE name=?", (image_url, name))
    # لا نحتاج عدد دقيق - فقط للتأكيد
    _ = conn.total_changes - changes_before


def _insert_product_row(c, cat_map, row):
    """إدراج منتج واحد: (name, desc, price, old_price, stock, image, brand, slug, featured, sales)."""
    name, desc, price, old_price, stock, image, brand, slug, featured, sales = row
    cat_id = cat_map.get(slug)
    c.execute("""
        INSERT INTO products
        (name, description, price, old_price, stock, image, brand, category_id, is_featured, sales_count)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (name, desc, price, old_price, stock, image, brand, cat_id, featured, sales))


def seed_extra_catalog(conn):
    """إضافة منتجات الكتالوج الإضافي دون تكرار الأسماء."""
    c = conn.cursor()
    c.execute("SELECT id, slug FROM categories")
    cat_map = {row['slug']: row['id'] for row in c.fetchall()}
    added = 0
    for row in EXTRA_CATALOG_PRODUCTS:
        c.execute("SELECT id FROM products WHERE name = ? LIMIT 1", (row[0],))
        if c.fetchone():
            continue
        _insert_product_row(c, cat_map, row)
        added += 1
    if added:
        print(f"تمت إضافة {added} منتج جديد للكتالوج")


def _seed_data(conn):
    """إدراج البيانات الأولية"""
    c = conn.cursor()

    # حساب المسؤول
    admin_email = 'abdallah2k@gmail.com'
    admin_password = 'abdallah2k'
    c.execute("SELECT id FROM users WHERE email = ? LIMIT 1", (admin_email,))
    target_user = c.fetchone()
    c.execute("SELECT id FROM users WHERE is_admin = 1 ORDER BY id LIMIT 1")
    admin_user = c.fetchone()
    if target_user:
        c.execute("""
            UPDATE users
            SET password_hash = ?, is_admin = 1, is_active = 1
            WHERE id = ?
        """, (hash_password(admin_password), target_user['id']))
    elif admin_user:
        c.execute("""
            UPDATE users
            SET email = ?, password_hash = ?, is_active = 1
            WHERE id = ?
        """, (admin_email, hash_password(admin_password), admin_user['id']))
    else:
        c.execute("""
            INSERT INTO users (name, email, password_hash, is_admin)
            VALUES (?, ?, ?, 1)
        """, ('مدير المتجر', admin_email, hash_password(admin_password)))
    print(f"تم ضبط حساب المسؤول: {admin_email} / {admin_password}")

    # المنتجات
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        c.execute("SELECT id, slug FROM categories")
        cat_map = {row['slug']: row['id'] for row in c.fetchall()}

        products = [
            ('iPhone 15 Pro Max', 'أحدث هاتف من آبل مع شريحة A17 Pro وكاميرا 48MP وتصميم تيتانيوم يدعم USB-C وDynamic Island.', 5999.99, 6499.99, 25, 'https://images.unsplash.com/photo-1695048133142-1a20484d2569?auto=format&fit=crop&w=900&q=80', 'Apple', cat_map.get('smartphones'), 1, 145),
            ('Samsung Galaxy S24 Ultra', 'هاتف سامسونج الرائد مع قلم S Pen مدمج وكاميرا 200MP وشاشة Dynamic AMOLED 2K.', 5499.99, None, 18, 'https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?auto=format&fit=crop&w=900&q=80', 'Samsung', cat_map.get('smartphones'), 1, 132),
            ('MacBook Pro M3', 'لابتوب آبل بمعالج M3 مع شاشة Liquid Retina XDR 14 بوصة وبطارية 22 ساعة.', 8999.99, None, 12, 'https://images.unsplash.com/photo-1541807084-5c52b6b3adef?auto=format&fit=crop&w=900&q=80', 'Apple', cat_map.get('laptops'), 1, 89),
            ('Dell XPS 15', 'لابتوب Dell بمعالج Core i9 وكرت RTX 4060 وشاشة OLED 4K 15.6 بوصة.', 7299.99, 7999.99, 8, 'https://images.unsplash.com/photo-1593642632823-8f785ba67e45?auto=format&fit=crop&w=900&q=80', 'Dell', cat_map.get('laptops'), 0, 67),
            ('Sony WH-1000XM5', 'سماعة لاسلكية بأفضل تقنية إلغاء ضوضاء عالمياً مع جودة صوت Hi-Res وبطارية 30 ساعة.', 1299.99, None, 35, 'https://images.unsplash.com/photo-1546435770-a3e426bf472b?auto=format&fit=crop&w=900&q=80', 'Sony', cat_map.get('headphones'), 1, 210),
            ('AirPods Pro 2', 'سماعات آبل اللاسلكية مع إلغاء ضوضاء فعال وصوت مكاني وشريحة H2.', 899.99, 999.99, 50, 'https://images.unsplash.com/photo-1606220588913-b3aacb4d2f37?auto=format&fit=crop&w=900&q=80', 'Apple', cat_map.get('headphones'), 0, 198),
            ('Sony A7 IV', 'كاميرا Full Frame بدقة 33MP مع تتبع ذكي للعين وفيديو 4K/60fps.', 10999.99, None, 6, 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=900&q=80', 'Sony', cat_map.get('cameras'), 0, 34),
            ('Apple Watch Series 9', 'ساعة آبل الذكية مع شريحة S9 وميزة Double Tap وشاشة Always-On أكثر إضاءة.', 1599.99, None, 30, 'https://images.unsplash.com/photo-1434494878577-86c23bcb06b9?auto=format&fit=crop&w=900&q=80', 'Apple', cat_map.get('smartwatches'), 1, 156),
            ('Logitech MX Master 3S', 'ماوس احترافي لاسلكي بعجلة MagSpeed ودقة 8000 DPI متوافق Mac/Windows.', 399.99, None, 45, 'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=900&q=80', 'Logitech', cat_map.get('accessories'), 0, 178),
            ('iPad Pro M2', 'تابلت آبل بمعالج M2 وشاشة Liquid Retina XDR 12.9 بوصة يدعم Apple Pencil.', 4299.99, None, 20, 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=900&q=80', 'Apple', cat_map.get('smartphones'), 0, 78),
            ('Samsung Galaxy Watch 6', 'ساعة ذكية بشاشة Super AMOLED ومتابعة صحية متقدمة وبطارية 40 ساعة.', 899.99, 1099.99, 22, 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=900&q=80', 'Samsung', cat_map.get('smartwatches'), 0, 95),
            ('Canon EOS R50', 'كاميرا مرايا خفيفة 24MP مثالية للمبتدئين مع تتبع الوجه وفيديو 4K.', 3999.99, None, 14, 'https://images.unsplash.com/photo-1510127034890-ba27508e9f1c?auto=format&fit=crop&w=900&q=80', 'Canon', cat_map.get('cameras'), 0, 52),
        ]
        c.executemany("""
            INSERT INTO products
            (name, description, price, old_price, stock, image, brand, category_id, is_featured, sales_count)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, products)

    # تحديث صور المنتجات الموجودة مسبقاً إذا كانت افتراضية
    product_images = {
        'iPhone 15 Pro Max': 'https://images.unsplash.com/photo-1695048133142-1a20484d2569?auto=format&fit=crop&w=900&q=80',
        'Samsung Galaxy S24 Ultra': 'https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?auto=format&fit=crop&w=900&q=80',
        'MacBook Pro M3': 'https://images.unsplash.com/photo-1541807084-5c52b6b3adef?auto=format&fit=crop&w=900&q=80',
        'Dell XPS 15': 'https://images.unsplash.com/photo-1593642632823-8f785ba67e45?auto=format&fit=crop&w=900&q=80',
        'Sony WH-1000XM5': 'https://images.unsplash.com/photo-1546435770-a3e426bf472b?auto=format&fit=crop&w=900&q=80',
        'AirPods Pro 2': 'https://images.unsplash.com/photo-1606220588913-b3aacb4d2f37?auto=format&fit=crop&w=900&q=80',
        'Sony A7 IV': 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=900&q=80',
        'Apple Watch Series 9': 'https://images.unsplash.com/photo-1434494878577-86c23bcb06b9?auto=format&fit=crop&w=900&q=80',
        'Logitech MX Master 3S': 'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=900&q=80',
        'iPad Pro M2': 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=900&q=80',
        'Samsung Galaxy Watch 6': 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=900&q=80',
        'Canon EOS R50': 'https://images.unsplash.com/photo-1510127034890-ba27508e9f1c?auto=format&fit=crop&w=900&q=80',
    }
    for product_name, image_url in product_images.items():
        c.execute("""
            UPDATE products
            SET image = ?
            WHERE name = ?
              AND (image IS NULL OR image = '' OR image = 'default.jpg')
        """, (image_url, product_name))

    seed_extra_catalog(conn)
    conn.commit()
