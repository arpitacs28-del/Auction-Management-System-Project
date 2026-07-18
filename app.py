from flask import Flask,render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('00_index.html')

@app.route('/home')
def home():
    return render_template('01_home.html')

@app.route('/register')
def register():
      return render_template('02_register.html')

@app.route('/login')
def login():
      return render_template('03_login.html')

@app.route('/dashboard')
def dashboard():
      return render_template('04_dashboard.html')

@app.route('/auction_details')
def auction_details():
      return render_template('05_auction_details.html')

@app.route('/my_bids')
def my_bids():
      return render_template('06_my_bids.html')

@app.route('/my_profile')
def my_profile():
      return render_template('07_my_profile.html')

@app.route('/about')
def about():
      return render_template('08_about.html')

@app.route('/contact')
def contact():
      return render_template('09_contact.html')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)