from fastapi import FastAPI, Query
from typing import Optional
from datetime import datetime, timezone
import requests
from fastapi.responses import JSONResponse
# from fastapi.middleware.cors import CORSMiddleware
 
 
app = FastAPI()
 

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["https://testingmarmorkrafts.store"],  
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
# For DEv
# WC_API_URL = "https://testingmarmorkrafts.store/wp-json/wc/v3"
# WC_CONSUMER_KEY = "ck_fb05462837d9679c0f6c8b11ccbac57d09c79638"
# WC_CONSUMER_SECRET = "cs_cd485ed45fc41da284d567e0d49cb8a272fbe4f1"
 
# For Prod
WC_API_URL = "https://marmorkrafts.com/wp-json/wc/v3"
WC_CONSUMER_KEY = "ck_fb05462837d9679c0f6c8b11ccbac57d09c79638"
WC_CONSUMER_SECRET = "cs_cd485ed45fc41da284d567e0d49cb8a272fbe4f1"
 
@app.get("/categories")
def get_categories():
    url = f"{WC_API_URL}/products/categories?per_page=100"
    response = requests.get(url, auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET))
 
    if response.status_code != 200:
        return JSONResponse(
            status_code=response.status_code,
            content={"error": "Failed to fetch categories from WooCommerce."}
        )
 
    data = response.json()
 
    mcp_formatted = {
        "@context": "https://schema.org",
        "@type": "Collection",
        "name": "Product Categories",
        "members": []
    }
 
    for item in data:
        # ✅ Include only categories where count > 0
        if item.get("count", 0) > 0:
            mcp_formatted["members"].append({
                "@type": "ProductCategory",
                "name": item["name"],
                "url": f"https://testingmarmorkrafts.store/product-category/{item['slug']}/",
                "image": {
                    "@type": "ImageObject",
                    "url": item["image"]["src"] if item.get("image") else ""
                },
                "description": item.get("description", "")
            })
 
    return JSONResponse(content=mcp_formatted)
 
 
@app.get("/products")
def get_products(query: str = ""):
    url = f"{WC_API_URL}/products?search={query}&per_page=10"
    response = requests.get(url, auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET))
   
    if response.status_code != 200:
        return JSONResponse(
            status_code=response.status_code,
            content={"error": "Failed to fetch products"}
        )
 
    data = response.json()
 
    formatted = {
        "@context": "https://schema.org",
        "@type": "Collection",
        "name": "Products",
        "members": []
    }
 
    for item in data:
        formatted["members"].append({
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
 
    return formatted
 
 
@app.get("/products/on-sale")
def get_on_sale_products():
    url = f"{WC_API_URL}/products?per_page=100&orderby=modified&order=desc"
    response = requests.get(url, auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET))
 
    if response.status_code != 200:
        return JSONResponse(
            status_code=response.status_code,
            content={"error": "Failed to fetch products"}
        )
 
    all_products = response.json()
 
    # Filter for on_sale items only
    sale_products = [p for p in all_products if p.get("on_sale") is True]
 
    formatted = {
        "@context": "https://schema.org",
        "@type": "Collection",
        "name": "On Sale Products",
        "members": []
    }
 
    for item in sale_products:
        formatted["members"].append({
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
 
    return JSONResponse(content=formatted)
 
 
# === Smart unified endpoint ===
@app.get("/order-status/lookup/")
def lookup_order(input: str = Query(..., description="Order ID or Tracking Number")):
    if input.isdigit():
        if len(input) > 10:
            return fetch_order_by_tracking_number(input)
        else:
            return fetch_order_by_id(int(input))
    else:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid input format. Must be numeric tracking number or order ID."}
        )
 
# === Original direct endpoints (optional) ===
@app.get("/order-status/")
def get_order_status(order_id: Optional[int] = Query(None), tracking_number: Optional[str] = Query(None)):
    if order_id:
        return fetch_order_by_id(order_id)
    elif tracking_number:
        return fetch_order_by_tracking_number(tracking_number)
    else:
        return JSONResponse(
            status_code=400,
            content={"error": "Please provide either order_id or tracking_number"}
        )
 
# === Fetch by order ID ===
def fetch_order_by_id(order_id: int):
    url = f"{WC_API_URL}/orders/{order_id}"
    response = requests.get(url, auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET))
 
    if response.status_code == 404:
        return JSONResponse(
            status_code=200,
            content={
                "status": "not_found",
                "message": "No order found with the provided order ID."
            }
        )
 
    elif response.status_code != 200:
        return JSONResponse(
            status_code=response.status_code,
            content={"error": "Failed to fetch order details"}
        )
 
    return format_order_response(response.json())
 
# === Search by tracking number ===
def fetch_order_by_tracking_number(tracking_number: str):
    per_page = 20
    page = 1
    max_pages = 10  # Safety limit
 
    while page <= max_pages:
        url = f"{WC_API_URL}/orders?per_page={per_page}&page={page}"
        response = requests.get(url, auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET))
 
        if response.status_code != 200:
            return JSONResponse(
                status_code=response.status_code,
                content={"error": "Failed to fetch orders"}
            )
 
        orders = response.json()
        if not orders:
            break
 
        for order in orders:
            for meta in order.get("meta_data", []):
                if meta.get("key") == "_wc_shipment_tracking_items":
                    tracking_items = meta.get("value", [])
                    for item in tracking_items:
                        if item.get("tracking_number") == tracking_number:
                            return format_order_response(order)
 
        page += 1
 
    # return JSONResponse(
    #     status_code=404,
    #     content={"error": "No order found with the provided tracking number"}
    # )
 
    return JSONResponse(
        status_code=200,
        content={
            "status": "not_found",
            "message": "No order found with the provided tracking number."
        }
    )
# === Format WooCommerce order into JSON ===
def format_order_response(order_data):
    tracking_number = "Not available"
 
    for meta_item in order_data.get("meta_data", []):
        if meta_item.get("key") == "_wc_shipment_tracking_items":
            tracking_items = meta_item.get("value", [])
            if tracking_items:
                tracking_number = tracking_items[0].get("tracking_number", "Not available")
            break
 
    return JSONResponse(content={
        "@context": "https://schema.org",
        "@type": "Order",
        "order_number": order_data["number"],
        "status": order_data["status"],
        "currency": order_data["currency"],
        "total": order_data["total"],
        "shipping_method": order_data["shipping_lines"][0]["method_title"] if order_data["shipping_lines"] else "N/A",
        "billing_address": order_data["billing"],
        "shipping_address": order_data["shipping"],
        "tracking_number": tracking_number,
        "order_date": order_data["date_created"],
        "line_items": [
            {
                "name": item["name"],
                "quantity": item["quantity"],
                "price": item["price"],
                "sku": item.get("sku"),
                "image": item.get("image", {}).get("src")
            } for item in order_data["line_items"]
        ],
    })
 
 
def fetch_all_coupons():
    coupons = []
    page = 1
    while True:
        response = requests.get(
            f"{WC_API_URL}/coupons",
            params={
                "per_page": 100,
                "page": page
            },
            auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET)
        )
        if response.status_code != 200:
            break
        data = response.json()
        if not data:
            break
        coupons.extend(data)
        page += 1
    return coupons
 
def is_coupon_active(coupon):
    now = datetime.now(timezone.utc)
    # Check if status is published
    if coupon.get("status") != "publish":
        return False
    # Check start date if exists
    for meta in coupon.get("meta_data", []):
        if meta.get("key") == "_wt_coupon_start_date":
            start_date_str = meta.get("value")
            if start_date_str:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if now < start_date:
                    return False
    # Check expiry
    expires = coupon.get("date_expires_gmt")
    if expires:
        expiry_date = datetime.strptime(expires, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        if now > expiry_date:
            return False
    return True
 
@app.get("/promotions/active")
def get_active_promotions():
    coupons = fetch_all_coupons()
    active_coupons = [coupon for coupon in coupons if is_coupon_active(coupon)]
 
    promotions = []
    for coupon in active_coupons:
        promotions.append({
            "code": coupon["code"],
            "amount": f"{coupon['amount']}% off" if coupon['discount_type'] == "percent" else f"{coupon['amount']} off",
            "description": coupon.get("description", ""),
            "expires": coupon.get("date_expires_gmt")
        })
 
    if not promotions:
        return {"message": "There are currently no active promotions."}
   
    return {"active_promotions": promotions}