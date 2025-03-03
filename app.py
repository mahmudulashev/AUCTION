from flask import Flask, render_template, request, redirect, session
import sqlite3
import uuid
import datetime
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config["UPLOAD_FOLDER"] = "static/uploads"


# Home


@app.route("/")
def home():
    return render_template("index.html")


#Register


@app.route("/register", methods=["GET", "POST"])
def register():
    error = ''
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]

        ulanish = sqlite3.connect("users.db")
        cursor = ulanish.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            error = "Kechirasiz, bu username band."
        else:
            cursor.execute("INSERT INTO users (username, password, first_name, last_name) VALUES (?, ?, ?, ?)", 
                           (username, password, first_name, last_name))
            ulanish.commit()
            cursor.execute("SELECT id, username FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            session["user_id"] = user[0]
            session["username"] = user[1]
            return redirect("/products")
        
        ulanish.close()

    return render_template("register.html", error=error)


#Login


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ''  

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        ulanish = sqlite3.connect("users.db")
        cursor = ulanish.cursor()
        cursor.execute("SELECT id, username FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        ulanish.close()

        if user:
            session["user_id"] = user[0]
            session["username"] = user[1]
            return redirect("/products")
        else:
            error = "Login yoki parol noto‘g‘ri!"  

    return render_template("login.html", error=error)


#Logout


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("username", None)
    return redirect("/")


#Barcha Mahsulotlar


@app.route("/products", methods=["GET", "POST"])
def products():
    if "user_id" not in session:
        return redirect("/login")

    ulanish = sqlite3.connect("users.db")
    cursor = ulanish.cursor()

    if request.method == "POST":
        product_name = request.form["product_name"]
        price = float(request.form["price"])
        created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        image_path = None
        if "image" in request.files:
            image = request.files["image"]
            if image.filename:
                filename = f"{uuid.uuid4()}.jpg"
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                image.save(save_path)
                image_path = f"/static/uploads/{filename}"

        cursor.execute("INSERT INTO products (product_name, price, user_id, created_at, image_path) VALUES (?, ?, ?, ?, ?)", 
                       (product_name, price, session["user_id"], created_at, image_path))
        ulanish.commit()

    cursor.execute("""
        SELECT products.id, products.product_name, products.price, products.created_at, 
               users.username AS creator_name, products.image_path, products.user_id
        FROM products 
        JOIN users ON products.user_id = users.id
    """)
    products_list = cursor.fetchall()
    ulanish.close()

    return render_template("products.html", products=products_list, user_id=session["user_id"], username=session["username"])



#Har bir masulotni o'zini varag'i



@app.route("/product/<int:product_id>", methods=["GET", "POST"])
def product_page(product_id):
    if "user_id" not in session:
        return redirect("/login")

    ulanish = sqlite3.connect("users.db")
    cursor = ulanish.cursor()

    if request.method == "POST":
        offer_price = float(request.form["offer_price"])
        created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO offers (product_id, user_id, offer_price, created_at) VALUES (?, ?, ?, ?)", 
                       (product_id, session["user_id"], offer_price, created_at))
        ulanish.commit()

    cursor.execute("""
        SELECT products.id, products.product_name, products.price, products.created_at, 
               users.username AS creator_name, products.image_path 
        FROM products 
        JOIN users ON products.user_id = users.id
        WHERE products.id = ?
    """, (product_id,))
    
    product = cursor.fetchone()

    cursor.execute("""
        SELECT offers.offer_price, offers.created_at, users.username 
        FROM offers 
        JOIN users ON offers.user_id = users.id
        WHERE offers.product_id = ?
        ORDER BY offers.created_at DESC
    """, (product_id,))

    offers = cursor.fetchall()
    ulanish.close()

    if not product:
        return "Mahsulot topilmadi!"

    return render_template("product.html", product=product, offers=offers, user_id=session["user_id"])


#Mahsulotni O'chirish


@app.route("/delete_product/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    if "user_id" not in session:
        return redirect("/login")

    ulanish = sqlite3.connect("users.db")
    cursor = ulanish.cursor()

    cursor.execute("SELECT user_id FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()

    if product and product[0] == session["user_id"]:
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        ulanish.commit()

    ulanish.close()
    return redirect("/products")


# Akkount


@app.route("/account")
def account():
    if "user_id" not in session:
        return redirect("/login")

    ulanish = sqlite3.connect("users.db")
    cursor = ulanish.cursor()
    cursor.execute("SELECT first_name, last_name FROM users WHERE id = ?", 
                   (session["user_id"],))
    user_info = cursor.fetchone()
    cursor.execute("SELECT id, product_name, image_path FROM products WHERE user_id = ?", 
                   (session["user_id"],))
    user_products = cursor.fetchall()
    ulanish.close()

    return render_template(
        "account.html", 
        first_name=user_info[0] 
        if user_info 
        else "",  
        last_name=user_info[1] 
        if user_info 
        else "",  
        products=user_products
    )

# Search Bar

def qidiruv(query):
    ulanish = sqlite3.connect("users.db")
    cursor = ulanish.cursor()
    cursor.execute("""
        SELECT id, product_name, price, created_at, image_path 
        FROM products 
        WHERE product_name LIKE ? 
        OR price LIKE ?
    """, ('%' + query + '%', '%' + query + '%'))
    
    results = cursor.fetchall()
    ulanish.close()
    return results

@app.route("/search", methods=["GET"])
def search():
    if "user_id" not in session:
        return redirect("/login")

    query = request.args.get("q", "")
    results = qidiruv(query) if query else []
    
    return render_template("search.html", query=query, results=results, username=session["username"])



if __name__ == "__main__":
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])
    app.run(host="0.0.0.0", port=5000)