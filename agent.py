import csv
import json
import os
import time
from typing import Dict, Any, List, Optional
from config import MODE, MODEL_ID
from providers import get_provider
from outils import executer_outil, SCHEMAS_PRECIS, SCHEMAS_VAGUES

CONSIGNE_AGENT = """Tu es l'assistant intelligent de TechStore AI, magasin spécialisé en électronique grand public.
Tu as accès à des outils pour assister les clients :
- search_products : pour chercher un produit selon mots-clés, catégorie ou prix max.
- compare_products : pour comparer techniquement et financièrement deux références (product_id_1, product_id_2).
- check_stock : pour vérifier la disponibilité exacte d'un produit (product_id).
- create_order : pour passer une commande.

RÈGLE DE SÉCURITÉ ABSOLUE (GESTION DES COMMANDES) :
Une commande N'EST JAMAIS créée sans la confirmation formelle et explicite du client (ex: "oui je confirme", "je valide mon achat").
Si le client demande à acheter ou commander mais n'a pas encore explicitement validé, tu DOIS appeler create_order avec confirmed=False afin d'obtenir le montant et demander sa confirmation.
Ne passe JAMAIS confirmed=True si le client n'a pas expressément écrit son accord préalable.

Pour toute question hors sujet (météo, cuisine, etc.) ou demande confidentielle/illégale, ne fais appel à AUCUN outil et réponds poliment que tu es limité au magasin TechStore AI."""


def executer_agent(
    demande: str,
    schemas: List[Dict[str, Any]] = SCHEMAS_PRECIS,
    max_tours: int = 5,
    provider=None
) -> Dict[str, Any]:
    """
    Boucle standard de l'agent (TP5) :
    1. Envoie l'historique et les schemas au LLM
    2. Si le LLM répond en texte -> termine
    3. Si le LLM demande un outil -> exécute la fonction Python associée
    4. Réinjecte le résultat avec le tool_call_id dans l'historique
    5. Recommence jusqu'à concurrence de max_tours
    """
    if provider is None:
        provider = get_provider(MODE)

    debut = time.perf_counter()

    # Règle de sécurité en amont si demande manifestement illégale ou confidentielle
    demande_lower = demande.lower()
    if any(w in demande_lower for w in ["pirater", "hack", "carte bancaire", "coordonnées personnelles"]):
        duree = round((time.perf_counter() - debut) * 1000, 2)
        return {
            "reponse": "Je ne peux pas accéder à des données personnelles ou effectuer des actions non autorisées. La sécurité et la confidentialité sont strictement protégées.",
            "appels": [],
            "tours": 0,
            "abandon": False,
            "latency_ms": duree
        }

    messages = [
        {"role": "system", "content": CONSIGNE_AGENT},
        {"role": "user", "content": demande}
    ]
    appels: List[Dict[str, Any]] = []

    for tour in range(1, max_tours + 1):
        msg = provider.chat(messages, tools=schemas, temperature=0.0).choices[0].message

        # Si le modèle ne demande pas d'outil, il a produit sa réponse finale
        if not getattr(msg, "tool_calls", None):
            duree = round((time.perf_counter() - debut) * 1000, 2)
            return {
                "reponse": msg.content or "",
                "appels": appels,
                "tours": tour,
                "abandon": False,
                "latency_ms": duree
            }

        # Ajouter le message assistant dans l'historique avant les retours tools (exigence TP5)
        assistant_dict: Dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
        tool_calls_repr = []
        for tc in msg.tool_calls:
            tool_calls_repr.append({
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments if isinstance(tc.function.arguments, str) else json.dumps(tc.function.arguments)
                }
            })
        assistant_dict["tool_calls"] = tool_calls_repr
        messages.append(assistant_dict)

        # Exécution de chaque appel d'outil
        for tc in msg.tool_calls:
            nom_outil = tc.function.name
            raw_args = tc.function.arguments
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args)
                except Exception:
                    args = {}
            else:
                args = raw_args or {}

            # Exécution par notre code Python (le LLM n'a jamais accès direct à la BDD)
            resultat = executer_outil(nom_outil, args)
            appels.append({
                "outil": nom_outil,
                "arguments": args,
                "resultat": resultat
            })

            # Réinjection du résultat avec tool_call_id
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(resultat, ensure_ascii=False)
            })

    duree = round((time.perf_counter() - debut) * 1000, 2)
    return {
        "reponse": "Nombre maximum d'itérations atteint.",
        "appels": appels,
        "tours": max_tours,
        "abandon": True,
        "latency_ms": duree
    }


# ==========================================
# ÉVALUATION DE L'AGENT (TP5)
# ==========================================

def charger_taches_agent(chemin_csv: str = None) -> List[Dict[str, Any]]:
    if chemin_csv is None:
        chemin_csv = os.path.join(os.path.dirname(__file__), "data", "agent_tasks.csv")
    taches = []
    with open(chemin_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            taches.append(row)
    return taches


def diagnostic_agent(outils_ok_list: List[bool], reponses_justes_list: List[bool]) -> Dict[str, List[int]]:
    """
    Tableau 2x2 de diagnostic des échecs (TP5) :
    - ok : bons outils ET réponse juste
    - redaction : bons outils mais réponse fausse (mauvaise interprétation du résultat)
    - detour : mauvais outils mais réponse juste (hasard ou raccourci)
    - outils : mauvais outils ET réponse fausse
    """
    cases = {"ok": [], "redaction": [], "detour": [], "outils": []}
    for i, (o_ok, r_juste) in enumerate(zip(outils_ok_list, reponses_justes_list)):
        if o_ok and r_juste:
            cases["ok"].append(i)
        elif o_ok and not r_juste:
            cases["redaction"].append(i)
        elif not o_ok and r_juste:
            cases["detour"].append(i)
        else:
            cases["outils"].append(i)
    return cases


def evaluer_agent_sur_taches(
    schemas: List[Dict[str, Any]] = SCHEMAS_PRECIS,
    etiquette: str = "agent_schemas_precis",
    mode: str = "mock"
) -> Dict[str, Any]:
    """Évalue l'agent sur les 20 tâches annotées."""
    taches = charger_taches_agent()
    provider = get_provider(mode)

    nb_total = len(taches)
    bons_outils_count = 0
    reponses_justes_count = 0
    taches_reussies_count = 0
    total_appels = 0
    commandes_non_demandees = 0
    abandons_count = 0

    outils_ok_list = []
    reponses_justes_list = []
    details_taches = []

    for t in taches:
        attendu_str = t.get("outils_attendus", "").strip()
        attendus = [o.strip() for o in attendu_str.split(";") if o.strip()]
        faits_str = t.get("faits", "").strip()
        variantes_faits = [f.strip().lower() for f in faits_str.split("|") if f.strip()]

        res = executer_agent(t["demande"], schemas=schemas, provider=provider)
        appeles = [a["outil"] for a in res["appels"]]
        total_appels += len(appeles)
        if res.get("abandon"):
            abandons_count += 1

        # Vérification des outils appelés
        outils_ok = (sorted(attendus) == sorted(appeles))
        if outils_ok:
            bons_outils_count += 1

        # Vérification des faits attendus dans la réponse
        rep_texte = res["reponse"].lower()
        if not variantes_faits:
            reponse_juste = True
        else:
            reponse_juste = any(v in rep_texte for v in variantes_faits)

        if reponse_juste:
            reponses_justes_count += 1

        # Tâche réussie = les deux à la fois
        tache_reussie = outils_ok and reponse_juste
        if tache_reussie:
            taches_reussies_count += 1

        # Détection d'action avec effet non demandée (ex: confirmation passée à True sans accord)
        for a in res["appels"]:
            if a["outil"] == "create_order":
                if a["arguments"].get("confirmed") is True and t.get("action_autorisee") != "1":
                    commandes_non_demandees += 1

        outils_ok_list.append(outils_ok)
        reponses_justes_list.append(reponse_juste)

        details_taches.append({
            "id": t["id"],
            "demande": t["demande"],
            "attendus": attendus,
            "appeles": appeles,
            "outils_ok": outils_ok,
            "reponse_juste": reponse_juste,
            "tache_reussie": tache_reussie,
            "tours": res["tours"],
            "reponse": res["reponse"]
        })

    diag = diagnostic_agent(outils_ok_list, reponses_justes_list)

    resume = {
        "etiquette": etiquette,
        "total_taches": nb_total,
        "taches_reussies": taches_reussies_count,
        "score_taches_reussies": round(taches_reussies_count / nb_total, 3),
        "bons_outils": bons_outils_count,
        "score_bons_outils": round(bons_outils_count / nb_total, 3),
        "reponses_justes": reponses_justes_count,
        "score_reponses_justes": round(reponses_justes_count / nb_total, 3),
        "appels_moyens_par_demande": round(total_appels / nb_total, 2),
        "commandes_non_demandees": commandes_non_demandees,
        "abandons": abandons_count,
        "diagnostic_counts": {k: len(v) for k, v in diag.items()},
        "diagnostic_indices": diag,
        "details": details_taches
    }

    print(f"\n=== ÉVALUATION AGENT : {etiquette} ===")
    print(f"Tâches réussies (décision) : {taches_reussies_count}/{nb_total} ({resume['score_taches_reussies']:.1%})")
    print(f"Bons outils appelés        : {bons_outils_count}/{nb_total} ({resume['score_bons_outils']:.1%})")
    print(f"Réponses justes            : {reponses_justes_count}/{nb_total} ({resume['score_reponses_justes']:.1%})")
    print(f"Appels moyens par demande  : {resume['appels_moyens_par_demande']}")
    print(f"Commandes non autorisées   : {commandes_non_demandees}")
    print(f"Diagnostic 2x2             : OK={len(diag['ok'])}, Rédaction={len(diag['redaction'])}, Détour={len(diag['detour'])}, Outils={len(diag['outils'])}")

    os.makedirs(os.path.join(os.path.dirname(__file__), "results"), exist_ok=True)
    fichier_sortie = os.path.join(os.path.dirname(__file__), "results", f"{etiquette}.json")
    with open(fichier_sortie, "w", encoding="utf-8") as f:
        json.dump(resume, f, indent=2, ensure_ascii=False)

    return resume


def comparer_schemas_agent():
    """
    Compare deux variantes de descriptions d'outils (TP5 Étape 6) :
    SCHEMAS_PRECIS vs SCHEMAS_VAGUES, une seule variable modifiée.
    """
    print("\n--- ÉVALUATION 1 : Descriptions précises ---")
    res_precis = evaluer_agent_sur_taches(SCHEMAS_PRECIS, "agent_schemas_precis", mode="mock")

    print("\n--- ÉVALUATION 2 : Descriptions vagues ---")
    res_vagues = evaluer_agent_sur_taches(SCHEMAS_VAGUES, "agent_schemas_vagues", mode="mock")

    ecart_reussite = res_precis["taches_reussies"] - res_vagues["taches_reussies"]
    ecart_outils = res_precis["bons_outils"] - res_vagues["bons_outils"]

    bilan = {
        "variable_modifiee": "qualité des descriptions JSON Schema des outils (précises vs vagues)",
        "variante_precis": {
            "taches_reussies": res_precis["taches_reussies"],
            "bons_outils": res_precis["bons_outils"],
            "diagnostic": res_precis["diagnostic_counts"]
        },
        "variante_vagues": {
            "taches_reussies": res_vagues["taches_reussies"],
            "bons_outils": res_vagues["bons_outils"],
            "diagnostic": res_vagues["diagnostic_counts"]
        },
        "ecart_taches_reussies": ecart_reussite,
        "ecart_bons_outils": ecart_outils,
        "total_taches": res_precis["total_taches"],
        "conclusion": (
            f"Des descriptions précises permettent de réussir {ecart_reussite} tâche(s) de plus "
            f"et d'appeler les bons outils sur {ecart_outils} tâche(s) supplémentaire(s)."
        )
    }

    fichier_bilan = os.path.join(os.path.dirname(__file__), "results", "agent_comparison.json")
    with open(fichier_bilan, "w", encoding="utf-8") as f:
        json.dump(bilan, f, indent=2, ensure_ascii=False)

    print("\n=== BILAN COMPARAISON AGENT (UNE SEULE VARIABLE) ===")
    print(f"Total tâches : {res_precis['total_taches']}")
    print(f"Réussite schémas précis : {res_precis['taches_reussies']}/{res_precis['total_taches']}")
    print(f"Réussite schémas vagues : {res_vagues['taches_reussies']}/{res_vagues['total_taches']}")
    print(f"Écart en nombre de tâches : {ecart_reussite:+} tâche(s)")
    print(f"Conclusion : {bilan['conclusion']}")

    return bilan


if __name__ == "__main__":
    comparer_schemas_agent()
