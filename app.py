import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
secret_key = secrets.token_hex(16)
app.secret_key = 'your_secret_key'
DATABASE = 'database.db'
UPLOAD_FOLDER = 'static/img'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Connect Database
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn
def init_db():
    conn = get_db_connection()
    with app.open_resource('schema.sql', mode='r') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
def sum_product():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tblproduct")
        conn.commit()
    total_amount = 0
    total_stock = 0
    for item in cursor.fetchall():
        total_amount += item[2] * item[3]
        total_stock += item[2]
    return total_amount, total_stock
def sum_staff():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM tblUser where role = 'Employee'")
        total_emp = cursor.fetchall()
        conn.commit()
        cursor.execute("SELECT count(*) FROM tblUser")
        total_staff = cursor.fetchall()
        conn.commit()
    return total_staff, total_emp

def chart():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tblproduct")
        products = cursor.fetchall()
        cursor.execute("select role, count(*) from tblUser group by role ")
        users = cursor.fetchall()
    return products, users

# First View
@app.route('/')
def home():
    return render_template('login.html')

# Home Page and Check Session
@app.route('/index')
def index():
    total_price, total_stock = sum_product()
    formatted_total_amount = f"${total_price:.2f}"
    total_staff, total_emp = sum_staff()
    products, users = chart()

    if 'logged' in session or session['role'] == 'Admin':
        return render_template('index.html', total_price=formatted_total_amount, total_stock=total_stock, total_staff=total_staff, total_emp=total_emp, products=products, users=users)
    return render_template('index.html')

# Login and Set Session
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tblUser WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()

        if user:
            session['logged'] = True
            session['id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]
            return redirect(url_for('index'))
        else:
            error_message = 'Wrong! account invalid!'
            return render_template('login.html', error_message=error_message, username=username)

# Logout and Clear Session
@app.route('/logout')
def logout():
    session.pop('logged', None)
    session.pop('id', None)
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('home'))

# List User
@app.route('/users')
def users():
    msg = ''
    if 'logged' in session and session['role'] == 'Admin':
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tblUser")
            users = cursor.fetchall()
            cursor.execute("select count(*) from tblUser WHERE role = 'Admin'")
            admin_count = cursor.fetchone()[0]
            if admin_count <= 1:
                msg = 'Only one Admin left, cannot delete right now'
        return render_template('users.html', users=users, msg=msg)

# Add User
@app.route('/add_user', methods=['POST'])
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tblUser (username, password, role) VALUES (?, ?, ?)", (username, password, role))
            conn.commit()

        return redirect(url_for('users'))

# Edit User
@app.route('/edit_user/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE tblUser SET username = ?, password = ?, role = ? WHERE id = ?", (username, password, role, user_id))
            conn.commit()

        return redirect(url_for('users'))

# Delete User
@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tblUser WHERE id = ?", (user_id,))
        conn.commit()

    return redirect(url_for('users'))

# Product List
@app.route('/products')
def products():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tblproduct")
        products = cursor.fetchall()
    return render_template('products.html', products=products)

# Add Product
@app.route('/add_product', methods=['POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        quantity = request.form['quantity']
        price = request.form['price']
        description = request.form['description']
        image_file = request.files['image']

        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tblproduct (name, qty, price, desc, image) VALUES (?, ?, ?, ?, ?)",
                           (name, quantity, price, description, image_file.filename))
            conn.commit()
        if image_file:
            filename = image_file.filename
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
        return redirect(url_for('products', name=name))

# Edit Product
@app.route('/edit_product/<int:product_id>', methods=['POST'])
def edit_product(product_id):
    if request.method == 'POST':
        name = request.form['name']
        quantity = request.form['quantity']
        price = request.form['price']
        description = request.form['description']
        image_file = request.files['image']
        old_image = request.form['old_image']

        if image_file and allowed_file(image_file.filename):
            filename = image_file.filename
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            image_upload = image_file.filename
        else:
            image_upload = old_image
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE tblproduct SET name = ?, qty = ?, price = ?, desc = ?, image = ? WHERE id = ?",
                           (name,quantity, price, description, image_upload, product_id))
            conn.commit()
    return redirect(url_for('products'))

# Delete Product
@app.route('/delete_product/<int:product_id>', methods=['GET'])
def delete_product(product_id):
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tblproduct WHERE id = ?", (product_id,))
        conn.commit()

    return redirect(url_for('products'))

if __name__ == '__main__':
    init_db()
    app.run()
