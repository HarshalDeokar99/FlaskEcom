# python -m venv venv - create a virtual env of name venv
# venv\Scripts\activate - activates venv 
# pip install flask
# pip install flask-login  - for user authentication
# pip install flask-sqlalchemy
# pip install flask-wtf
#pip install intasend-python - NOT FOR India
#pip install razorpay - for India

from flask import Flask,render_template,url_for,request,flash,redirect,session,send_from_directory,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin,login_user,login_required,logout_user,LoginManager
from datetime import datetime
from werkzeug.security import generate_password_hash,check_password_hash
import os
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, PasswordField, EmailField, BooleanField, SubmitField
from wtforms.validators import DataRequired, length, NumberRange
from werkzeug.utils import secure_filename
# from intasend import APIService - this gateway not work in INDIA
import traceback
import razorpay

#intasend api key and api token
# API_PUBLISHABLE_KEY='ISPubKey_test_27504589-d979-49b7-9877-d711eb1d4563'
# API_TOKEN='ISSecretKey_test_9f119b17-9602-4466-9fa4-fe19f2478702'

import razorpay

# Razorpay Keys
RAZORPAY_KEY_ID = "rzp_test_axfgWI5Vc08h89"
RAZORPAY_KEY_SECRET = "fpnLRnyKtrFk3BAs9KkgYAzS"

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


# App Setup
app = Flask(__name__,template_folder='website/templates',static_folder='website/static')
app.secret_key='alinaangel69'

# Database Setup
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
db=SQLAlchemy(app)

#Inherits UserMixin so Flask-Login can manage this model as a user.
class Customer(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    email = db.Column(db.String(100),unique=True)
    username=db.Column(db.String(100))
    password_hash=db.Column(db.String(150))
    date_joined=db.Column(db.DateTime(),default=datetime.utcnow)

    cart_items=db.relationship('Cart',backref=db.backref('customer',lazy=True))  #this is like join of mysql
    orders=db.relationship('Order',backref=db.backref('customer',lazy=True)) #join 
    #In SQLAlchemy, the link is automatically understood through the db.ForeignKey() declarations.



class Product(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    product_name=db.Column(db.String(100),nullable=False)
    current_price=db.Column(db.Float,nullable=False)
    previous_price=db.Column(db.Float,nullable=False)
    in_stock=db.Column(db.Integer,nullable=False)
    product_picture=db.Column(db.String(1000),nullable=False)
    flash_sale=db.Column(db.Boolean,default=False)
    date_added=db.Column(db.DateTime,default=datetime.utcnow)

    carts=db.relationship('Cart',backref=db.backref('product',lazy=True)) #join
    orders=db.relationship('Order',backref=db.backref('product',lazy=True))#join


class Cart(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    quantity = db.Column(db.Integer,nullable=False)

    customer_link=db.Column(db.Integer,db.ForeignKey('customer.id'),nullable=False) #foreign key
    product_link=db.Column(db.Integer,db.ForeignKey('product.id'),nullable=False) #foreign key

class Order(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    quantity=db.Column(db.Integer,nullable=False)
    price=db.Column(db.Float,nullable=False)
    status=db.Column(db.String(100),nullable=False)
    payment_id=db.Column(db.String(1000),nullable=False)

    customer_link=db.Column(db.Integer,db.ForeignKey('customer.id'),nullable=False) #foreign key
    product_link=db.Column(db.Integer,db.ForeignKey('product.id'),nullable=False)#foreign key

#create DB once
with app.app_context():
    db.create_all()


@app.route("/cart")
def show_cart():
    if 'user_id' not in session:
        flash("Please login to access the dashboard.")

    cart=Cart.query.filter_by(customer_link=session['user_id']).all()
    amount=0

    for item in cart:
        amount+=item.product.current_price*item.quantity

    return render_template('cart.html',amount=amount,cart=cart,total=amount+200)

@app.route("/pluscart")
def plus_cart():
    if 'user_id' not in session:
        flash("Please login to access the dashboard.")

    if request.method == 'GET':
        cart_id = request.args.get('cart_id')
        print(cart_id)
        cart_item=Cart.query.get(cart_id)
        cart_item.quantity=cart_item.quantity+1
        db.session.commit()
        cart=Cart.query.filter_by(customer_link=session['user_id'])
        amount=0
        for item in cart:
            amount+=item.product.current_price * item.quantity
        data={
            'quantity':cart_item.quantity,
            'amount':amount,
            'total':amount+200
        }
        return jsonify(data)
    
@app.route("/minuscart")
def minus_cart():
    if 'user_id' not in session:
        flash("Please login to access the dashboard.")

    if request.method == 'GET':
        cart_id = request.args.get('cart_id')
        print(cart_id)
        cart_item=Cart.query.get(cart_id)
        cart_item.quantity=cart_item.quantity-1
        db.session.commit()
        cart=Cart.query.filter_by(customer_link=session['user_id'])
        amount=0
        for item in cart:
            amount+=item.product.current_price * item.quantity
        data={
            'quantity':cart_item.quantity,
            'amount':amount,
            'total':amount+200
        }
        return jsonify(data)

@app.route("/")
def home():
    items=Product.query.filter_by(flash_sale=True)
    cart=[]
    if 'user_id' in session:
        cart=Cart.query.filter_by(customer_link=session['user_id']).all()
    return render_template('home.html',items=items,cart=cart)

@app.route("/add-to-cart/<int:item_id>")
def add_to_cart(item_id):
    if 'user_id' not in session:
        flash("Please login to access the dashboard.")
    
    item_to_add=Product.query.get(item_id)
    item_exists=Cart.query.filter_by(product_link=item_id,customer_link=session['user_id']).first()
    if item_exists:
        try:
            item_exists.quantity = item_exists.quantity + 1
            db.session.commit()
            flash(f' Quantity of {item_exists.product.product_name} has been updated')
            return redirect(request.referrer)
        except Exception as e:
            print('Quantity not updated',e)
            flash(f'Quantity of {item_exists.product.product_name} not updated')
            return redirect((request.referrer))
    new_cart_item=Cart(
        quantity=1,
        product_link=item_id,
        customer_link=session['user_id']
    )
    try:
        db.session.add(new_cart_item)
        db.session.commit()
        flash(f'{new_cart_item.product.product_name} added to cart')
    except Exception as e:
        flash(f'{new_cart_item.product.product_name} has not been added to cart')

    return redirect(request.referrer)


@app.route("/media/<path:filename>")
def get_image(filename):
    return send_from_directory('../media',filename)

@app.route("/change-password/<int:customer_id>",methods=['GET','POST'])
def change_password(customer_id):
    if 'user_id' not in session:
        flash("Please login to access the dashboard.")
        return redirect(url_for('login'))
    
    # customer=Customer.query.get(customer_id)
    customer=Customer.query.filter_by(id=customer_id).first()


    if request.method == 'POST':
        current_password=request.form['current_password']
        new_password=request.form['new_password']
        confirm_new_password=request.form['confirm_new_password']

        if check_password_hash(customer.password_hash,current_password):
            if new_password == confirm_new_password:
                customer.password_hash=generate_password_hash(new_password)
                db.session.commit()
                flash('Password Updated Successfully')
                return redirect(url_for('profile',customer_id=customer_id))
            else:
                flash('New Passwords does not match')
        else:
            flash('Current Password is incorrect')
    
    return render_template('change_password.html')

@app.route("/profile/<int:customer_id>")
def profile(customer_id):
    if 'user_id' not in session:
        flash("Please login to access the dashboard.")
        return redirect(url_for('login'))
    
    customer=Customer.query.get(customer_id)
    return render_template('profile.html',customer=customer) 

@app.route("/logout",methods=['GET','POST'])
def log_out():
    if 'user_id' not in session:
        flash("Please login to access the dashboard.")
        return redirect(url_for('login'))
    
    session.clear()
    flash("Logged out successfully.")
    return redirect(url_for('home'))

@app.route("/place-order")
def place_order():
    if 'user_id' not in session:
        flash("Please login to access the dashboard.")
        return redirect(url_for('login'))
    
    # Step 1: Get cart items of the logged-in user
    customer_cart=Cart.query.filter_by(customer_link=session['user_id']).all()

    if customer_cart:
        try:
            total = 0
            for item in customer_cart:
                total += item.product.current_price * item.quantity
            
            total_in_paise = int((total + 200) * 100)  # Razorpay uses paise

            # Step 2: Create Razorpay order
            client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

            razorpay_order = client.order.create({
                "amount": total_in_paise,
                "currency": "INR",
                "payment_capture": 1,  # auto capture after payment
                "notes": {
                    "customer_email": session['email'],
                    "user_id": session['user_id']
                }
            })

            # Step 3: Store Order and update product/cart
            for item in customer_cart:
                new_order=Order()
                new_order.quantity=item.quantity
                new_order.price=item.product.current_price
                new_order.status="Pending" # will update after real payment confirmation
                new_order.payment_id=razorpay_order['id']
                new_order.product_link=item.product_link
                new_order.customer_link=item.customer_link
                db.session.add(new_order)
                product=Product.query.get(item.product_link)
                product.in_stock-=item.quantity
                db.session.delete(item)
            db.session.commit()
            flash('Order Placed Successfully!')
            return render_template('orders.html')
        except Exception as e:
            print("❌ Exception during order placement:")
            print(traceback.format_exc())  # ✅ This will show full details
            flash('Order not placed')
            return redirect('/')
    else:
        flash('Your cart is Empty')
        return redirect('/')


@app.route("/removecart",methods=['GET','POST'])
def remove_cart():
    if 'user_id' not in session:
        flash("Please login to access the dashboard.")
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        cart_id=request.args.get('cart_id')
        cart_item=Cart.query.get(cart_id)
        db.session.delete(cart_item)
        db.session.commit()
        cart=Cart.query.filter_by(customer_link=session['user_id']).all()
        amount=0
        for item in cart:
            amount += item.product.current_price * item.quantity
        data={
            'quantity':cart_item.quantity,
            'amount':amount,
            'total':amount+200
        }
        return jsonify(data)

@app.route("/login",methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email=request.form['email'].strip()
        password=request.form['password'].strip()

        customer=Customer.query.filter_by(email=email).first()

        if customer:
            if check_password_hash(customer.password_hash,password):
              
                session['user_id']=customer.id
                session['username']=customer.username
                session['email']=customer.email

                flash("Login SUccessful!")
                return redirect(url_for('home'))
            else:
                flash("Incorrect Email or Password")

        else:
            flash("Account does not exist please sign Up")

    return render_template('login.html')

@app.route("/sign-up",methods=['GET','POST'])
def sign_up():
    if request.method == 'POST':
        email=request.form['email'].strip()
        password1=request.form['password1'].strip()
        password2=request.form['password2'].strip()
        username=request.form['username'].strip()

        existing=Customer.query.filter_by(email=email).first()
        if existing:
            flash("Email already exists")
            return redirect(url_for('sign_up'))

        if password1 == password2:
            new_customer = Customer(
                email=email,
                username=username,
                password_hash=generate_password_hash(password1)
            )

            try:
                db.session.add(new_customer)
                db.session.commit()
                flash('Account Created Successfully, You can now Login')
                return redirect(url_for('login'))
            except Exception as e:
                print(e)
                flash('Account not created!!, Email already exists')

            request.form['email']=''
            request.form['username']=''
            request.form['password1']=''
            request.form['password2']=''

    return render_template('signup.html')

@app.route("/add-shop-items",methods=['GET','POST'])
def add_shop_items():
    if 'user_id' not in session:
        flash("Please login to access the dashboard.")
        return redirect(url_for('login'))
    if session['user_id'] == 1:
        if request.method=='POST':
            product_name=request.form['product_name']
            current_price=request.form['current_price']
            previous_price=request.form['previous_price']
            in_stock=request.form['in_stock']
            flash_sale = 'flash_sale' in request.form  # safe checkbox handling
            #This line sets flash_sale = True if checkbox is checked, otherwise False.
            file=request.files['product_picture']

            file_name=secure_filename(file.filename) #the white spaces or invalid character in file name will be replaced by underscore

            file_path= f'./website/static/media/{file_name}'
            file_path_db=f'./media/{file_name}'

            file.save(file_path)

            new_shop_item=Product(
                product_name=product_name,
                current_price=current_price,
                previous_price=previous_price,
                in_stock=in_stock,
                flash_sale=flash_sale,
                product_picture=file_path_db
            )
            try:
                db.session.add(new_shop_item)
                db.session.commit()
                flash(f'{product_name} added Successfully!')
                print('Product added')
                redirect(url_for('add_shop_items'))
            except Exception as e:
                print(e)
                flash('Item not added.')

        return render_template('add-shop-items.html')
    return render_template('404.html') 
  
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html')

@app.route("/shop-items",methods=['GET','POST'])
def shop_items():
    if 'user_id' not in session:
        flash("Please login to access the dashboard.")
        return redirect(url_for('login'))
    
    if session['user_id'] == 1:
        items=Product.query.order_by(Product.date_added).all()
        return render_template('shop_items.html',items=items)
   
    return render_template('404.html')


@app.route("/update-item/<int:item_id>",methods=['GET','POST'])
def update_item(item_id):
    if 'user_id' not in session:
        flash("Please login to access the dashboard.")
        return redirect(url_for('login'))
    if session['user_id'] == 1:
        item_to_update=Product.query.get(item_id)

        if request.method == 'POST':
            product_name=request.form['product_name']
            current_price=request.form['current_price']
            previous_price=request.form['previous_price']
            in_stock=request.form['in_stock']
            flash_sale='flash_sale' in request.form

            file=request.files['product_picture']
            file_name=secure_filename(file.filename)
            file_path= f'./website/static/media/{file_name}'
            file_path_db=f'./media/{file_name}'
            file.save(file_path)

            try:
                Product.query.filter_by(id=item_id).update(dict(product_name=product_name,current_price=current_price,previous_price=previous_price,in_stock=in_stock,flash_sale=flash_sale,product_picture=file_path_db))
                db.session.commit()
                flash(f'{product_name} updated Successfully')
                print('Product Updated')
                return redirect(url_for('shop_items'))
            except Exception as e:
                print('Product not updated',e)
                flash('Item Not updated!!!')

        return render_template('update_item.html',item_to_update=item_to_update)
    return render_template('404.html')

@app.route("/delete-item/<int:item_id>",methods=['GET','POST'])
def delete_item(item_id):
    if 'user_id' not in session:
        flash("Please login to access the dashboard.")
        return redirect(url_for('login'))
    
    if session['user_id'] == 1:
        try:
            item_to_delete=Product.query.get(item_id)
            db.session.delete(item_to_delete)
            db.session.commit()
            flash('One item deleted')
            return redirect(url_for('shop_items'))
        except Exception as e:
            flash('Item not deleted!!')
        return redirect(url_for('shop_items'))
    return render_template('404.html')

@app.route("/orders",methods=['GET','POST'])
def order():
    if 'user_id' not in session:
        flash("Please login to access the dashboard.")
        return redirect(url_for('login'))
    
    orders=Order.query.filter_by(customer_link=session['user_id']).all()
    return render_template('orders.html',orders=orders)
    
@app.route("/view-orders",methods=['GET','POST'])
def order_view():
    if 'user_id' not in session:
        flash("Please login to access the dashboard.")
        return redirect(url_for('login'))
    
    if session['user_id'] == 1:
        orders=Order.query.all()
        return render_template('view_orders.html',orders=orders)
    return render_template('404.html')

@app.route("/update-order/<int:order_id>",methods=['GET','POST'])
def update_order(order_id):
    if 'user_id' not in session:
        flash("Please login to access the dashboard.")
        return redirect(url_for('login'))
    
    if session['user_id'] == 1:
        order=Order.query.get(order_id)
        if request.method == 'POST':
            status=request.form['order_status']
            order.status=status
            try:
                db.session.commit()
                flash(f'Order {order_id} Updated Successfully')
                return redirect(url_for('order_view'))
            except Exception as e:
                print(e)
                flash(f'Order {order_id} not updated')
                return redirect(url_for('order_view'))
        return render_template('order_update.html',order_id=order_id)
    return render_template('404.html')

@app.route("/customers",methods=['GET','POST'])
def display_customers():
    if 'user_id' not in session:
        flash("Please login to access the dashboard.")
        return redirect(url_for('login'))
    if session['user_id'] == 1:
        customers=Customer.query.all()
        return render_template('customers.html',customers=customers)
    return render_template('404.html')

@app.route("/admin-page")
def admin_page():
    if 'user_id' not in session:
        flash("Please login to access the dashboard.")
        return redirect(url_for('login'))
    if session['user_id'] == 1:
        return render_template('admin.html')
    return render_template('404.html')

@app.route("/search",methods=['GET','POST'])
def search():
    cart=[]
    if 'user_id' in session:
        cart=Cart.query.filter_by(customer_link=session['user_id']).all()
    if request.method=='POST':
        search_query=request.form.get('search')
        items=Product.query.filter(Product.product_name.ilike(f'%{search_query}%')).all()
        return render_template('search.html',items=items,cart=cart)
    return render_template('search.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # You can add logic here to save messages to DB or send email
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        flash("Message sent successfully!", "success")
        return redirect(url_for('contact'))
    return render_template('contact.html')


if __name__ == '__main__':
    app.run(debug=True)