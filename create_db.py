from database import engine
from models.product import Product

Product.metadata.create_all(engine)
print("Database created successfully")
