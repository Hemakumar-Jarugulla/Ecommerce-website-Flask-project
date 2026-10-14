CREATE DATABASE eshop;
USE eshop;

CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    two_step_verification BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

select * from users;

CREATE TABLE products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    stock INT NOT NULL DEFAULT 0,
    image VARCHAR(255),
    rating DECIMAL(2,1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (price >= 0),
    CHECK (stock >= 0),
    CHECK (rating >= 0 AND rating <= 5)
);

CREATE TABLE IF NOT EXISTS addresses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    pincode VARCHAR(10) NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cart (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_cart_user_product (user_id, product_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    CHECK (quantity > 0)
);

CREATE TABLE IF NOT EXISTS favorites (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_favorites_user_product (user_id, product_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    address_id INT NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'PLACED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (address_id) REFERENCES addresses(id)
);

CREATE TABLE IF NOT EXISTS order_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS payments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL UNIQUE,
    payment_method VARCHAR(20) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    transaction_id VARCHAR(255),
    razorpay_order_id VARCHAR(255),
    paid_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

INSERT INTO products
(name, category, description, price, stock, image, rating)
VALUES
(
    'Wireless Headphones',
    'Electronics',
    'High-quality wireless headphones with excellent sound, comfortable design and long battery life.',
    2499.00,
    25,
    'headphones.jpg',
    4.8
),
(
    'Smart Watch',
    'Electronics',
    'Smart watch with fitness tracking, heart rate monitoring and multiple smart features.',
    3999.00,
    15,
    'smartwatch.jpg',
    4.7
),
(
    'Running Shoes',
    'Footwear',
    'Comfortable lightweight running shoes suitable for daily workouts and running.',
    2199.00,
    30,
    'running-shoes.jpg',
    4.6
),
(
    'Laptop Backpack',
    'Bags',
    'Durable laptop backpack with multiple compartments and water-resistant material.',
    1499.00,
    40,
    'backpack.jpg',
    4.5
),
(
    'Bluetooth Speaker',
    'Electronics',
    'Portable Bluetooth speaker with powerful audio and long battery backup.',
    1799.00,
    20,
    'speaker.jpg',
    4.4
),
(
    'Mechanical Keyboard',
    'Electronics',
    'RGB mechanical keyboard designed for gaming and professional use.',
    3299.00,
    18,
    'keyboard.jpg',
    4.7
),
(
    'Cotton T-Shirt',
    'Fashion',
    'Premium cotton regular-fit T-shirt suitable for everyday wear.',
    799.00,
    50,
    'tshirt.jpg',
    4.3
),
(
    'Denim Jeans',
    'Fashion',
    'Comfortable slim-fit denim jeans with premium stitching.',
    1899.00,
    35,
    'jeans.jpg',
    4.5
),
(
    'Sunglasses',
    'Fashion',
    'Stylish UV-protected sunglasses for everyday outdoor use.',
    999.00,
    25,
    'sunglasses.jpg',
    4.2
),
(
    'Water Bottle',
    'Accessories',
    'Stainless steel insulated water bottle with leak-proof design.',
    699.00,
    60,
    'water-bottle.jpg',
    4.4
);

select * from products;