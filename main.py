from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests

app = FastAPI()

# ✅ Allow WordPress domain to access this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://testingmarmorkrafts.store"],  # ✅ Your WordPress site
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ WooCommerce API credentials (only needed on server-side)
WC_API_URL = "https://testingmarmorkrafts.store/wp-json/wc/v3"
WC_CONSUMER_KEY = "ck_fb05462837d9679c0f6c8b11ccbac57d09c79638"
WC_CONSUMER_SECRET = "cs_cd485ed45fc41da284d567e0d49cb8a272fbe4f1"

@app.get("/categories")
def get_categories():
    url = f"{WC_API_URL}/products/categories?per_page=100"
    response = requests.get(url, auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET))

    if response.status_code != 200:
        return JSONResponse(status_code=response.status_code, content={"error": "Failed to fetch categories"})

    data = response.json()
    result = {
        "@context": "https://schema.org",
        "@type": "Collection",
        "name": "Product Categories",
        "members": []
    }

    for cat in data:
        if cat.get("count", 0) > 0:
            result["members"].append({
                "@type": "ProductCategory",
                "name": cat["name"],
                "url": f"https://testingmarmorkrafts.store/product-category/{cat['slug']}/",
                "image": {
                    "@type": "ImageObject",
                    "url": cat.get("image", {}).get("src", "")
                },
                "description": cat.get("description", "")
            })

    return JSONResponse(content=result)


@app.get("/products")
def get_products(query: str = ""):
    url = f"{WC_API_URL}/products?search={query}&per_page=10"
    response = requests.get(url, auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET))

    if response.status_code != 200:
        return JSONResponse(status_code=response.status_code, content={"error": "Failed to fetch products"})

    data = response.json()
    result = {
        "@context": "https://schema.org",
        "@type": "Collection",
        "name": "Products",
        "members": []
    }

    for prod in data:
        result["members"].append({
            "@type": "Product",
            "name": prod["name"],
            "url": prod["permalink"],
            "image": {
                "@type": "ImageObject",
                "url": prod["images"][0]["src"] if prod.get("images") else ""
            },
            "price": prod.get("price"),
            "description": prod.get("short_description", "")
        })

    return JSONResponse(content=result)


@app.get("/products/on-sale")
def get_on_sale_products():
    url = f"{WC_API_URL}/products?per_page=100&orderby=modified&order=desc"
    response = requests.get(url, auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET))

    if response.status_code != 200:
        return JSONResponse(status_code=response.status_code, content={"error": "Failed to fetch products"})

    all_products = response.json()
    sale_products = [p for p in all_products if p.get("on_sale") is True]

    result = {
        "@context": "https://schema.org",
        "@type": "Collection",
        "name": "On Sale Products",
        "members": []
    }

    for item in sale_products:
        result["members"].append({
            "@type": "Product",
            "name": item["name"],
            "url": item["permalink"],
            "image": {
                "@type": "ImageObject",
                "url": item["images"][0]["src"] if item.get("images") else ""
            },
            "price": item.get("price"),
            "description": item.get("short_description", "")
        })

    return JSONResponse(content=result)


@app.get("/order-status/{order_id}")
def get_order_status(order_id: int):
    url = f"{WC_API_URL}/orders/{order_id}"
    response = requests.get(url, auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET))

    if response.status_code != 200:
        return JSONResponse(status_code=response.status_code, content={"error": "Failed to fetch order details"})

    order_data = response.json()
    tracking_number = "Not available"

    for meta in order_data.get("meta_data", []):
        if meta.get("key") == "_wc_shipment_tracking_items":
            tracking_items = meta.get("value", [])
            if tracking_items:
                tracking_number = tracking_items[0].get("tracking_number", "Not available")
            break

    result = {
        "@context": "https://schema.org",
        "@type": "Order",
        "order_number": order_data["number"],
        "status": order_data["status"],
        "currency": order_data["currency"],
        "total": order_data["total"],
        "shipping_method": order_data["shipping_lines"][0]["method_title"] if order_data.get("shipping_lines") else "N/A",
        "billing_address": order_data["billing"],
        "shipping_address": order_data["shipping"],
        "tracking_number": tracking_number,
        "order_date": order_data["date_created"],
        "line_items": [
            {
                "name": item["name"],
                "quantity": item["quantity"],
                "price": item["price"]
            } for item in order_data.get("line_items", [])
        ]
    }

    return JSONResponse(content=result)
