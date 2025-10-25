from fastapi.testclient import TestClient


def test_catalog_inventory_order_flow(client: TestClient) -> None:
    # create store
    store_payload = {"store_id": "S001", "name": "Main Store", "region": "East"}
    response = client.post("/api/v1/stores", json=store_payload)
    assert response.status_code == 201, response.text

    # create SKU with barcodes and prices
    sku_payload = {
        "sku_id": "SKU001",
        "name": "Bottled Water",
        "brand": "Fresh",
        "category": "Beverages",
        "tax_rate": 0.13,
        "barcodes": [{"code": "6900000000017", "package_size": "500ml"}],
        "prices": [
            {
                "store_id": "S001",
                "price": 3.5,
                "member_price": 3.2,
            }
        ],
    }
    response = client.post("/api/v1/catalog/skus", json=sku_payload)
    assert response.status_code == 201, response.text
    sku_data = response.json()
    assert sku_data["sku_id"] == "SKU001"
    assert sku_data["barcodes"][0]["code"] == "6900000000017"

    # inbound stock
    move_payload = {
        "store_id": "S001",
        "sku_id": "SKU001",
        "qty_delta": 100,
        "reason": "purchase",
    }
    response = client.post("/api/v1/inventory/moves", json=move_payload)
    assert response.status_code == 201, response.text

    # verify stock balance
    response = client.get("/api/v1/inventory/stock", params={"store_id": "S001"})
    assert response.status_code == 200
    balances = response.json()
    assert balances[0]["on_hand"] == 100

    # create member
    member_payload = {"member_id": "M001", "phone": "13800000000"}
    response = client.post("/api/v1/members", json=member_payload)
    assert response.status_code == 201

    # create order which deducts stock
    order_payload = {
        "order_id": "O001",
        "store_id": "S001",
        "channel": "POS",
        "status": "PAID",
        "member_id": "M001",
        "total": 7.0,
        "tax_total": 0.91,
        "items": [
            {"sku_id": "SKU001", "qty": 2, "price": 3.5, "tax_rate": 0.13}
        ],
    }
    response = client.post("/api/v1/orders", json=order_payload)
    assert response.status_code == 201, response.text

    # order detail includes items
    order_data = response.json()
    assert order_data["order_id"] == "O001"
    assert order_data["items"][0]["qty"] == 2

    # stock decreased by order quantity
    response = client.get("/api/v1/inventory/stock", params={"store_id": "S001"})
    assert response.status_code == 200
    balances = response.json()
    assert balances[0]["on_hand"] == 98

    # update promotion
    promo_payload = {
        "promotion_id": "P001",
        "name": "Spring Sale",
        "promotion_type": "discount",
        "store_scope": "S001",
        "payload": "{\"discount\":0.9}",
    }
    response = client.post("/api/v1/promotions", json=promo_payload)
    assert response.status_code == 201

    response = client.patch("/api/v1/promotions/P001", json={"name": "Spring Mega Sale"})
    assert response.status_code == 200
    assert response.json()["name"] == "Spring Mega Sale"
