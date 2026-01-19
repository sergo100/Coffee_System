from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'uploads'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ----------------- МОДЕЛИ -----------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    fio = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    login = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20))  # admin/manager

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    producer = db.Column(db.String(100), nullable=False)
    unit = db.Column(db.String(10), nullable=False)
    price = db.Column(db.Float, nullable=False)
    short_desc = db.Column(db.String(255))
    full_desc = db.Column(db.Text)
    deleted = db.Column(db.Boolean, default=False)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fio = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    note = db.Column(db.String(255))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default="Новый") # Новый, Отгрузка, Доставка, Выдан, Отменен
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    shipped_at = db.Column(db.DateTime)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    price = db.Column(db.Float)
    discount = db.Column(db.Float, default=0)
    qty = db.Column(db.Integer, default=1)

# ----------------- LOGIN -----------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ----------------- РОУТЫ -----------------
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_input = request.form['login']
        password_input = request.form['password']
        user = User.query.filter_by(login=login_input).first()
        if user and bcrypt.check_password_hash(user.password, password_input):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Неверный логин или пароль')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    total_orders = Order.query.count()
    users = User.query.all()
    sum_orders = sum([oi.price*oi.qty*(1-oi.discount/100) for oi in OrderItem.query.all()])
    return render_template('dashboard.html', total_orders=total_orders, users=users, sum_orders=sum_orders)

# ----------------- USERS -----------------
@app.route('/users')
@login_required
def users():
    if current_user.role != 'admin':
        flash("Нет доступа")
        return redirect(url_for('dashboard'))
    users_list = User.query.all()
    return render_template('users.html', users=users_list)

# ----------------- PRODUCTS -----------------
@app.route('/products')
@login_required
def products():
    products_list = Product.query.filter_by(deleted=False).all()
    return render_template('products.html', products=products_list)

# ----------------- CLIENTS -----------------
@app.route('/clients')
@login_required
def clients():
    clients_list = Client.query.all()
    return render_template('clients.html', clients=clients_list)

# ----------------- ORDERS -----------------
@app.route('/orders')
@login_required
def orders():
    orders_list = Order.query.all()
    return render_template('orders.html', orders=orders_list)

# ----------------- CSV импорт -----------------
@app.route('/import_products')
@login_required
def import_products():
    if current_user.role != 'admin':
        flash("Нет доступа")
        return redirect(url_for('dashboard'))
    df = pd.read_csv('csv/товары.csv')
    for _, row in df.iterrows():
        p = Product(name=row['name'], producer=row['producer'], unit=row['unit'], price=row['price'], short_desc=row.get('short_desc',''), full_desc=row.get('full_desc',''))
        db.session.add(p)
    db.session.commit()
    flash("Товары импортированы")
    return redirect(url_for('products'))

@app.route('/import_clients')
@login_required
def import_clients():
    if current_user.role != 'admin':
        flash("Нет доступа")
        return redirect(url_for('dashboard'))
    df = pd.read_csv('csv/клиенты.csv')
    for _, row in df.iterrows():
        c = Client(fio=row['fio'], email=row['email'], address=row['address'], phone=row['phone'], note=row.get('note',''))
        db.session.add(c)
    db.session.commit()
    flash("Клиенты импортированы")
    return redirect(url_for('clients'))

# ----------------- ИНИЦИАЛИЗАЦИЯ -----------------
def init_admin():
    if not User.query.filter_by(login='admin').first():
        pw = bcrypt.generate_password_hash('kofeman').decode('utf-8')
        admin = User(fio='Admin', email='admin@coffee.com', login='admin', password=pw, role='admin')
        db.session.add(admin)
        # два менеджера
        m1 = User(fio='Manager1', email='m1@coffee.com', login='manager1', password=bcrypt.generate_password_hash('manager2026').decode('utf-8'), role='manager')
        m2 = User(fio='Manager2', email='m2@coffee.com', login='manager2', password=bcrypt.generate_password_hash('manager262').decode('utf-8'), role='manager')
        db.session.add(m1)
        db.session.add(m2)
        db.session.commit()

if __name__ == '__main__':
    if not os.path.exists('database.db'):
        db.create_all()
        init_admin()
    app.run(debug=True)
