import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

PRODUCTS_FILE = os.path.join(os.path.dirname(__file__), "data", "products.json")
ORDERS_FILE = os.path.join(os.path.dirname(__file__), "data", "orders.json")

CATEGORIES_AUTORISEES = [
    "Smartphones",
    "Ordinateurs portables",
    "Tablettes",
    "Casques et écouteurs",
    "Accessoires électroniques",
]


def _charger_json(fichier: str) -> List[Dict[str, Any]]:
    if not os.path.exists(fichier):
        return []
    with open(fichier, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _sauvegarder_json(fichier: str, donnees: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(fichier), exist_ok=True)
    with open(fichier, "w", encoding="utf-8") as f:
        json.dump(donnees, f, indent=2, ensure_ascii=False)


# ==========================================
# GESTION DES PRODUITS (CRUD)
# ==========================================

def get_all_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    max_price: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Récupère tous les produits avec filtres optionnels."""
    produits = _charger_json(PRODUCTS_FILE)
    resultats = produits

    if category:
        cat_lower = category.lower().strip()
        resultats = [p for p in resultats if p.get("category", "").lower() == cat_lower]

    if search:
        s_lower = search.lower().strip()
        mots_ignores = {
            "cherche", "recherche", "trouve", "trouver", "avec", "pour", "dans", "plus",
            "euros", "euro", "smartphone", "smartphones", "ordinateur", "ordinateurs",
            "laptop", "laptops", "casque", "casques", "tablette", "tablettes", "appareil",
            "appareils", "quel", "quels", "quelle", "quelles", "avez", "vous", "avez-vous",
            "liste", "tous", "vos", "montre", "montrez", "disponible", "disponibles", "prix",
            "combien", "coute", "coûte", "cout", "tarif", "proposez", "vendez", "magasin",
            "boutique", "rayon", "catalogue", "notre", "votre", "proposez-vous", "avez-vous"
        }
        import re
        mots_cles = [re.sub(r"[^\w]", "", m) for m in s_lower.split() if len(re.sub(r"[^\w]", "", m)) > 2 and re.sub(r"[^\w]", "", m) not in mots_ignores]

        def match_produit(p):
            # Si une catégorie est déjà filtrée et qu'il n'y a pas d'autres mots-clés spécifiques (ex: "Quels smartphones avez-vous ?")
            if category and not mots_cles:
                return True
            texte_p = f"{p.get('name', '')} {p.get('brand', '')} {p.get('description', '')}".lower()
            if s_lower in texte_p:
                return True
            if mots_cles and any(m in texte_p for m in mots_cles):
                return True
            return False

        resultats = [p for p in resultats if match_produit(p)]

    if max_price is not None:
        resultats = [p for p in resultats if float(p.get("price", 0)) <= max_price]

    return resultats


def get_product_by_id(product_id: str) -> Optional[Dict[str, Any]]:
    """Consulte un produit par son identifiant unique."""
    produits = _charger_json(PRODUCTS_FILE)
    pid_clean = product_id.strip().upper()
    for p in produits:
        if p.get("id", "").upper() == pid_clean:
            return p
    return None


def create_product(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ajoute un nouveau produit avec validation des champs."""
    produits = _charger_json(PRODUCTS_FILE)

    # Génération d'un nouvel identifiant si absent
    if not data.get("id"):
        max_id = 0
        for p in produits:
            id_val = p.get("id", "")
            if id_val.startswith("P") and id_val[1:].isdigit():
                max_id = max(max_id, int(id_val[1:]))
        nouveau_id = f"P{max_id + 1:03d}"
    else:
        nouveau_id = data["id"].strip().upper()
        if any(p.get("id", "").upper() == nouveau_id for p in produits):
            raise ValueError(f"Le produit avec l'identifiant {nouveau_id} existe déjà.")

    nouveau_produit = {
        "id": nouveau_id,
        "name": data.get("name", "").strip(),
        "brand": data.get("brand", "").strip(),
        "category": data.get("category", "").strip(),
        "price": float(data.get("price", 0.0)),
        "description": data.get("description", "").strip(),
        "ram": data.get("ram", "N/A").strip(),
        "storage": data.get("storage", "N/A").strip(),
        "stock": int(data.get("stock", 0)),
    }

    produits.append(nouveau_produit)
    _sauvegarder_json(PRODUCTS_FILE, produits)
    return nouveau_produit


def update_product(product_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Modifie un produit existant."""
    produits = _charger_json(PRODUCTS_FILE)
    pid_clean = product_id.strip().upper()
    index_trouve = None

    for i, p in enumerate(produits):
        if p.get("id", "").upper() == pid_clean:
            index_trouve = i
            break

    if index_trouve is None:
        return None

    # Mise à jour des champs autorisés
    p_existant = produits[index_trouve]
    champs = ["name", "brand", "category", "price", "description", "ram", "storage", "stock"]
    for c in champs:
        if c in data and data[c] is not None:
            if c == "price":
                p_existant[c] = float(data[c])
            elif c == "stock":
                p_existant[c] = int(data[c])
            else:
                p_existant[c] = str(data[c]).strip()

    produits[index_trouve] = p_existant
    _sauvegarder_json(PRODUCTS_FILE, produits)
    return p_existant


def delete_product(product_id: str) -> bool:
    """Supprime un produit par son identifiant."""
    produits = _charger_json(PRODUCTS_FILE)
    pid_clean = product_id.strip().upper()
    longueur_initiale = len(produits)
    produits_restants = [p for p in produits if p.get("id", "").upper() != pid_clean]

    if len(produits_restants) == longueur_initiale:
        return False

    _sauvegarder_json(PRODUCTS_FILE, produits_restants)
    return True


# ==========================================
# GESTION DES COMMANDES
# ==========================================

def get_all_orders() -> List[Dict[str, Any]]:
    """Récupère l'ensemble des commandes."""
    return _charger_json(ORDERS_FILE)


def get_order_by_id(order_id: str) -> Optional[Dict[str, Any]]:
    """Consulte une commande spécifique."""
    commandes = _charger_json(ORDERS_FILE)
    oid_clean = order_id.strip().upper()
    for cmd in commandes:
        if cmd.get("id", "").upper() == oid_clean:
            return cmd
    return None


def create_order(product_id: str, quantity: int, confirmed: bool = False) -> Dict[str, Any]:
    """
    Crée une commande simple.
    RÈGLE ABSOLUE DU GUIDE & TP5 :
    Une commande ne doit jamais être créée sans confirmation explicite du client.
    """
    produit = get_product_by_id(product_id)
    if not produit:
        return {
            "statut": "erreur",
            "message": f"Produit avec l'identifiant {product_id} introuvable."
        }

    if quantity <= 0:
        return {
            "statut": "erreur",
            "message": "La quantité commandée doit être strictement positive."
        }

    if produit["stock"] < quantity:
        return {
            "statut": "erreur",
            "message": f"Stock insuffisant pour {produit['name']}. Stock disponible: {produit['stock']}, demandé: {quantity}."
        }

    total_price = round(produit["price"] * quantity, 2)

    # Si confirmation non explicite, bloquer et renvoyer la demande de confirmation
    if not confirmed:
        return {
            "statut": "confirmation_requise",
            "action_requise": "confirmer_commande",
            "message": (
                f"Confirmation requise : Voulez-vous commander {quantity}x '{produit['name']}' "
                f"pour un montant total de {total_price:.2f} € ? Répondez 'OUI' pour confirmer."
            ),
            "product_id": produit["id"],
            "product_name": produit["name"],
            "quantity": quantity,
            "total_price": total_price
        }

    # Création effective après confirmation explicite
    commandes = _charger_json(ORDERS_FILE)
    max_id = 1000
    for cmd in commandes:
        cid = cmd.get("id", "")
        if cid.startswith("CMD-") and cid[4:].isdigit():
            max_id = max(max_id, int(cid[4:]))

    nouvelle_commande = {
        "id": f"CMD-{max_id + 1}",
        "product_id": produit["id"],
        "product_name": produit["name"],
        "quantity": quantity,
        "total_price": total_price,
        "status": "confirmee",
        "created_at": datetime.now().isoformat()
    }

    # Mise à jour du stock après confirmation
    nouveau_stock = produit["stock"] - quantity
    update_product(produit["id"], {"stock": nouveau_stock})

    commandes.append(nouvelle_commande)
    _sauvegarder_json(ORDERS_FILE, commandes)

    return {
        "statut": "succes",
        "message": f"Commande {nouvelle_commande['id']} créée et confirmée avec succès.",
        "commande": nouvelle_commande,
        "nouveau_stock": nouveau_stock
    }


def update_order_status(order_id: str, new_status: str) -> Optional[Dict[str, Any]]:
    """Modifie le statut d'une commande (ex: confirmee, annulee, livree)."""
    statuts_valides = ["en_attente", "confirmee", "annulee", "livree"]
    statut_clean = new_status.strip().lower()
    if statut_clean not in statuts_valides:
        raise ValueError(f"Statut invalide. Statuts valides : {', '.join(statuts_valides)}")

    commandes = _charger_json(ORDERS_FILE)
    oid_clean = order_id.strip().upper()
    cmd_trouvee = None

    for cmd in commandes:
        if cmd.get("id", "").upper() == oid_clean:
            ancien_statut = cmd.get("status")
            cmd["status"] = statut_clean
            cmd_trouvee = cmd

            # Si la commande est annulée, on restitue le stock
            if statut_clean == "annulee" and ancien_statut == "confirmee":
                produit = get_product_by_id(cmd["product_id"])
                if produit:
                    update_product(produit["id"], {"stock": produit["stock"] + cmd["quantity"]})
            break

    if cmd_trouvee:
        _sauvegarder_json(ORDERS_FILE, commandes)

    return cmd_trouvee
