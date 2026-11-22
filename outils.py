import json
from typing import Dict, Any, List, Optional
import crud


# ==========================================
# FONCTIONS PYTHON DES OUTILS
# ==========================================

def search_products(query: str = "", category: Optional[str] = None, max_price: Optional[float] = None) -> Dict[str, Any]:
    """Recherche des produits électroniques dans le catalogue."""
    try:
        prods = crud.get_all_products(category=category, search=query, max_price=max_price)
        resultats_simplifies = [
            {
                "id": p["id"],
                "name": p["name"],
                "brand": p["brand"],
                "category": p["category"],
                "price": p["price"],
                "stock": p["stock"],
                "ram": p["ram"],
                "storage": p["storage"]
            }
            for p in prods[:5]  # limiter aux 5 premiers pour économiser le contexte
        ]
        return {
            "nb_resultats": len(prods),
            "resultats": resultats_simplifies
        }
    except Exception as e:
        return {"erreur": f"Erreur lors de la recherche : {str(e)}"}


def compare_products(product_id_1: str, product_id_2: str) -> Dict[str, Any]:
    """Compare deux produits selon leurs caractéristiques techniques et prix."""
    p1 = crud.get_product_by_id(product_id_1)
    p2 = crud.get_product_by_id(product_id_2)

    if not p1:
        return {"erreur": f"Produit {product_id_1} introuvable."}
    if not p2:
        return {"erreur": f"Produit {product_id_2} introuvable."}

    diff_prix = round(abs(p1["price"] - p2["price"]), 2)
    plus_cher = p1["name"] if p1["price"] > p2["price"] else (p2["name"] if p2["price"] > p1["price"] else "Égaux")

    return {
        "comparaison": {
            "produit_1": {"id": p1["id"], "nom": p1["name"], "prix": p1["price"], "ram": p1["ram"], "stock": p1["stock"]},
            "produit_2": {"id": p2["id"], "nom": p2["name"], "prix": p2["price"], "ram": p2["ram"], "stock": p2["stock"]},
            "difference_prix": diff_prix,
            "plus_onereux": plus_cher
        }
    }


def check_stock(product_id: str) -> Dict[str, Any]:
    """Vérifie la disponibilité et le niveau de stock d'un produit."""
    p = crud.get_product_by_id(product_id)
    if not p:
        return {"erreur": f"Produit {product_id} introuvable."}
    return {
        "id": p["id"],
        "nom": p["name"],
        "stock": p["stock"],
        "disponible": p["stock"] > 0
    }


def create_order(product_id: str, quantity: int = 1, confirmed: bool = False) -> Dict[str, Any]:
    """
    Crée une commande client.
    ATTENTION : La commande N'EST CRÉÉE QUE SI confirmed=True.
    Si confirmed=False, renvoie une demande explicite de confirmation sans altérer la base.
    """
    return crud.create_order(product_id=product_id, quantity=quantity, confirmed=confirmed)


# ==========================================
# DISPATCHER D'EXÉCUTION DES OUTILS
# ==========================================

REGISTRE_OUTILS = {
    "search_products": search_products,
    "compare_products": compare_products,
    "check_stock": check_stock,
    "create_order": create_order,
}


def executer_outil(nom: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Exécute de manière sécurisée une fonction d'outil.
    Capture les erreurs d'arguments et de type pour éviter tout plantage du programme.
    """
    if nom not in REGISTRE_OUTILS:
        return {"erreur": f"Outil inconnu : '{nom}'."}

    fonction = REGISTRE_OUTILS[nom]
    try:
        if not isinstance(arguments, dict):
            arguments = {}
        return fonction(**arguments)
    except TypeError as te:
        return {"erreur": f"Arguments invalides pour '{nom}' : {str(te)}"}
    except Exception as exc:
        return {"erreur": f"Erreur d'exécution de '{nom}' : {str(exc)}"}


# ==========================================
# JSON SCHEMAS DES OUTILS (TP5)
# ==========================================

def schema(nom: str, description: str, proprietes: Dict[str, Any], requis: List[str]) -> Dict[str, Any]:
    """Construit la spécification JSON Schema au format standard OpenAI / Groq."""
    return {
        "type": "function",
        "function": {
            "name": nom,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": proprietes,
                "required": requis
            }
        }
    }


# SCHÉMAS PRÉCIS (Détaillés, conformes au protocole)
SCHEMA_SEARCH_PRECIS = schema(
    "search_products",
    "Recherche des produits électroniques dans le catalogue selon des mots-clés, une catégorie ou un budget maximum. À utiliser dès que l'utilisateur cherche un produit.",
    {
        "query": {"type": "string", "description": "Mots-clés de recherche (nom, marque ou type d'appareil)"},
        "category": {"type": "string", "description": "Catégorie : Smartphones, Ordinateurs portables, Tablettes, Casques et écouteurs, Accessoires électroniques"},
        "max_price": {"type": "number", "description": "Prix plafond en euros"}
    },
    ["query"]
)

SCHEMA_COMPARE_PRECIS = schema(
    "compare_products",
    "Compare les caractéristiques techniques et le prix entre deux produits du magasin. À utiliser quand le client hésite entre deux modèles.",
    {
        "product_id_1": {"type": "string", "description": "Identifiant du premier produit (ex: P001)"},
        "product_id_2": {"type": "string", "description": "Identifiant du second produit (ex: P002)"}
    },
    ["product_id_1", "product_id_2"]
)

SCHEMA_STOCK_PRECIS = schema(
    "check_stock",
    "Consulte le niveau de stock disponible pour un produit précis. À utiliser pour savoir si un article est en réserve ou épuisé.",
    {
        "product_id": {"type": "string", "description": "Identifiant du produit (ex: P001)"}
    },
    ["product_id"]
)

SCHEMA_ORDER_PRECIS = schema(
    "create_order",
    "Crée une commande client dans le système. ATTENTION : Ne passer confirmed=True UNIQUEMENT si le client a donné un accord explicite préalable (ex: 'oui je confirme', 'je valide la commande'). Sinon confirmed doit impérativement être false.",
    {
        "product_id": {"type": "string", "description": "Identifiant du produit à commander (ex: P001)"},
        "quantity": {"type": "integer", "minimum": 1, "description": "Quantité commandée"},
        "confirmed": {"type": "boolean", "description": "True UNIQUEMENT si confirmation explicite du client, False sinon"}
    },
    ["product_id", "quantity", "confirmed"]
)

SCHEMAS_PRECIS = [
    SCHEMA_SEARCH_PRECIS,
    SCHEMA_COMPARE_PRECIS,
    SCHEMA_STOCK_PRECIS,
    SCHEMA_ORDER_PRECIS,
]


# SCHÉMAS VAGUES (Pour la comparaison TP5 : même outils mais descriptions minimales)
SCHEMA_SEARCH_VAGUE = schema("search_products", "Rechercher", {"query": {"type": "string"}}, ["query"])
SCHEMA_COMPARE_VAGUE = schema("compare_products", "Comparer", {"product_id_1": {"type": "string"}, "product_id_2": {"type": "string"}}, ["product_id_1", "product_id_2"])
SCHEMA_STOCK_VAGUE = schema("check_stock", "Stock", {"product_id": {"type": "string"}}, ["product_id"])
SCHEMA_ORDER_VAGUE = schema("create_order", "Commander", {"product_id": {"type": "string"}, "quantity": {"type": "integer"}, "confirmed": {"type": "boolean"}}, ["product_id", "quantity", "confirmed"])

SCHEMAS_VAGUES = [
    SCHEMA_SEARCH_VAGUE,
    SCHEMA_COMPARE_VAGUE,
    SCHEMA_STOCK_VAGUE,
    SCHEMA_ORDER_VAGUE,
]
