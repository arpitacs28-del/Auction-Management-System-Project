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
     fname = db.Column(db.String(100))
     lname = db.Column(db.String(100))
     email = db.Column(db.String(100),unique = True)
     password = db.Column(db.String(100))
     cpass = db.Column(db.String(100))

#Database initialization with app context
with app.app_context():
      db.create_all()

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/home')
def home():
    return render_template('01_home.html')

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