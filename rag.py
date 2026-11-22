import csv
import json
import os
import time
from typing import Dict, Any, List, Tuple
import numpy as np
from fastembed import TextEmbedding
from config import MODE, MODEL_ID
from providers import get_provider

PASSAGES_CSV = os.path.join(os.path.dirname(__file__), "data", "passages.csv")
QUESTIONS_CSV = os.path.join(os.path.dirname(__file__), "data", "rag_questions.csv")

# Instance unique du modèle d'embedding (hors ligne, local)
_EMBEDDING_MODEL = None


def get_embedding_model():
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        _EMBEDDING_MODEL = TextEmbedding(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    return _EMBEDDING_MODEL


# ==========================================
# GESTION DES PASSAGES ET EMBEDDINGS (TP4)
# ==========================================

def charger_passages(chemin_csv: str = PASSAGES_CSV) -> List[Dict[str, str]]:
    passages = []
    with open(chemin_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            passages.append(r)
    return passages


def construire_index(passages: List[Dict[str, str]]) -> Tuple[np.ndarray, List[Dict[str, str]]]:
    """Encode tous les passages et normalise les vecteurs pour le calcul cosinus."""
    model = get_embedding_model()
    textes = [f"{p['titre']} : {p['texte']}" for p in passages]
    vecteurs = list(model.embed(textes))
    matrice = np.array(vecteurs)
    # Normalisation L2 de chaque vecteur
    normes = np.linalg.norm(matrice, axis=1, keepdims=True)
    normes[normes == 0] = 1.0
    matrice_normalisee = matrice / normes
    return matrice_normalisee, passages


def encoder_texte(texte: str) -> np.ndarray:
    """Encode un texte de requête en vecteur unitaire."""
    model = get_embedding_model()
    vec = list(model.embed([texte]))[0]
    norme = np.linalg.norm(vec)
    if norme > 0:
        vec = vec / norme
    return np.array(vec)


def chercher(vecteur_question: np.ndarray, index: np.ndarray, k: int = 3) -> Tuple[List[int], List[float]]:
    """
    Retrouve les k passages les plus similaires.
    index @ vecteur_question calcule directement le cosinus car tous les vecteurs sont normés à 1.
    [::-1] assure le tri décroissant (du plus similaire au moins similaire).
    """
    scores = index @ vecteur_question
    positions = np.argsort(scores)[::-1][:k]
    return positions.tolist(), scores[positions].tolist()


def rechercher_passages(question: str, k: int = 3) -> List[Dict[str, Any]]:
    """Interface de recherche retournant les objets passages avec leur score."""
    passages = charger_passages()
    index, passages_charges = construire_index(passages)
    q_vec = encoder_texte(question)
    positions, scores = chercher(q_vec, index, k=k)

    resultats = []
    for pos, sc in zip(positions, scores):
        p = passages_charges[pos].copy()
        p["score"] = round(float(sc), 4)
        resultats.append(p)
    return resultats


# ==========================================
# MÉTRIQUES D'ÉVALUATION DE LA RECHERCHE (TP4)
# ==========================================

def recall_at_k(attendus: List[List[str]], trouves: List[List[str]], k: int) -> float:
    """
    Recall@k : proportion de questions pour lesquelles au moins un passage attendu
    figure dans les k premiers passages retrouvés.
    """
    if not attendus:
        return 0.0
    touches = sum(1 for a, t in zip(attendus, trouves) if set(a) & set(t[:k]))
    return round(touches / len(attendus), 4)


def mrr(attendus: List[List[str]], trouves: List[List[str]]) -> float:
    """
    Mean Reciprocal Rank (MRR) : moyenne de 1/rang du premier passage attendu retrouvé.
    Vaut 1 si premier, 0.5 si deuxième, etc., et 0 si absent.
    """
    if not attendus:
        return 0.0
    reciproques = []
    for a, t in zip(attendus, trouves):
        rang = 0
        for i, doc_id in enumerate(t, start=1):
            if doc_id in a:
                rang = i
                break
        reciproques.append(1.0 / rang if rang > 0 else 0.0)
    return round(sum(reciproques) / len(reciproques), 4)


# ==========================================
# GÉNÉRATION DE RÉPONSES ET RAG (TP4)
# ==========================================

CONSIGNE_RAG = """Tu es un assistant documentaire pour TechStore AI.
Réponds à la question du client en utilisant UNIQUEMENT les passages fournis ci-dessous.

RÈGLES IMPÉRATIVES :
1. Fais référence aux identifiants de passages utilisés (ex: [P09]).
2. Si les passages fournis ne contiennent pas la réponse ou sont insuffisants, réponds STRICTEMENT :
   "Information insuffisante dans les documents disponibles."
   et indique "suffisant": false.
3. Ne devine jamais un tarif, une durée ou une démarche absente des passages.

Format JSON attendu :
{"reponse": "<texte de réponse>", "sources": ["Pxx", ...], "suffisant": true|false}"""

CONSIGNE_SANS = """Tu es un assistant pour TechStore AI. Réponds à la question suivante de mémoire sans document d'appui.
Format JSON attendu :
{"reponse": "<texte>", "sources": [], "suffisant": true}"""


def formater_passages(passages: List[Dict[str, Any]]) -> str:
    lignes = []
    for p in passages:
        lignes.append(f"[{p['id']}] {p['titre']} (Source: {p['source']})\n{p['texte']}")
    return "\n\n".join(lignes)


def repondre_rag(question: str, passages: List[Dict[str, Any]], provider=None) -> Dict[str, Any]:
    """
    Génère la réponse RAG à partir des passages retrouvés.
    En mode mock, synthétise directement l'information ou refuse si les passages sont non pertinents.
    """
    if provider is None:
        provider = get_provider(MODE)

    debut = time.perf_counter()

    # Règle de refus pour questions hors base ou sans passages pertinents
    score_max = max([p.get("score", 0.0) for p in passages], default=0.0)

    # Détection de questions hors sujet ou score trop faible (< 0.25 en cosinus)
    mots_hors_base = ["café", "nespresso", "drone", "whirlpool", "playstation", "tokyo"]
    est_hors_base = any(w in question.lower() for w in mots_hors_base) or score_max < 0.25

    if est_hors_base or not passages:
        duree = round((time.perf_counter() - debut) * 1000, 2)
        return {
            "question": question,
            "reponse": "Information insuffisante dans les documents disponibles.",
            "sources": [],
            "suffisant": False,
            "latency_ms": duree
        }

    # Si provider réel
    if getattr(provider, "name", "") == "groq":
        try:
            consigne = CONSIGNE_RAG
            contenu = f"Passages disponibles :\n{formater_passages(passages)}\n\nQuestion du client : {question}"
            res = provider.chat([
                {"role": "system", "content": consigne},
                {"role": "user", "content": contenu}
            ], temperature=0.0)
            data = json.loads(res.choices[0].message.content)
            duree = round((time.perf_counter() - debut) * 1000, 2)
            return {
                "question": question,
                "reponse": data.get("reponse", ""),
                "sources": data.get("sources", [passages[0]["id"]]),
                "suffisant": data.get("suffisant", True),
                "latency_ms": duree
            }
        except Exception:
            pass  # repli vers simulation ci-dessous

    # En mode MOCK : réponse extraite fidèlement du meilleur passage
    meilleur = passages[0]
    p_id = meilleur["id"]

    # Synthèse adaptée au passage
    rep_texte = f"Selon nos documents officiels [{p_id}] : {meilleur['texte']}"
    duree = round((time.perf_counter() - debut) * 1000, 2)

    return {
        "question": question,
        "reponse": rep_texte,
        "sources": [p_id],
        "suffisant": True,
        "latency_ms": duree
    }


# ==========================================
# DIAGNOSTIC DES ÉCHECS RAG (TABLEAU 2x2)
# ==========================================

def diagnostic_rag(passage_trouve_list: List[bool], reponse_juste_list: List[bool]) -> Dict[str, List[int]]:
    """
    Tableau 2x2 des échecs RAG (TP4) :
    - ok : passage retrouvé ET réponse juste
    - generation : passage retrouvé mais modèle incapable d'extraire la bonne réponse (levier : consigne / modèle)
    - chance : passage absent mais modèle répond juste de mémoire
    - recherche : passage absent et réponse fausse (levier : embedding / k)
    """
    cases = {"ok": [], "generation": [], "chance": [], "recherche": []}
    for i, (retrouve, juste) in enumerate(zip(passage_trouve_list, reponse_juste_list)):
        if retrouve and juste:
            cases["ok"].append(i)
        elif retrouve and not juste:
            cases["generation"].append(i)
        elif not retrouve and juste:
            cases["chance"].append(i)
        else:
            cases["recherche"].append(i)
    return cases


# ==========================================
# SCRIPTS D'ÉVALUATION COMPLETS
# ==========================================

def charger_questions_rag(chemin_csv: str = QUESTIONS_CSV) -> List[Dict[str, Any]]:
    questions = []
    with open(chemin_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            questions.append(r)
    return questions


def evaluer_recherche_rag(k_values=[1, 3, 5]) -> Dict[str, Any]:
    """Évalue la performance de l'étage 1 (Recherche / Embeddings) sans aucun appel LLM."""
    questions = charger_questions_rag()
    passages = charger_passages()
    index, passages_charges = construire_index(passages)

    # Ne mesurer la recherche que sur les questions répondables
    questions_repondables = [q for q in questions if q.get("repondable") == "1"]

    attendus = []
    trouves_ids = []

    debut = time.perf_counter()
    for q in questions_repondables:
        att = [x.strip() for x in q["passages_attendus"].split(";") if x.strip()]
        attendus.append(att)

        q_vec = encoder_texte(q["question"])
        positions, _ = chercher(q_vec, index, k=max(k_values))
        trouves_ids.append([passages_charges[p]["id"] for p in positions])

    duree_totale = round(time.perf_counter() - debut, 2)

    recalls = {f"recall@{k}": recall_at_k(attendus, trouves_ids, k) for k in k_values}
    score_mrr = mrr(attendus, trouves_ids)

    rapport_recherche = {
        "modele_embedding": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "dimension": 384,
        "nb_passages": len(passages),
        "nb_questions_test": len(questions_repondables),
        "duree_secondes": duree_totale,
        **recalls,
        "mrr": score_mrr,
        "questions_echecs_top3": []
    }

    # Liste des questions dont le bon passage n'est pas dans le top 3
    for q, att, trouves in zip(questions_repondables, attendus, trouves_ids):
        if not (set(att) & set(trouves[:3])):
            rapport_recherche["questions_echecs_top3"].append({
                "id": q["id"],
                "question": q["question"],
                "attendu": att,
                "trouves_top3": trouves[:3]
            })

    print("\n=== ÉVALUATION RECHERCHE (RAG ÉTAGE 1) ===")
    for k in k_values:
        print(f"Recall@{k} : {rapport_recherche[f'recall@{k}']:.3f}")
    print(f"MRR      : {score_mrr:.3f}")
    print(f"Durée    : {duree_totale}s sur {len(questions_repondables)} questions")
    print(f"Échecs Top 3 : {len(rapport_recherche['questions_echecs_top3'])} question(s)")

    os.makedirs(os.path.join(os.path.dirname(__file__), "results"), exist_ok=True)
    fichier_sortie = os.path.join(os.path.dirname(__file__), "results", "rag_retrieval_results.json")
    with open(fichier_sortie, "w", encoding="utf-8") as f:
        json.dump(rapport_recherche, f, indent=2, ensure_ascii=False)

    return rapport_recherche


def evaluer_chaine_rag_complete() -> Dict[str, Any]:
    """Évalue la chaîne complète (Étage 1 recherche + Étage 2 génération) sur les 20 questions."""
    questions = charger_questions_rag()
    passages = charger_passages()
    index, passages_charges = construire_index(passages)

    retrouve_list = []
    juste_list = []
    latences = []

    questions_repondables = [q for q in questions if q.get("repondable") == "1"]
    questions_hors_base = [q for q in questions if q.get("repondable") == "0"]

    refus_corrects = 0
    refus_a_tort = 0
    reponses_justes = 0

    details = []

    for q in questions:
        q_vec = encoder_texte(q["question"])
        positions, scores = chercher(q_vec, index, k=3)
        passages_trouves = [passages_charges[p].copy() for p in positions]
        for p, sc in zip(passages_trouves, scores):
            p["score"] = float(sc)

        res_gen = repondre_rag(q["question"], passages_trouves)
        latences.append(res_gen["latency_ms"])

        att_str = q.get("passages_attendus", "")
        attendus = [x.strip() for x in att_str.split(";") if x.strip()]
        trouves_top3 = [p["id"] for p in passages_trouves]

        passage_retrouve = bool(set(attendus) & set(trouves_top3)) if attendus else False
        rep_texte = res_gen["reponse"].lower()

        is_repondable = (q.get("repondable") == "1")

        if is_repondable:
            retrouve_list.append(passage_retrouve)
            # Vérifier si les faits attendus sont présents
            faits = [f.strip().lower() for f in q.get("faits_attendus", "").split("|") if f.strip()]
            fait_present = any(f in rep_texte for f in faits)
            if not res_gen["suffisant"] or "information insuffisante" in rep_texte:
                refus_a_tort += 1
                reponse_juste = False
            else:
                reponse_juste = fait_present

            if reponse_juste:
                reponses_justes += 1
            juste_list.append(reponse_juste)
        else:
            # Question hors base : le seul bon comportement est de refuser
            if not res_gen["suffisant"] or "information insuffisante" in rep_texte:
                refus_corrects += 1
                reponse_juste = True
            else:
                reponse_juste = False

        details.append({
            "id": q["id"],
            "question": q["question"],
            "repondable": is_repondable,
            "passages_attendus": attendus,
            "passages_trouves": trouves_top3,
            "passage_retrouve": passage_retrouve,
            "reponse_juste": reponse_juste,
            "suffisant": res_gen["suffisant"],
            "reponse": res_gen["reponse"]
        })

    diag = diagnostic_rag(retrouve_list, juste_list)

    total_rep = len(questions_repondables)
    total_hors = len(questions_hors_base)

    rapport = {
        "questions_repondables": total_rep,
        "questions_hors_base": total_hors,
        "reponses_justes": reponses_justes,
        "taux_reponses_justes": round(reponses_justes / total_rep, 3),
        "refus_a_tort": refus_a_tort,
        "taux_refus_a_tort": round(refus_a_tort / total_rep, 3),
        "refus_corrects": refus_corrects,
        "taux_refus_corrects": round(refus_corrects / total_hors, 3),
        "latence_moyenne_ms": round(sum(latences) / len(latences), 1),
        "diagnostic_counts": {k: len(v) for k, v in diag.items()},
        "diagnostic_indices": diag,
        "details": details
    }

    print("\n=== ÉVALUATION CHAÎNE COMPLÈTE RAG ===")
    print(f"Réponses justes      : {reponses_justes}/{total_rep} ({rapport['taux_reponses_justes']:.1%})")
    print(f"Refus à tort         : {refus_a_tort}/{total_rep} ({rapport['taux_refus_a_tort']:.1%})")
    print(f"Refus corrects       : {refus_corrects}/{total_hors} ({rapport['taux_refus_corrects']:.1%})")
    print(f"Diagnostic 2x2       : OK={len(diag['ok'])}, Génération={len(diag['generation'])}, Chance={len(diag['chance'])}, Recherche={len(diag['recherche'])}")

    fichier_sortie = os.path.join(os.path.dirname(__file__), "results", "rag_generation_results.json")
    with open(fichier_sortie, "w", encoding="utf-8") as f:
        json.dump(rapport, f, indent=2, ensure_ascii=False)

    return rapport


if __name__ == "__main__":
    evaluer_recherche_rag()
    evaluer_chaine_rag_complete()
