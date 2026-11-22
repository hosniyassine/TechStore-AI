from typing import List, Dict, Any

CATEGORIES = ["recherche", "prix", "comparaison", "stock", "garantie", "commande", "autre"]


def accuracy(vrais: List[str], predits: List[str]) -> float:
    """Calcule la proportion exacte de prédictions correctes."""
    if not vrais:
        return 0.0
    return sum(1 for v, p in zip(vrais, predits) if v == p) / len(vrais)


def scores_par_classe(vrais: List[str], predits: List[str], classes: List[str] = CATEGORIES) -> Dict[str, Dict[str, float]]:
    """
    Calcule précision, rappel et F1-score par classe.
    Gère explicitement la division par zéro (if vp+fp else 0.0).
    """
    resultat = {}
    for c in classes:
        vp = sum(1 for v, p in zip(vrais, predits) if v == c and p == c)
        fp = sum(1 for v, p in zip(vrais, predits) if v != c and p == c)
        fn = sum(1 for v, p in zip(vrais, predits) if v == c and p != c)

        precision = vp / (vp + fp) if (vp + fp) > 0 else 0.0
        recall = vp / (vp + fn) if (vp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        resultat[c] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": vp + fn,
            "vp": vp,
            "fp": fp,
            "fn": fn,
        }
    return resultat


def f1_macro(scores: Dict[str, Dict[str, float]]) -> float:
    """Moyenne non pondérée des F1-scores sur l'ensemble des classes."""
    if not scores:
        return 0.0
    f1_sum = sum(d["f1"] for d in scores.values())
    return round(f1_sum / len(scores), 4)


def taux_invalides(predits: List[str], classes: List[str] = CATEGORIES) -> float:
    """Mesure la proportion de sorties hors nomenclature ou mal formatées."""
    if not predits:
        return 0.0
    nb_invalides = sum(1 for p in predits if p not in classes)
    return round(nb_invalides / len(predits), 4)


def matrice_confusion(vrais: List[str], predits: List[str], classes: List[str] = CATEGORIES) -> Dict[str, Dict[str, int]]:
    """Génère la matrice de confusion croisant vérités terrain et prédictions."""
    matrice = {c: {c2: 0 for c2 in classes + ["invalide"]} for c in classes}
    for v, p in zip(vrais, predits):
        if v in matrice:
            col = p if p in classes else "invalide"
            matrice[v][col] += 1
    return matrice


def afficher_rapport(etiquette: str, vrais: List[str], predits: List[str], classes: List[str] = CATEGORIES) -> Dict[str, Any]:
    """Affiche et retourne le bilan d'évaluation complet au format des TP."""
    acc = round(accuracy(vrais, predits), 4)
    scores = scores_par_classe(vrais, predits, classes)
    macro_f1 = f1_macro(scores)
    invalides = taux_invalides(predits, classes)
    matrice = matrice_confusion(vrais, predits, classes)

    print(f"\n=== ÉVALUATION : {etiquette} ===")
    print(f"Accuracy  : {acc:.3f} ({sum(1 for v, p in zip(vrais, predits) if v == p)}/{len(vrais)})")
    print(f"Macro-F1  : {macro_f1:.3f}")
    print(f"Invalides : {invalides:.3f}")
    print(f"{'Catégorie':<15} {'Précision':<10} {'Rappel':<10} {'F1-score':<10} {'Support':<8}")
    print("-" * 55)
    for c in classes:
        sc = scores[c]
        print(f"{c:<15} {sc['precision']:<10.3f} {sc['recall']:<10.3f} {sc['f1']:<10.3f} {sc['support']:<8}")

    print("\nMatrice de confusion (Lignes = Vérité, Colonnes = Prédictions) :")
    en_tetes = " ".join(f"{c[:6]:>7}" for c in classes) + "  Inval"
    print(f"{'':<12} {en_tetes}")
    for c in classes:
        ligne_vals = " ".join(f"{matrice[c][c2]:>7}" for c2 in classes) + f" {matrice[c]['invalide']:>7}"
        print(f"{c[:10]:<12} {ligne_vals}")

    return {
        "etiquette": etiquette,
        "total_exemples": len(vrais),
        "bons_exemples": sum(1 for v, p in zip(vrais, predits) if v == p),
        "accuracy": acc,
        "macro_f1": macro_f1,
        "taux_invalides": invalides,
        "scores_par_classe": scores,
        "matrice_confusion": matrice
    }
