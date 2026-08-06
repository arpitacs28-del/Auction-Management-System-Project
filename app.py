import os
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-auction-key-2026-bidding-app'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bidding.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==============================================================================
# DATABASE MODELS
# ==============================================================================

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
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

    # Relationships
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
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# ==============================================================================
# HELPER UTILITIES & DECORATORS
# ==============================================================================

# ------------------------------------------------------------------------------
# Function: update_auction_statuses()
# This function checks every active auction in the database.
# If the auction end time has already passed, it automatically changes the
# auction status to 'closed' and selects the highest bidder as the winner.
# This keeps the auction results updated whenever the application runs.
# ------------------------------------------------------------------------------
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

# ------------------------------------------------------------------------------
# Decorator: login_required
# A decorator is used to protect routes.
# Before opening a page, this decorator checks whether the user is logged in.
# If not, the user is redirected to the login page.
# This avoids unauthorized access to private pages.
# ------------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
# ------------------------------------------------------------------------------
# Context Processor: inject_globals()
# This function runs before rendering every HTML template.
# It makes the current logged-in user and current time available in all
# templates automatically, so we don't have to pass them from every route.
# It also updates auction statuses before displaying data.
# ------------------------------------------------------------------------------
def inject_globals():
    update_auction_statuses()
    current_user = None
    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
    return {
        'current_user': current_user,
        'now': datetime.utcnow()
    }

# ==============================================================================
# SAMPLE DATA SEEDING
# ==============================================================================

# ------------------------------------------------------------------------------
# Function: seed_database()
# This function inserts sample users, auction items, and bids.
# It runs only when the database is empty, making it easy for beginners to
# test the project without manually adding data.
# ------------------------------------------------------------------------------
def seed_database():
    """Seed initial sample users and live auctions for testing."""
    if User.query.first() is not None:
        return

    # Seed users
    john = User(username='john_seller', email='john@example.com')
    john.set_password('password123')

    alice = User(username='alice_bidder', email='alice@example.com')
    alice.set_password('password123')

    bob = User(username='bob_bidder', email='bob@example.com')
    bob.set_password('password123')

    db.session.add_all([john, alice, bob])
    db.session.commit()

    # Seed items
    now = datetime.utcnow()
    item1 = Item(
        title='Vintage Rolex Submariner (1985)',
        description='Classic vintage luxury timepiece in excellent working condition with original box, paper documentation, and stainless steel bracelet.',
        image_url='https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&auto=format&fit=crop',
        starting_bid=1200.0,
        current_bid=1450.0,
        seller_id=john.id,
        end_time=now + timedelta(hours=26),
        status='active'
    )

    item2 = Item(
        title='Cyberpunk RTX 4090 Gaming Beast PC',
        description='Custom water-cooled liquid gaming desktop. Intel i9-14900K, 64GB DDR5 RAM, 2TB NVMe SSD, Custom ARGB Sleeved Cables.',
        image_url='https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=800&auto=format&fit=crop',
        starting_bid=2000.0,
        current_bid=2350.0,
        seller_id=john.id,
        end_time=now + timedelta(hours=8),
        status='active'
    )

    item3 = Item(
        title='Limited Edition Signed Electric Guitar',
        description='Hand-autographed Gibson Les Paul Standard in Cherry Sunburst with hardshell case and certificate of authenticity.',
        image_url='https://images.unsplash.com/photo-1550291652-6ea9114a47b1?w=800&auto=format&fit=crop',
        starting_bid=850.0,
        current_bid=850.0,
        seller_id=john.id,
        end_time=now + timedelta(days=3),
        status='active'
    )

    item4 = Item(
        title='Retro Mechanical Keyboard & Artisan Caps',
        description='Custom built 75% hot-swappable keyboard with Lubricated Holy Panda Switches, Brass Plate, and PBT Keycaps.',
        image_url='https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=800&auto=format&fit=crop',
        starting_bid=150.0,
        current_bid=220.0,
        seller_id=alice.id,
        end_time=now - timedelta(hours=2),
        status='closed',
        winner_id=bob.id
    )

    db.session.add_all([item1, item2, item3, item4])
    db.session.commit()

    # Seed bids for sample items
    bid1 = Bid(item_id=item1.id, user_id=alice.id, amount=1300.0, timestamp=now - timedelta(hours=5))
    bid2 = Bid(item_id=item1.id, user_id=bob.id, amount=1450.0, timestamp=now - timedelta(hours=2))

    bid3 = Bid(item_id=item2.id, user_id=bob.id, amount=2150.0, timestamp=now - timedelta(hours=4))
    bid4 = Bid(item_id=item2.id, user_id=alice.id, amount=2350.0, timestamp=now - timedelta(hours=1))

    bid5 = Bid(item_id=item4.id, user_id=bob.id, amount=220.0, timestamp=now - timedelta(hours=3))

    db.session.add_all([bid1, bid2, bid3, bid4, bid5])
    db.session.commit()


# ==============================================================================
# ROUTE HANDLERS
# ==============================================================================

@app.route('/')
# ------------------------------------------------------------------------------
# Route: /
# Home Page
# Displays all auctions. It also supports searching by keyword and filtering
# auctions based on their status (active or closed).
# ------------------------------------------------------------------------------
def index():
    query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', 'active').strip()

    items_query = Item.query

    if status_filter == 'active':
        items_query = items_query.filter_by(status='active')
    elif status_filter == 'closed':
        items_query = items_query.filter_by(status='closed')

    if query:
        items_query = items_query.filter(Item.title.ilike(f'%{query}%') | Item.description.ilike(f'%{query}%'))

    items = items_query.order_by(Item.end_time.asc()).all()

    return render_template('index.html', items=items, query=query, status_filter=status_filter)


@app.route('/login', methods=['GET', 'POST'])
# ------------------------------------------------------------------------------
# Route: /login
# Allows an existing user to log in.
# It validates the username/email and password, creates a session, and
# redirects the user to the home page.
# ------------------------------------------------------------------------------
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username_or_email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email)).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username/email or password. Please try again.', 'danger')

    return render_template('sign_in.html')


@app.route('/register', methods=['GET', 'POST'])
# ------------------------------------------------------------------------------
# Route: /register
# Allows a new user to create an account.
# It validates the input, checks duplicate username/email, stores the user in
# the database, and logs the user in automatically.
# ------------------------------------------------------------------------------
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        fname = request.form.get('fname', '').strip()
        lname = request.form.get('lname', '').strip()
        username = f"{fname} {lname}".strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('Username is already taken. Choose another.', 'danger')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Email address is already registered.', 'danger')
            return render_template('register.html')

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        session['user_id'] = new_user.id
        session['username'] = new_user.username
        flash('Account registered successfully! Welcome to the Auction Bidding System.', 'success')
        return redirect(url_for('index'))

    return render_template('register.html')


@app.route('/logout')
# ------------------------------------------------------------------------------
# Route: /logout
# Clears the user's session and logs them out safely.
# ------------------------------------------------------------------------------
def logout():
    session.clear()
    flash('You have been logged out safely.', 'info')
    return redirect(url_for('index'))


@app.route('/create-auction', methods=['GET', 'POST'])
@login_required
# ------------------------------------------------------------------------------
# Route: /create-auction
# Allows a logged-in user to create a new auction.
# It validates the form data, creates a new auction record, and saves it in
# the database.
# ------------------------------------------------------------------------------
def create_auction():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        image_url = request.form.get('image_url', '').strip()
        starting_bid_str = request.form.get('starting_bid', '0').strip()
        duration_hours_str = request.form.get('duration_hours', '24').strip()

        try:
            starting_bid = float(starting_bid_str)
            if starting_bid < 0:
                raise ValueError
        except ValueError:
            flash('Please enter a valid non-negative starting bid price.', 'danger')
            return render_template('create_auction.html')

        try:
            duration_hours = int(duration_hours_str)
            if duration_hours < 1:
                raise ValueError
        except ValueError:
            flash('Auction duration must be at least 1 hour.', 'danger')
            return render_template('create_auction.html')

        end_time = datetime.utcnow() + timedelta(hours=duration_hours)

        if not image_url:
            image_url = 'https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=800&auto=format&fit=crop'

        new_item = Item(
            title=title,
            description=description,
            image_url=image_url,
            starting_bid=starting_bid,
            current_bid=starting_bid,
            seller_id=session['user_id'],
            end_time=end_time,
            status='active'
        )

        db.session.add(new_item)
        db.session.commit()

        flash('Your auction listing has been published successfully!', 'success')
        return redirect(url_for('auction_detail', item_id=new_item.id))

    return render_template('create_auction.html')


@app.route('/auction/<int:item_id>')
# ------------------------------------------------------------------------------
# Route: /auction/<item_id>
# Shows complete details of a selected auction including bid history,
# highest bidder, and remaining auction time.
# ------------------------------------------------------------------------------
def auction_detail(item_id):
    item = Item.query.get_or_404(item_id)
    update_auction_statuses()

    # Get bidding history sorted by amount descending
    bids = Bid.query.filter_by(item_id=item.id).order_by(Bid.amount.desc()).all()
    highest_bidder = bids[0].bidder if bids else None

    user_is_highest_bidder = False
    if highest_bidder and 'user_id' in session:
        user_is_highest_bidder = (highest_bidder.id == session['user_id'])

    # Find related items
    related_items = Item.query.filter(Item.status == 'active', Item.id != item_id).limit(4).all()

    return render_template(
        'auction_details.html',
        item=item,
        bids=bids,
        highest_bidder=highest_bidder,
        user_is_highest_bidder=user_is_highest_bidder,
        related_items=related_items
    )


@app.route('/auction/<int:item_id>/bid', methods=['POST'])
@login_required
# ------------------------------------------------------------------------------
# Route: /auction/<item_id>/bid
# Allows a logged-in user to place a bid.
# It validates the bid amount, checks auction rules, stores the bid, and
# updates the current highest bid.
# ------------------------------------------------------------------------------
def place_bid(item_id):
    item = Item.query.get_or_404(item_id)
    update_auction_statuses()

    if item.status == 'closed' or item.is_expired():
        flash('This auction is closed. Further bids cannot be placed.', 'danger')
        return redirect(url_for('auction_detail', item_id=item.id))

    if item.seller_id == session['user_id']:
        flash('You cannot bid on your own auction listing!', 'danger')
        return redirect(url_for('auction_detail', item_id=item.id))

    bid_amount_str = request.form.get('bid_amount', '').strip()
    try:
        bid_amount = float(bid_amount_str)
    except ValueError:
        flash('Please enter a valid numeric bid amount.', 'danger')
        return redirect(url_for('auction_detail', item_id=item.id))

    min_required = item.min_next_bid()
    if bid_amount < min_required:
        flash(f'Bid amount must be at least ${min_required:,.2f}.', 'warning')
        return redirect(url_for('auction_detail', item_id=item.id))

    # Record bid and update current_bid
    item.current_bid = bid_amount
    new_bid = Bid(item_id=item.id, user_id=session['user_id'], amount=bid_amount)
    db.session.add(new_bid)
    db.session.commit()

    flash(f'Success! You placed a bid of ${bid_amount:,.2f}. You are currently the highest bidder!', 'success')
    return redirect(url_for('auction_detail', item_id=item.id))


@app.route('/auction/<int:item_id>/close', methods=['POST'])
@login_required
# ------------------------------------------------------------------------------
# Route: /auction/<item_id>/close
# Allows only the seller to manually close an auction before its end time.
# The highest bidder becomes the winner.
# ------------------------------------------------------------------------------
def close_auction(item_id):
    item = Item.query.get_or_404(item_id)
    if item.seller_id != session['user_id']:
        flash('Only the seller can close this auction listing.', 'danger')
        return redirect(url_for('auction_detail', item_id=item.id))

    item.status = 'closed'
    top_bid = Bid.query.filter_by(item_id=item.id).order_by(Bid.amount.desc()).first()
    if top_bid:
        item.winner_id = top_bid.user_id

    db.session.commit()
    flash('Auction has been manually closed.', 'info')
    return redirect(url_for('auction_detail', item_id=item.id))


@app.route('/my-profile')
@login_required
# ------------------------------------------------------------------------------
# Route: /my-profile
# Displays all auctions where the current user has placed bids, won, or created.
# ------------------------------------------------------------------------------
def my_profile():
    user_id = session['user_id']
    user = User.query.get(user_id)
    # Get all distinct items the user has bid on
    user_bids = Bid.query.filter_by(user_id=user_id).order_by(Bid.timestamp.desc()).all()

    # Group by item
    bidded_items_map = {}
    for b in user_bids:
        if b.item_id not in bidded_items_map:
            bidded_items_map[b.item_id] = {
                'item': b.item,
                'max_user_bid': b.amount,
                'latest_bid_time': b.timestamp
            }
        else:
            if b.amount > bidded_items_map[b.item_id]['max_user_bid']:
                bidded_items_map[b.item_id]['max_user_bid'] = b.amount

    my_auctions_items = Item.query.filter_by(seller_id=user_id).order_by(Item.start_time.desc()).all()
    
    return render_template('my_profile.html', bidded_items=bidded_items_map.values(), my_auctions=my_auctions_items, user=user)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')


# ==============================================================================
# MAIN APP ENTRY POINT
# ==============================================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_database()

    print("===============================================================")
    print("  Auction Bidding System starting on http://127.0.0.1:5000")
    print("===============================================================")
    app.run(debug=True, port=5000)
