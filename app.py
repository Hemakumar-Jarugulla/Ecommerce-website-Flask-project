from flask import Flask, render_template, redirect, url_for, request, session
import random
import razorpay
from database import db
import bcrypt
from mail import send_email

app = Flask(__name__)
app.secret_key = 'eshop@26'

RAZORPAY_KEY_ID = "rzp_test_ThN8Lqt5brwuvY"
RAZORPAY_KEY_SECRET = "mesr2c5qwwyOh0v3gCDf4eMq"

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def generate_otp():
    return str(random.randint(100000, 999999))
 
@app.route('/')
def base():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id,name,password,two_step_verification FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
        if not user:
            return render_template('login.html', info='Invalid email or password')
        if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            return render_template('login.html', info='Invalid email or password')
        session['user_id'] = user['id']
        session['uname'] = user['name']
        session['login_email'] = email
        if user['two_step_verification']:
            otp = generate_otp()
            session['otp'] = otp
            subject = "E-Shop OTP Verification"
            body = f"""Hello {user['name']},

Your E-Shop OTP is: {otp}

Please do not share this OTP with anyone.
"""
            if send_email(email, subject, body):
                return redirect(url_for('verify'))
            session.pop('user_id', None)
            session.pop('uname', None)
            session.pop('login_email', None)
            return render_template('login.html', info='Unable to send OTP')
        session['verified_login'] = True
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if password != confirm_password:
            return render_template('register.html', info='Passwords do not match')
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE email=%s OR phone=%s", (email, phone))
        existing_user = cursor.fetchone()
        if existing_user:
            cursor.close()
            return render_template('register.html', info='Email or phone already registered')
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute("INSERT INTO users (name,email,phone,password,two_step_verification) VALUES (%s,%s,%s,%s,%s)", (name, email, phone, hashed_password, False))
        db.commit()
        cursor.close()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        enteredotp = request.form.get('otp')
        storedotp = session.get('otp')
        if storedotp and enteredotp == storedotp:
            session.pop('otp', None)
            session['verified_login'] = True
            return redirect(url_for('dashboard'))
        return render_template('verify.html', info='Enter the correct OTP')
    return render_template('verify.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, name, category, description, price, stock, image, rating FROM products WHERE stock > 0 ORDER BY id DESC")
    products = cursor.fetchall()
    cursor.execute("SELECT product_id FROM favorites WHERE user_id=%s", (session['user_id'],))
    favorites = cursor.fetchall()
    favorite_ids = {item['product_id'] for item in favorites}

    for product in products:
        product['is_favorite'] = product['id'] in favorite_ids

    cursor.close()

    return render_template('dashboard.html', products=products)

@app.route('/productdetails/<int:product_id>')
def productdetails(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, name, category, description, price, stock, image, rating FROM products WHERE id=%s", (product_id,))
    product = cursor.fetchone()

    if not product:
        cursor.close()
        return "Product not found", 404

    cursor.execute("SELECT id FROM favorites WHERE user_id=%s AND product_id=%s", (session['user_id'], product_id))
    favorite = cursor.fetchone()
    product['is_favorite'] = favorite is not None

    cursor.close()

    return render_template('productdetails.html', product=product)

@app.route('/checkout/<int:product_id>', methods=['GET', 'POST'])
def checkout(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id,name,price,stock,image FROM products WHERE id=%s", (product_id,))
    product = cursor.fetchone()
    if not product:
        cursor.close()
        return "Product not found", 404
    if product['stock'] <= 0:
        cursor.close()
        return "Product is out of stock", 400
    cursor.execute("SELECT id,full_name,phone,address,city,state,pincode,is_default FROM addresses WHERE user_id=%s ORDER BY is_default DESC,id DESC", (session['user_id'],))
    addresses = cursor.fetchall()
    cursor.close()
    if request.method == 'POST':
        address_id = request.form.get('address_id')
        if address_id:
            session['selected_address_id'] = int(address_id)
            session['buy_now_product_id'] = product_id
            session['buy_now_quantity'] = int(request.form.get('quantity', 1))
            return redirect(url_for('ordersummary', product_id=product_id))
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        pincode = request.form.get('pincode')
        cursor = db.cursor(dictionary=True)
        cursor.execute("INSERT INTO addresses (user_id,full_name,phone,address,city,state,pincode) VALUES (%s,%s,%s,%s,%s,%s,%s)", (session['user_id'], full_name, phone, address, city, state, pincode))
        db.commit()
        address_id = cursor.lastrowid
        cursor.close()
        session['selected_address_id'] = address_id
        session['buy_now_product_id'] = product_id
        session['buy_now_quantity'] = int(request.form.get('quantity', 1))
        return redirect(url_for('ordersummary', product_id=product_id))
    return render_template('checkout.html', product=product, product_id=product_id, addresses=addresses)

@app.route('/ordersummary/<int:product_id>')
def ordersummary(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    address_id = session.get('selected_address_id')
    quantity = session.get('buy_now_quantity', 1)
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id,name,description,price,stock,image FROM products WHERE id=%s", (product_id,))
    product = cursor.fetchone()
    if not product:
        cursor.close()
        return "Product not found", 404
    if quantity < 1 or quantity > product['stock']:
        cursor.close()
        return "Invalid quantity", 400
    if not address_id:
        cursor.close()
        return redirect(url_for('checkout', product_id=product_id))
    cursor.execute("SELECT id,full_name,phone,address,city,state,pincode FROM addresses WHERE id=%s AND user_id=%s", (address_id, session['user_id']))
    address = cursor.fetchone()
    cursor.close()
    if not address:
        return "Address not found", 404
    total_amount = float(product['price']) * quantity
    session['Final_price'] = total_amount
    return render_template('ordersummary.html', product=product, address=address, quantity=quantity, total_amount=total_amount, product_id=product_id)

@app.route('/payment/<int:product_id>', methods=['GET', 'POST'])
def payment(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    address_id = session.get('selected_address_id')
    quantity = session.get('buy_now_quantity', 1)
    if not address_id:
        return redirect(url_for('checkout', product_id=product_id))
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id,name,price,stock,image FROM products WHERE id=%s", (product_id,))
    product = cursor.fetchone()
    cursor.close()
    if not product:
        return "Product not found", 404
    if quantity < 1 or quantity > product['stock']:
        return "Invalid quantity", 400
    total_amount = float(product['price']) * quantity
    return render_template('payment.html', product=product, product_id=product_id, quantity=quantity, total_amount=total_amount)

@app.route('/create_cod_order/<int:product_id>', methods=['POST'])
def create_cod_order(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    address_id = session.get('selected_address_id')
    quantity = session.get('buy_now_quantity', 1)
    if not address_id:
        return redirect(url_for('checkout', product_id=product_id))
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id,name,price,stock,image FROM products WHERE id=%s", (product_id,))
    product = cursor.fetchone()
    if not product:
        cursor.close()
        return "Product not found", 404
    if quantity < 1 or quantity > product['stock']:
        cursor.close()
        return "Invalid quantity", 400
    total_amount = float(product['price']) * quantity
    cursor.execute("INSERT INTO orders (user_id,address_id,total_amount,status) VALUES (%s,%s,%s,%s)", (session['user_id'], address_id, total_amount, 'CONFIRMED'))
    order_id = cursor.lastrowid
    cursor.execute("INSERT INTO order_items (order_id,product_id,quantity,price) VALUES (%s,%s,%s,%s)", (order_id, product_id, quantity, product['price']))
    cursor.execute("INSERT INTO payments (order_id,payment_method,amount,status,paid_at) VALUES (%s,%s,%s,%s,CURRENT_TIMESTAMP)", (order_id, 'COD', total_amount, 'SUCCESS'))
    cursor.execute("UPDATE products SET stock=stock-%s WHERE id=%s AND stock>=%s", (quantity, product_id, quantity))
    db.commit()
    cursor.close()
    session.pop('selected_address_id', None)
    session.pop('buy_now_product_id', None)
    session.pop('buy_now_quantity', None)
    session.pop('Final_price', None)
    return redirect(url_for('paymentsuccess', order_id=order_id))

@app.route('/create_razorpay_order/<int:product_id>', methods=['POST'])
def create_razorpay_order(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    address_id = session.get('selected_address_id')
    quantity = session.get('buy_now_quantity', 1)
    payment_method = request.form.get('payment_method')
    if payment_method not in ['UPI', 'CARD']:
        return "Invalid payment method", 400
    if not address_id:
        return redirect(url_for('checkout', product_id=product_id))
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id,name,price,stock,image FROM products WHERE id=%s", (product_id,))
    product = cursor.fetchone()
    if not product:
        cursor.close()
        return "Product not found", 404
    if quantity < 1 or quantity > product['stock']:
        cursor.close()
        return "Invalid quantity", 400
    total_amount = float(product['price']) * quantity
    cursor.execute("INSERT INTO orders (user_id,address_id,total_amount,status) VALUES (%s,%s,%s,%s)", (session['user_id'], address_id, total_amount, 'PLACED'))
    order_id = cursor.lastrowid
    cursor.execute("INSERT INTO order_items (order_id,product_id,quantity,price) VALUES (%s,%s,%s,%s)", (order_id, product_id, quantity, product['price']))
    cursor.execute("INSERT INTO payments (order_id,payment_method,amount,status) VALUES (%s,%s,%s,%s)", (order_id, payment_method, total_amount, 'PENDING'))
    db.commit()
    razorpay_order = razorpay_client.order.create({"amount": int(total_amount * 100), "currency": "INR", "payment_capture": 1})
    cursor.execute("UPDATE payments SET razorpay_order_id=%s WHERE order_id=%s", (razorpay_order['id'], order_id))
    db.commit()
    cursor.close()
    return render_template('razorpay_payment.html', order_id=order_id, razorpay_order_id=razorpay_order['id'], razorpay_key=RAZORPAY_KEY_ID, amount=int(total_amount * 100), payment_method=payment_method, product=product, quantity=quantity, total_amount=total_amount)

@app.route('/payment_success/<int:order_id>', methods=['POST'])
def payment_success(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    payment_id = request.form.get('razorpay_payment_id')
    razorpay_order_id = request.form.get('razorpay_order_id')
    signature = request.form.get('razorpay_signature')
    if not payment_id or not razorpay_order_id or not signature:
        return "Missing payment details", 400
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT o.id,o.user_id,o.address_id,o.total_amount,o.status,p.id AS payment_id,p.payment_method,p.razorpay_order_id,p.status AS payment_status FROM orders o JOIN payments p ON o.id=p.order_id WHERE o.id=%s AND o.user_id=%s", (order_id, session['user_id']))
    order = cursor.fetchone()
    if not order:
        cursor.close()
        return "Order not found", 404
    if order['razorpay_order_id'] != razorpay_order_id:
        cursor.close()
        return "Invalid Razorpay order", 400
    try:
        razorpay_client.utility.verify_payment_signature({'razorpay_order_id': razorpay_order_id, 'razorpay_payment_id': payment_id, 'razorpay_signature': signature})
        cursor.execute("SELECT product_id,quantity FROM order_items WHERE order_id=%s", (order_id,))
        item = cursor.fetchone()
        if not item:
            cursor.close()
            return "Order item not found", 404
        cursor.execute("SELECT stock FROM products WHERE id=%s", (item['product_id'],))
        product = cursor.fetchone()
        if not product or product['stock'] < item['quantity']:
            cursor.close()
            return "Insufficient stock", 400
        cursor.execute("UPDATE payments SET transaction_id=%s,status=%s,paid_at=CURRENT_TIMESTAMP WHERE order_id=%s", (payment_id, 'SUCCESS', order_id))
        cursor.execute("UPDATE orders SET status=%s WHERE id=%s", ('CONFIRMED', order_id))
        cursor.execute("UPDATE products SET stock=stock-%s WHERE id=%s AND stock>=%s", (item['quantity'], item['product_id'], item['quantity']))
        db.commit()
        cursor.execute("SELECT oi.quantity,oi.price,p.name,p.image FROM order_items oi JOIN products p ON oi.product_id=p.id WHERE oi.order_id=%s", (order_id,))
        item_details = cursor.fetchone()
        cursor.close()
        session.pop('selected_address_id', None)
        session.pop('buy_now_product_id', None)
        session.pop('buy_now_quantity', None)
        session.pop('Final_price', None)
        return render_template('paymentsuccess.html', order=order, item=item_details)
    except razorpay.errors.SignatureVerificationError:
        cursor.execute("UPDATE payments SET status=%s WHERE order_id=%s", ('FAILED', order_id))
        db.commit()
        cursor.close()
        return "Payment verification failed", 400

@app.route('/paymentsuccess/<int:order_id>')
def paymentsuccess(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT o.id,o.total_amount,o.status,p.payment_method,p.transaction_id,p.status AS payment_status FROM orders o JOIN payments p ON o.id=p.order_id WHERE o.id=%s AND o.user_id=%s", (order_id, session['user_id']))
    order = cursor.fetchone()
    if not order:
        cursor.close()
        return "Order not found", 404
    cursor.execute("SELECT oi.quantity,oi.price,p.name,p.image FROM order_items oi JOIN products p ON oi.product_id=p.id WHERE oi.order_id=%s", (order_id,))
    item = cursor.fetchone()
    cursor.close()
    return render_template('paymentsuccess.html', order=order, item=item)

@app.route('/myorders')
def myorders():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT o.id,o.total_amount,o.status,o.created_at,oi.quantity,oi.price,p.id AS product_id,p.name,p.image FROM orders o JOIN order_items oi ON o.id=oi.order_id JOIN products p ON oi.product_id=p.id WHERE o.user_id=%s ORDER BY o.id DESC", (session['user_id'],))
    orders = cursor.fetchall()
    cursor.close()
    return render_template('myorders.html', orders=orders)

@app.route('/track/<int:order_id>')
def track(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT o.id,o.total_amount,o.status,o.created_at,a.full_name,a.phone,a.address,a.city,a.state,a.pincode FROM orders o JOIN addresses a ON o.address_id=a.id WHERE o.id=%s AND o.user_id=%s", (order_id, session['user_id']))
    order = cursor.fetchone()
    if not order:
        cursor.close()
        return "Order not found", 404
    cursor.execute("SELECT oi.quantity,oi.price,p.id AS product_id,p.name,p.image FROM order_items oi JOIN products p ON oi.product_id=p.id WHERE oi.order_id=%s", (order_id,))
    items = cursor.fetchall()
    cursor.close()
    return render_template('track.html', order=order, items=items)

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT c.id,c.product_id,c.quantity,p.name,p.price,p.stock,p.image,p.rating FROM cart c JOIN products p ON c.product_id=p.id WHERE c.user_id=%s", (session['user_id'],))
    cart_items = cursor.fetchall()
    cursor.close()
    total = sum(float(item['price']) * item['quantity'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/addtocart/<int:product_id>', methods=['GET', 'POST'])
def addtocart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    quantity = int(request.form.get('quantity', 1)) if request.method == 'POST' else 1
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id,stock FROM products WHERE id=%s", (product_id,))
    product = cursor.fetchone()
    if not product:
        cursor.close()
        return "Product not found", 404
    cursor.execute("SELECT id,quantity FROM cart WHERE user_id=%s AND product_id=%s", (session['user_id'], product_id))
    cart_item = cursor.fetchone()
    if cart_item:
        new_quantity = cart_item['quantity'] + quantity
        if new_quantity > product['stock']:
            cursor.close()
            return "Requested quantity exceeds available stock", 400
        cursor.execute("UPDATE cart SET quantity=%s WHERE id=%s", (new_quantity, cart_item['id']))
    else:
        if quantity > product['stock']:
            cursor.close()
            return "Requested quantity exceeds available stock", 400
        cursor.execute("INSERT INTO cart (user_id,product_id,quantity) VALUES (%s,%s,%s)", (session['user_id'], product_id, quantity))
    db.commit()
    cursor.close()
    return redirect(url_for('cart'))

@app.route('/updatecart/<int:cart_id>', methods=['POST'])
def updatecart(cart_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    quantity = int(request.form.get('quantity', 1))
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT c.id,c.product_id,p.stock FROM cart c JOIN products p ON c.product_id=p.id WHERE c.id=%s AND c.user_id=%s", (cart_id, session['user_id']))
    cart_item = cursor.fetchone()
    if not cart_item:
        cursor.close()
        return "Cart item not found", 404
    if quantity < 1 or quantity > cart_item['stock']:
        cursor.close()
        return "Invalid quantity", 400
    cursor.execute("UPDATE cart SET quantity=%s WHERE id=%s", (quantity, cart_id))
    db.commit()
    cursor.close()
    return redirect(url_for('cart'))

@app.route('/removefromcart/<int:cart_id>')
def removefromcart(cart_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cursor = db.cursor(dictionary=True)
    cursor.execute("DELETE FROM cart WHERE id=%s AND user_id=%s", (cart_id, session['user_id']))
    db.commit()
    cursor.close()
    return redirect(url_for('cart'))

@app.route('/cartcheckout', methods=['POST'])
def cartcheckout():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT c.id,c.product_id,c.quantity,p.name,p.price,p.stock,p.image FROM cart c JOIN products p ON c.product_id=p.id WHERE c.user_id=%s", (session['user_id'],))
    cart_items = cursor.fetchall()
    cursor.close()
    if not cart_items:
        return "Cart is empty", 400
    for item in cart_items:
        if item['quantity'] > item['stock']:
            return f"Insufficient stock for {item['name']}", 400
    session['cart_checkout'] = True
    return redirect(url_for('cartaddress'))

@app.route('/cartaddress', methods=['GET', 'POST'])
def cartaddress():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if not session.get('cart_checkout'):
        return redirect(url_for('cart'))
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id,full_name,phone,address,city,state,pincode,is_default FROM addresses WHERE user_id=%s ORDER BY is_default DESC,id DESC", (session['user_id'],))
    addresses = cursor.fetchall()
    cursor.close()
    if request.method == 'POST':
        address_id = request.form.get('address_id')
        if address_id:
            session['selected_address_id'] = int(address_id)
            return redirect(url_for('cartordersummary'))
        cursor = db.cursor(dictionary=True)
        cursor.execute("INSERT INTO addresses (user_id,full_name,phone,address,city,state,pincode) VALUES (%s,%s,%s,%s,%s,%s,%s)", (session['user_id'], request.form.get('full_name'), request.form.get('phone'), request.form.get('address'), request.form.get('city'), request.form.get('state'), request.form.get('pincode')))
        db.commit()
        session['selected_address_id'] = cursor.lastrowid
        cursor.close()
        return redirect(url_for('cartordersummary'))
    return render_template('cartaddress.html', addresses=addresses)

@app.route('/cartordersummary')
def cartordersummary():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if not session.get('cart_checkout') or not session.get('selected_address_id'):
        return redirect(url_for('cart'))
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT c.id,c.product_id,c.quantity,p.name,p.price,p.stock,p.image FROM cart c JOIN products p ON c.product_id=p.id WHERE c.user_id=%s", (session['user_id'],))
    cart_items = cursor.fetchall()
    cursor.execute("SELECT id,full_name,phone,address,city,state,pincode FROM addresses WHERE id=%s AND user_id=%s", (session['selected_address_id'], session['user_id']))
    address = cursor.fetchone()
    cursor.close()
    if not cart_items or not address:
        return "Cart or address not found", 404
    total_amount = sum(float(item['price']) * item['quantity'] for item in cart_items)
    return render_template('cartordersummary.html', cart_items=cart_items, address=address, total_amount=total_amount)

@app.route('/addtofav/<int:product_id>')
def addtofav(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id FROM favorites WHERE user_id=%s AND product_id=%s", (session['user_id'], product_id))
    favorite = cursor.fetchone()

    if favorite:
        cursor.execute("DELETE FROM favorites WHERE id=%s", (favorite['id'],))
    else:
        cursor.execute("INSERT INTO favorites(user_id, product_id) VALUES(%s, %s)", (session['user_id'], product_id))

    db.commit()
    cursor.close()

    return redirect(request.referrer or url_for('dashboard'))

@app.route('/myfav')
def myfav():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT p.id,p.name,p.category,p.description,p.price,p.stock,p.image,p.rating FROM favorites f JOIN products p ON f.product_id=p.id WHERE f.user_id=%s ORDER BY f.id DESC", (session['user_id'],))
    products = cursor.fetchall()
    cursor.close()
    return render_template('myfav.html', products=products)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id,name,email,phone,two_step_verification FROM users WHERE id=%s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    if not user:
        return "User not found", 404
    return render_template('profile.html', user=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)


















