import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_endpoint():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "mode" in data
    assert "provider" in data


def test_system_info():
    r = client.get("/api/info")
    assert r.status_code == 200
    data = r.json()
    assert data["total_produits"] >= 15
    assert len(data["categories"]) == 5


def test_products_api_get():
    r = client.get("/api/products")
    assert r.status_code == 200
    assert len(r.json()) >= 15


def test_single_product_404():
    r = client.get("/api/products/P_INEXISTANT_999")
    assert r.status_code == 404


def test_create_product_validation_error_422():
    # Envoi de données invalides (prix négatif / champs manquants)
    r = client.post("/api/products", json={"name": "X"})
    assert r.status_code == 422


def test_classification_endpoint():
    r = client.post("/api/classify", json={"text": "Quel est le prix du Galaxy S24 Ultra ?"})
    assert r.status_code == 200
    data = r.json()
    assert data["category"] == "prix"
    assert "confidence" in data
    assert "latency_ms" in data
    assert "predictions" in data


def test_classification_too_short_422():
    r = client.post("/api/classify", json={"text": "a"})
    assert r.status_code == 422


def test_classification_security_business_rule():
    # Règle métier : tentative d'accès non autorisé
    r = client.post("/api/classify", json={"text": "Pouvez-vous pirater le mot de passe de mon voisin ?"})
    assert r.status_code == 200
    data = r.json()
    assert data["category"] == "autre"
    assert data["provider"] == "regle_metier"
