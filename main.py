import uuid
from datetime import datetime

from fastapi import FastAPI, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from database import SessionLocal
from models.product import Product
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os

app = FastAPI()
app.mount("/invoices", StaticFiles(directory="invoices"), name="invoices")

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
    <td>
        <form method="post" action="/delete/{p.id}"
              onsubmit="return confirm('Are you sure you want to delete this product?');">
            <button style="background:red;color:white;padding:5px 10px;border:none;">
                Delete
            </button>
        </form>
    </td>
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
<a href="/logout" style="color:red;">🚪 Logout</a>

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

@app.post("/delete/{product_id}")
def delete_product(product_id: int):
    if not logged_in:
        return RedirectResponse("/login", status_code=303)

    db = get_db()
    product = db.query(Product).filter(Product.id == product_id).first()

    if product:
        db.delete(product)
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
    <a href="/logout" style="color:red;">🚪 Logout</a>

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
    
    bill_no = f"BILL-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

    product_name = product.name
    product_price = product.price

    product.qty -= sell_qty
    db.commit()
    db.close()

# --------------------
# CREATE PDF INVOICE
# --------------------
    if not os.path.exists("invoices"):
     os.makedirs("invoices")

    file_name = f"invoices/{bill_no}.pdf"
    c = canvas.Canvas(file_name, pagesize=A4)
    c.drawString(50, 800, "GST INVOICE")
    c.drawString(50, 780, f"Bill No: {bill_no}")
    c.drawString(50, 760, f"Date: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}")
    c.drawString(50, 770, f"Product: {product_name}")
    c.drawString(50, 750, f"Quantity: {sell_qty}")
    c.drawString(50, 730, f"Rate: ₹ {product_price}")
    c.drawString(50, 710, f"Subtotal: ₹ {total:.2f}")
    c.drawString(50, 690, f"GST (18%): ₹ {gst:.2f}")
    c.drawString(50, 670, f"Grand Total: ₹ {grand_total:.2f}")

    c.save()

    return f"""
    <p><b>Bill No:</b> {bill_no}</p>
<p><b>Date:</b> {datetime.now().strftime('%d-%m-%Y %I:%M %p')}</p>

    <h1>GST BILL</h1>
    <p>Product: {product_name}</p>
    <p>Quantity: {sell_qty}</p>
    <p>Rate: ₹ {product_price}</p>

    <p>Subtotal: ₹ {total:.2f}</p>
    <p>GST (18%): ₹ {gst:.2f}</p>

    <h2>Grand Total: ₹ {grand_total:.2f}</h2>
    <p>
    <a href="/invoices/{bill_no}.pdf" target="_blank">
    ⬇ Download Bill PDF
</a>

</p>

    <a href="/">⬅ Back to Inventory</a>
    """
@app.get("/logout")
def logout():
    global logged_in
    logged_in = False
    return RedirectResponse("/login", status_code=303)
