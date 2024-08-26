from datetime import datetime, timezone, timedelta
import pandas as pd
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import declarative_base
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import jwt


# Database Configuration
DATABASE_URL = 'sqlite:///products.db'
JWT_SECRET_KEY = 'superSecretKey' # add in env var or config manager for security

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

Base = declarative_base()

# Database Models
class User(db.Model):
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password = Column(String(120), nullable=False)

class Product(db.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    category = Column(String(50))
    price = Column(Float)
    quantity_sold = Column(Integer)
    rating = Column(Float)

# Initialize the database
def init_db():
    with app.app_context():
        db.create_all()

def upload_csv_to_db(dataframe):
    with app.app_context():
        for _, row in dataframe.iterrows():
            product = Product(name=row['name'], category=row['category'],
                                price=row['price'], quantity_sold=row['quantity_sold'],
                                rating=row['rating'])
            db.session.add(product)
        db.session.commit()

def sanitze_data(file):
    df = pd.read_csv(file)
        
        # Clean data
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df['quantity_sold'] = pd.to_numeric(df['quantity_sold'], errors='coerce')
    df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
        
        # Handle missing values
    df['price'].fillna(df['price'].median(), inplace=True)
    df['quantity_sold'].fillna(df['quantity_sold'].median(), inplace=True)
        
        # For rating, fill missing values with the average rating in that category
    df['rating'] = df.groupby('category')['rating'].transform(lambda x: x.fillna(x.mean()))

    return df

# JWT Authentication
def generate_token(username):
    payload = {
        'sub': username,
        'exp': datetime.now(timezone.utc) + timedelta(hours=1)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'User already exists'}), 400
    
    new_user = User(username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'message': 'User created successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    if user and bcrypt.check_password_hash(user.password, password):
        token = generate_token(username)
        return jsonify({'token': token}), 200
    
    return jsonify({'message': 'Invalid credentials'}), 401

# Home Page for CSV Upload
@app.route('/', methods=['GET'])
def home():
    return render_template('home.html')

# Summary Page
@app.route('/summary', methods=['GET', 'POST'])
def summary():
    if request.method == 'GET':
        with app.app_context():
            # Use all data in the database
            dataframe = pd.read_sql_table('product', con=db.engine)
            
            return render_template('summary.html', table_html=summarize(dataframe))
                

    if 'file' not in request.files:
        app.logger.error('File not found')
        return redirect(url_for('home'))
    file = request.files['file']
    if file.filename == '':
        app.logger.error('File name invalid')
        return redirect(request.url)
    if not file or not file.filename.endswith('.csv'):
        app.logger.error(f'Invalid file {file.filename}')
        return render_template('home.html')
    action = request.form.get('action')
        
    try:
        if action == 'upload_csv':
            dataframe = sanitze_data(file)
            upload_csv_to_db(dataframe)
            app.logger.info("csv upload successful")

            return 'CSV upload successful!'
        
        dataframe = sanitze_data(file)            
        
        return render_template('summary.html', table_html=summarize(dataframe))
    except Exception as e:
        return f"An error occurred: {e}"

def summarize(dataframe):
    summary = dataframe.groupby('category').agg(
            total_revenue=pd.NamedAgg(column='price', aggfunc='sum'),
            top_product=pd.NamedAgg(column='name', aggfunc=lambda x: x.value_counts().idxmax()),
            top_product_quantity_sold=pd.NamedAgg(column='quantity_sold', aggfunc='max')
        ).reset_index()

    table_html = summary.to_html(classes='table table-striped', index=False)
    return table_html

# Initialize and run the application
if __name__ == '__main__':
    init_db()
    app.run(debug=True)