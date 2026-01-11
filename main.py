from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from database import SessionLocal
from models.product import Product

app = FastAPI()

# --------------------
# SIMPLE LOGIN FLAG
# --------------------
logged_in = False


# --------------------
# DATABASE HELPER
# --------------------
def get_db():
    return SessionLocal()


# --------------------
# LOGIN ROUTES
# --------------------
@app.get("/login", response_class=HTMLResponse)
def login():
    return """
    <h2>Login</h2>
    <form method="post" action="/login">
        <input name="username" placeholder="Username" required><br><br>
        <input type="password" name="password" placeholder="Password" required><br><br>
        <button type="submit">Login</button>
    </form>
    """


@app.post("/login")
def login_post(username: str = Form(...), password: str = Form(...)):
    global logged_in
    if username == "admin" and password == "1234":
        logged_in = True
        return RedirectResponse("/", status_code=303)
    return "<h3 style='color:red;'>Invalid username or password</h3>"


# --------------------
# HOME / INVENTORY
# --------------------
@app.get("/", response_class=HTMLResponse)
def home():
    if not logged_in:
        return RedirectResponse("/login", status_code=303)

    db = get_db()
    products = db.query(Product).all()

    rows = ""
    for p in products:
        status = "In Stock" if p.qty > 0 else "OUT OF STOCK"
        rows += f"""
        <tr>
            <td>{p.name}</td>
            <td>{p.qty}</td>
            <td>₹ {p.price}</td>
            <td>{status}</td>
        </tr>
        """

    db.close()

    return f"""
    <h1>Warehouse Inventory</h1>

    <form method="post" action="/add">
        <input name="name" placeholder="Product Name" required>
        <input type="number" name="qty" min="0" placeholder="Quantity" required>
        <input type="number" step="0.01" name="price" placeholder="Price" required>
        <button>Add Product</button>
    </form>

    <h2>Products</h2>
    <table border="1" cellpadding="5">
        <tr><th>Name</th><th>Qty</th><th>Price</th><th>Status</th></tr>
        {rows}
    </table>

    <br>
    <a href="/billing">➡ Billing</a>
    """


# --------------------
# ADD PRODUCT
# --------------------
@app.post("/add")
def add_product(name: str = Form(...), qty: int = Form(...), price: float = Form(...)):
    if not logged_in:
        return RedirectResponse("/login", status_code=303)

    db = get_db()
    product = Product(name=name, qty=qty, price=price)
    db.add(product)
    db.commit()
    db.close()

    return RedirectResponse("/", status_code=303)


# --------------------
# BILLING PAGE
# --------------------
@app.get("/billing", response_class=HTMLResponse)
def billing():
    if not logged_in:
        return RedirectResponse("/login", status_code=303)

    db = get_db()
    products = db.query(Product).filter(Product.qty > 0).all()

    options = ""
    for p in products:
        options += f"<option value='{p.id}'>{p.name} (Stock: {p.qty})</option>"

    db.close()

    return f"""
    <h1>Billing</h1>

    <form method="post" action="/bill">
        <select name="product_id" required>
            <option value="">Select Product</option>
            {options}
        </select>

        <input type="number" name="sell_qty" min="1" required>
        <button>Generate Bill</button>
    </form>

    <br>
    <a href="/">⬅ Back</a>
    """


# --------------------
# GENERATE BILL
# --------------------
@app.post("/bill", response_class=HTMLResponse)
def generate_bill(product_id: int = Form(...), sell_qty: int = Form(...)):
    if not logged_in:
        return RedirectResponse("/login", status_code=303)

    db = get_db()
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        db.close()
        return "<h2>Product not found</h2>"

    if sell_qty > product.qty:
        available = product.qty
        db.close()
        return f"<h2 style='color:red;'>Insufficient Stock (Available: {available})</h2>"

    total = sell_qty * product.price
    gst = total * 0.18
    grand_total = total + gst

    product_name = product.name
    product_price = product.price

    product.qty -= sell_qty
    db.commit()
    db.close()

    return f"""
    <h1>GST BILL</h1>
    <p>Product: {product_name}</p>
    <p>Quantity: {sell_qty}</p>
    <p>Rate: ₹ {product_price}</p>

    <p>Subtotal: ₹ {total:.2f}</p>
    <p>GST (18%): ₹ {gst:.2f}</p>

    <h2>Grand Total: ₹ {grand_total:.2f}</h2>

    <a href="/">⬅ Back to Inventory</a>
    """
