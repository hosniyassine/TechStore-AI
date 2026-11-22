import pytest
import crud


def test_get_all_products():
    prods = crud.get_all_products()
    assert len(prods) >= 15
    for p in prods:
        assert "id" in p
        assert "name" in p
        assert "price" in p
        assert "stock" in p


def test_filter_products_by_category():
    smartphones = crud.get_all_products(category="Smartphones")
    assert len(smartphones) > 0
    assert all(p["category"] == "Smartphones" for p in smartphones)


def test_search_products():
    res = crud.get_all_products(search="Galaxy")
    assert any("Galaxy" in p["name"] for p in res)


def test_crud_product_lifecycle():
    # 1. Création
    nouveau = {
        "id": "P999",
        "name": "Appareil Test CRUD",
        "brand": "MarqueTest",
        "category": "Smartphones",
        "price": 499.99,
        "description": "Description produit pour test unitaire CRUD",
        "ram": "8 Go",
        "storage": "128 Go",
        "stock": 10
    }
    cree = crud.create_product(nouveau)
    assert cree["id"] == "P999"
    assert cree["price"] == 499.99

    # 2. Lecture
    recupere = crud.get_product_by_id("P999")
    assert recupere is not None
    assert recupere["name"] == "Appareil Test CRUD"

    # 3. Modification
    modifie = crud.update_product("P999", {"price": 449.99, "stock": 15})
    assert modifie["price"] == 449.99
    assert modifie["stock"] == 15

    # 4. Suppression
    supprime = crud.delete_product("P999")
    assert supprime is True
    assert crud.get_product_by_id("P999") is None


def test_order_creation_without_confirmation():
    # Règle absolue du Guide : aucune commande sans confirmation explicite
    res = crud.create_order("P001", quantity=1, confirmed=False)
    assert res["statut"] == "confirmation_requise"
    assert "Confirmation requise" in res["message"]


def test_order_creation_with_confirmation_and_stock_update():
    p_initial = crud.get_product_by_id("P001")
    stock_initial = p_initial["stock"]

    # Commande confirmée
    res = crud.create_order("P001", quantity=1, confirmed=True)
    assert res["statut"] == "succes"
    assert "commande" in res
    assert res["nouveau_stock"] == stock_initial - 1

    # Vérification du stock en base
    p_apres = crud.get_product_by_id("P001")
    assert p_apres["stock"] == stock_initial - 1

    # Restauration du stock pour les tests suivants
    crud.update_product("P001", {"stock": stock_initial})


def test_order_insufficient_stock():
    # Tentative de commande au-delà du stock
    p = crud.get_product_by_id("P001")
    res = crud.create_order("P001", quantity=p["stock"] + 1000, confirmed=True)
    assert res["statut"] == "erreur"
    assert "Stock insuffisant" in res["message"]
