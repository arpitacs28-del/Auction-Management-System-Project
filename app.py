import os
from datetime import datetime,timedate
from functools import wraps
from flask import Flask,render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = 'secretkey' #secret key for session management
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False #to suppress a warning from SQLALchemy

db = SQLAlchemy(app)#initialize the database


#user model
class User(db.Model):
     id = db.Column(db.Integer,primary_key = True)
     username = db.Column(db.String(80), unique=True, nullable=False) 
     fname = db.Column(db.String(100))
     lname = db.Column(db.String(100))
     email = db.Column(db.String(100),unique = True)
     password = db.Column(db.String(100))
     cpass = db.Column(db.String(100))
     created_at = db.Column(db.DateTime, default=datetime.utcnow) 

     #Relationship

     items_created = db.relationship('Item', foreign_keys='Item.seller_id', backref='seller', lazy=True) 
     items_won = db.relationship('Item', foreign_keys='Item.winner_id', backref='winner', lazy=True) 
     bids = db.relationship('Bid', backref='bidder', lazy=True)   
     def set_password(self, password): 
       self.password_hash = generate_password_hash(password)    
     def check_password(self, password):       
      return check_password_hash(self.password_hash, password)    
     class Item(db.Model):    
         __tablename__ = 'item'   
         id = db.Column(db.Integer, primary_key=True)    
         title = db.Column(db.String(120), nullable=False)   
         description = db.Column(db.Text, nullable=False)    
         image_url = db.Column(db.String(500), nullable=True)  
         starting_bid = db.Column(db.Float, nullable=False, default=0.0)   
         current_bid = db.Column(db.Float, nullable=False, default=0.0)  
         seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)    
         winner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)     
         start_time = db.Column(db.DateTime, default=datetime.utcnow)   
         end_time = db.Column(db.DateTime, nullable=False) 
         status = db.Column(db.String(20), default='active')  # 'active', 'closed'   

         bids = db.relationship('Bid', backref='item', lazy=True, order_by="desc(Bid.amount)", cascade="all, delete-orphan") 
         def is_expired(self):
          return datetime.utcnow() >= self.end_time     
         def time_remaining_formatted(self):      
            if self.status == 'closed' or self.is_expired():        
             return "Auction Ended"      
         diff = self.end_time - datetime.utcnow()     
         days = diff.days       
         hours, remainder = divmod(diff.seconds, 3600)     
         minutes, seconds = divmod(remainder, 60)      
if days > 0:
  return f"{days}d {hours}h {minutes}m"     
elif hours > 0:
   return f"{hours}h {minutes}m {seconds}s"       
else: 
   return f"{minutes}m {seconds}s"    

def min_next_bid(self):        
 if not self.bids:        
    return self.starting_bid       
    return round(self.current_bid + 1.0, 2)
class Bid(db.Model):   
 __tablename__ = 'bid'   
id = db.Column(db.Integer, primary_key=True) 

class Bid(db.Model):     
    __tablename__ = 'bid'  
    id = db.Column(db.Integer, primary_key=True)

item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)   
user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)   
amount = db.Column(db.Float, nullable=False)   
timestamp = db.Column(db.DateTime, default=datetime.utcnow) 

def update_auction_statuses():
"""Check all active auctions; if past end_time, mark as closed & assign winner."""
expired_items = Item.query.filter(Item.status == 'active', Item.end_time <= datetime.utcnow()).all()
updated = False
for item in expired_items:
item.status = 'closed'
top_bid = Bid.query.filter_by(item_id=item.id).order_by(Bid.amount.desc()).first()
if top_bid:
item.winner_id = top_bid.user_id
updated = True
if updated:
db.session.commit()
#
def login_required(f):
@wraps(f)
def decorated_function(*args, **kwargs):
if 'user_id' not in session:
flash('Please log in to access this page.', 'warning')
return redirect(url_for('login', next=request.url))
return f(*args, **kwargs)
return decorated_function

#Database initialization with app context

with app.app_context():
      db.create_all()

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fname = request.form.get('fname', '').strip()
        lname = request.form.get('lname', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        #validations
        if not fname or len(fname.strip())<2:
            flash('Name must be at least 2 characters long.', 'error')
            return redirect(url_for('register'))
        
        if not email or '@' not in email:
            flash('Please enter a valid email address.', 'error')
            return redirect(url_for('register'))
        
        #password must be at least 8 characters long and a combination of letters and numbers and special characters
        if len(password)<8 or not any(char.isdigit() for char in password)\
              or not any(char.isalpha() for char in password) or not any(not char.isalnum()\
                                                                          for char in password):
            flash('Password must be at least 8 characters long and contain letters, \
                  numbers, and special characters.', 'error')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('register'))
        
        #check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please log in.', 'error')
            return redirect(url_for('register'))
        
        #create new user
        hashed_password = generate_password_hash(password)
        new_user = User(
            fname=fname,
            lname=lname,
            email=email,
            password=hashed_password,
            cpass=confirm_password
        )
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('sign_in'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'error')
            return redirect(url_for('register'))
        
    return render_template('register.html')

@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.fname or user.email
            flash('sign_in successful!', 'success')
            return redirect(url_for('my_profile'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template('sign_in.html')

@app.route('/auction_details')
def auction_details():
      return render_template('auction_details.html')

@app.route('/my_profile')
def my_profile():
      return render_template('my_profile.html')

@app.route('/about')
def about():
      return render_template('about.html')

@app.route('/contact')
def contact():
      return render_template('contact.html')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)