from flask import Flask,render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('00_index.html')

@app.route('/home')
def home():
    return render_template('01_home.html')

@app.route('/sign_in')
def sign_in():
      return render_template('02_sign_in.html')

@app.route('/auction_details')
def auction_details():
      return render_template('03_auction_details.html')
@app.route('/my_profile')
def my_profile():
      return render_template('04_my_profile.html')

@app.route('/about')
def about():
      return render_template('05_about.html')

@app.route('/contact')
def contact():
      return render_template('06_contact.html')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)