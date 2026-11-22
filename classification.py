import csv
import json
import os
import time
from typing import Dict, Any, List, Tuple
from config import MODE, REVIEW_THRESHOLD
from providers import get_provider, CATEGORIES
from schemas import Prediction
from evaluation import afficher_rapport

CONSIGNE_BASE = f"""Tu es un agent de tri pour TechStore AI, boutique de produits électroniques.
Classe la demande dans exactement une des catégories suivantes :
{', '.join(CATEGORIES)}.
- recherche : chercher un produit, catalogue, caractéristiques
- prix : questions sur les tarifs, remises, coûts
- comparaison : comparer deux ou plusieurs modèles
- stock : disponibilité d'un article
- garantie : SAV, panne, retour, remboursement, conditions de garantie
- commande : achat, passer commande, panier
- autre : hors sujet, salutations vagues, demandes non pertinentes

Réponds uniquement avec un objet JSON : {{"categorie": "<une_des_sept>", "confiance": <entre 0 et 1>}}."""

CONSIGNE_FEW_SHOT = CONSIGNE_BASE + """
Exemples :
"Avez-vous le Samsung S24 en magasin ?" -> {"categorie": "stock", "confiance": 0.95}
"Combien coûte l'iPad Pro 11 pouces ?" -> {"categorie": "prix", "confiance": 0.98}
"Je cherche un PC portable pour jouer" -> {"categorie": "recherche", "confiance": 0.92}
"Quelle différence entre iPhone 15 et Pixel 8 ?" -> {"categorie": "comparaison", "confiance": 0.95}
"Mon écran clignote, comment fonctionne le SAV ?" -> {"categorie": "garantie", "confiance": 0.94}
"Je valide l'achat du chargeur 67W" -> {"categorie": "commande", "confiance": 0.96}
"Donne-moi la météo à Marseille" -> {"categorie": "autre", "confiance": 0.99}
"""

MOTS_CLES_SECURITE_REFUS = [
    "pirater", "hack", "mot de passe de mon voisin", "coordonnées personnelles d'un autre client",
    "données personnelles", "coordonnees", "voler", "attaque"
]


def verifier_regle_metier_securite(texte: str) -> Tuple[bool, str]:
    """
    Règle métier stricte (Guide point 2) :
    Une règle de sécurité qui décide à la place du modèle en cas de tentative malveillante ou demande interdite.
    """
    texte_lower = texte.lower()
    for mot in MOTS_CLES_SECURITE_REFUS:
        if mot in texte_lower:
            return True, "Demande refusée pour des motifs de sécurité ou de confidentialité."
    return False, ""


def classer_demande(
    texte: str,
    consigne: str = CONSIGNE_BASE,
    provider=None
) -> Dict[str, Any]:
    """
    Exécute la classification d'un texte.
    Applique en priorité la règle métier, puis le provider (MOCK ou REAL),
    mesure la latence et applique le seuil de revue humaine.
    """
    if provider is None:
        provider = get_provider(MODE)

    debut = time.perf_counter()

    # 1. RÈGLE MÉTIER QUI DÉCIDE À LA PLACE DU MODÈLE
    refuse, raison = verifier_regle_metier_securite(texte)
    if refuse:
        duree = round((time.perf_counter() - debut) * 1000, 2)
        return {
            "categorie": "autre",
            "score": 1.0,
            "requires_review": False,
            "refuse": True,
            "motif_refus": raison,
            "latency_ms": duree,
            "provider": "regle_metier",
            "predictions": [Prediction(label="autre", score=1.0)]
        }

    # 2. APPEL DU FOURNISSEUR (MOCK OU REAL)
    try:
        predictions = provider.detect_category(texte, consigne=consigne)
    except TypeError:
        predictions = provider.detect_category(texte)
    except Exception:
        # En cas de panne du provider réel, repli sur MockProvider
        from providers import MockProvider
        provider = MockProvider()
        predictions = provider.detect_category(texte, consigne=consigne)

    duree = round((time.perf_counter() - debut) * 1000, 2)

    meilleur = max(predictions, key=lambda p: p.score) if predictions else Prediction(label="autre", score=0.5)
    categorie = meilleur.label if meilleur.label in CATEGORIES else "invalide"

    # 3. SEUIL DE REVUE HUMAINE (Guide point 3)
    requires_review = bool(meilleur.score < REVIEW_THRESHOLD)

    return {
        "categorie": categorie,
        "score": round(meilleur.score, 4),
        "requires_review": requires_review,
        "refuse": False,
        "motif_refus": None,
        "latency_ms": duree,
        "provider": getattr(provider, "name", "unknown"),
        "predictions": predictions
    }


def charger_dataset_classification(chemin_csv: str = None) -> List[Dict[str, str]]:
    if chemin_csv is None:
        chemin_csv = os.path.join(os.path.dirname(__file__), "data", "classification.csv")
    lignes = []
    with open(chemin_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lignes.append(row)
    return lignes


def evaluer_classifieur(
    consigne: str = CONSIGNE_BASE,
    etiquette: str = "Classifieur Standard",
    mode: str = "mock"
) -> Dict[str, Any]:
    """Évalue le classifieur sur le dataset annoté et retourne le rapport."""
    lignes = charger_dataset_classification()
    provider = get_provider(mode)
    vrais = []
    predits = []
    latences = []

    for ligne in lignes:
        res = classer_demande(ligne["texte"], consigne=consigne, provider=provider)
        vrais.append(ligne["categorie"])
        predits.append(res["categorie"])
        latences.append(res["latency_ms"])

    rapport = afficher_rapport(etiquette, vrais, predits, CATEGORIES)
    rapport["latence_min_ms"] = min(latences)
    rapport["latence_mediane_ms"] = sorted(latences)[len(latences) // 2]
    rapport["latence_max_ms"] = max(latences)

    # Sauvegarde du résultat
    os.makedirs(os.path.join(os.path.dirname(__file__), "results"), exist_ok=True)
    fichier_sortie = os.path.join(os.path.dirname(__file__), "results", f"{etiquette.replace(' ', '_').lower()}.json")
    with open(fichier_sortie, "w", encoding="utf-8") as f:
        json.dump(rapport, f, indent=2, ensure_ascii=False)

    return rapport


def comparer_variantes():
    """
    Compare deux variantes en ne changeant qu'une seule variable (consigne de base vs consigne few-shot),
    calcule l'écart exprimé en nombre d'exemples et en Macro-F1.
    """
    print("\n--- ÉVALUATION 1 : Consigne de base (Zero-shot) ---")
    res_base = evaluer_classifieur(CONSIGNE_BASE, "classification_zero_shot", mode="mock")

    print("\n--- ÉVALUATION 2 : Consigne avec exemples (Few-shot) ---")
    res_fewshot = evaluer_classifieur(CONSIGNE_FEW_SHOT, "classification_few_shot", mode="mock")

    ecart_exemples = res_fewshot["bons_exemples"] - res_base["bons_exemples"]
    ecart_macro_f1 = round(res_fewshot["macro_f1"] - res_base["macro_f1"], 4)

    bilan_comparaison = {
        "variable_modifiee": "consigne (zero-shot vs few-shot avec 7 exemples)",
        "variante_1": {
            "nom": "Zero-shot",
            "bons_exemples": res_base["bons_exemples"],
            "accuracy": res_base["accuracy"],
            "macro_f1": res_base["macro_f1"]
        },
        "variante_2": {
            "nom": "Few-shot",
            "bons_exemples": res_fewshot["bons_exemples"],
            "accuracy": res_fewshot["accuracy"],
            "macro_f1": res_fewshot["macro_f1"]
        },
        "ecart_en_exemples": ecart_exemples,
        "ecart_macro_f1": ecart_macro_f1,
        "total_exemples": res_base["total_exemples"],
        "conclusion": (
            f"L'ajout d'exemples dans la consigne donne un écart de {ecart_exemples} exemple(s) "
            f"({ecart_macro_f1:+.3f} de Macro-F1). "
            f"{'La variante few-shot est supérieure.' if ecart_exemples >= 1 else 'Pas de différence significative.'}"
        )
    }

    fichier_comp = os.path.join(os.path.dirname(__file__), "results", "classification_comparison.json")
    with open(fichier_comp, "w", encoding="utf-8") as f:
        json.dump(bilan_comparaison, f, indent=2, ensure_ascii=False)

    print("\n=== BILAN DE COMPARAISON (UNE SEULE VARIABLE) ===")
    print(f"Total exemples testés : {res_base['total_exemples']}")
    print(f"Bons exemples Zero-shot : {res_base['bons_exemples']}/{res_base['total_exemples']} (Macro-F1: {res_base['macro_f1']})")
    print(f"Bons exemples Few-shot  : {res_fewshot['bons_exemples']}/{res_fewshot['total_exemples']} (Macro-F1: {res_fewshot['macro_f1']})")
    print(f"Écart en nombre d'exemples : {ecart_exemples:+} exemple(s)")
    print(f"Écart en Macro-F1          : {ecart_macro_f1:+.4f}")
    print(f"Conclusion                 : {bilan_comparaison['conclusion']}")

    return bilan_comparaison


if __name__ == "__main__":
    comparer_variantes()
