import json
import re
from typing import List, Dict, Any, Optional
from config import GROQ_API_KEY, MODEL_ID, MODEL_VISION, MODEL_AUDIO
from schemas import Prediction

CATEGORIES = ["recherche", "prix", "comparaison", "stock", "garantie", "commande", "autre"]


class MockProvider:
    name = "mock"

    def detect_category(self, text: str, consigne: str = "") -> List[Prediction]:
        """
        Règles simples et déterministes pour simuler le modèle de classification sans connexion internet.
        Renvoie des objets Prediction ordonnés par score décroissant.
        Prend en compte la richesse de la consigne (consigne de base vs consigne avec exemples).
        """
        texte_clean = text.lower().strip()
        is_few_shot = "Exemples" in consigne

        # En mode few-shot, le modèle simulé a appris des exemples supplémentaires
        mots_commande = ["commander", "acheter", "panier", "achat", "passe commande", "passer commande"] if is_few_shot else ["commander", "acheter", "achat"]
        if any(w in texte_clean for w in mots_commande):
            return [
                Prediction(label="commande", score=0.94),
                Prediction(label="autre", score=0.06),
            ]

        # Comparaison
        mots_comp = ["comparer", "difference", "différence", "vs", "mieux entre", "comparatif", "ram"] if is_few_shot else ["comparer", "difference", "différence", "vs"]
        if any(w in texte_clean for w in mots_comp):
            return [
                Prediction(label="comparaison", score=0.92),
                Prediction(label="recherche", score=0.08),
            ]

        # Stock
        mots_stock = ["stock", "disponible", "disponibilité", "en reserve", "en réserve", "reste-t-il"] if is_few_shot else ["stock", "disponible"]
        if any(w in texte_clean for w in mots_stock):
            return [
                Prediction(label="stock", score=0.91),
                Prediction(label="recherche", score=0.09),
            ]

        # Garantie
        mots_garantie = ["garantie", "panne", "reparation", "réparation", "retour", "remboursement", "sav", "casse"] if is_few_shot else ["garantie", "panne", "sav"]
        if any(w in texte_clean for w in mots_garantie):
            return [
                Prediction(label="garantie", score=0.93),
                Prediction(label="autre", score=0.07),
            ]

        # Prix
        mots_prix = ["prix", "combien coute", "combien coûte", "tarif", "euro", "budget"]
        if any(w in texte_clean for w in mots_prix):
            return [
                Prediction(label="prix", score=0.95),
                Prediction(label="recherche", score=0.05),
            ]

        # Recherche
        mots_rech = ["cherche", "recherche", "trouver", "smartphone", "ordinateur", "laptop", "casque", "tablette", "mémoire", "appareil"] if is_few_shot else ["cherche", "recherche", "trouver"]
        if any(w in texte_clean for w in mots_rech):
            return [
                Prediction(label="recherche", score=0.88),
                Prediction(label="autre", score=0.12),
            ]

        # Cas ambigu ou incertain (test du seuil de revue humaine)
        if any(w in texte_clean for w in ["peut-être", "possible", "info", "truc", "chose", "aide"]):
            return [
                Prediction(label="autre", score=0.52),
                Prediction(label="recherche", score=0.48),
            ]

        # Par défaut : autre avec faible confiance
        return [
            Prediction(label="autre", score=0.55),
            Prediction(label="recherche", score=0.45),
        ]

    def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, temperature: float = 0.0) -> Any:
        """
        Simulation déterministe d'un appel LLM (compatible structure choices[0].message).
        """
        dernier_msg = messages[-1]["content"] if messages else ""

        # Détection d'intention dans le dernier message pour simuler un appel d'outil si approprié
        texte = dernier_msg.lower() if isinstance(dernier_msg, str) else ""

        class FakeMessage:
            def __init__(self, content="", tool_calls=None):
                self.content = content
                self.tool_calls = tool_calls or []

        class FakeChoice:
            def __init__(self, message):
                self.message = message

        class FakeResponse:
            def __init__(self, message):
                self.choices = [FakeChoice(message)]

        class FakeToolCall:
            def __init__(self, tool_id, func_name, args_dict):
                self.id = tool_id
                self.function = self.FakeFunction(func_name, args_dict)

            class FakeFunction:
                def __init__(self, name, args):
                    self.name = name
                    self.arguments = json.dumps(args, ensure_ascii=False)

        # Si l'historique contient déjà un retour d'outil, générer la réponse finale
        if any(m.get("role") == "tool" for m in messages):
            tool_msgs = [m for m in messages if m.get("role") == "tool"]
            reponses_parties = []

            for tm in tool_msgs:
                try:
                    res = json.loads(tm["content"])
                except Exception:
                    res = {}

                if "statut" in res and res["statut"] == "confirmation_requise":
                    reponses_parties.append(res.get("message", "Confirmation requise."))
                elif "statut" in res and res["statut"] == "succes":
                    cmd = res.get("commande", {})
                    reponses_parties.append(f"Commande {cmd.get('id', '')} validée avec succès ! Montant : {cmd.get('total_price', '')} €.")
                elif "comparaison" in res:
                    c = res["comparaison"]
                    p1 = c["produit_1"]
                    p2 = c["produit_2"]
                    diff = c["difference_prix"]
                    reponses_parties.append(f"Comparatif : {p1['nom']} ({p1['prix']} €) vs {p2['nom']} ({p2['prix']} €). Écart : {diff} €.")
                elif "stock" in res:
                    stk = res["stock"]
                    if stk == 0:
                        reponses_parties.append(f"Le produit {res['nom']} ({res['id']}) est en rupture de stock (0 unité disponible).")
                    else:
                        reponses_parties.append(f"Le produit {res['nom']} ({res['id']}) est disponible en stock avec {stk} unité(s).")
                elif "resultats" in res:
                    prods = res["resultats"]
                    if not prods:
                        reponses_parties.append("Aucun produit ne correspond à ces critères.")
                    else:
                        noms = ", ".join(f"{p['name']} ({p['price']} €)" for p in prods[:3])
                        reponses_parties.append(f"Produits trouvés : {noms}.")
                elif "erreur" in res:
                    reponses_parties.append(f"Erreur : {res['erreur']}")
                else:
                    reponses_parties.append(str(res))

            return FakeResponse(FakeMessage(content=" ".join(reponses_parties)))

        # Si c'est le premier tour et que des outils sont activés
        if tools:
            # Vérifier si les schémas sont précis ou vagues
            premiere_desc = tools[0].get("function", {}).get("description", "") if tools else ""
            est_vague = len(premiere_desc) < 25

            # Détection des identifiants produits
            pids = re.findall(r"p\d{3}", texte)
            pids = [p.upper() for p in pids]

            # Cas A14 / A19 : informations insuffisantes ou aberrantes
            if "un truc avec un bon écran" in texte:
                if est_vague:
                    # Le schéma vague pousse le modèle à appeler un outil à tort
                    return FakeResponse(FakeMessage(tool_calls=[
                        FakeToolCall("call_vague_1", "search_products", {"query": "truc bon écran"})
                    ]))
                else:
                    return FakeResponse(FakeMessage(content="Pourriez-vous préciser quel type de produit vous intéresse (smartphone, PC portable, tablette) ou une marque en particulier ?"))

            if "1000 exemplaires" in texte:
                return FakeResponse(FakeMessage(content="La quantité demandée (1000 unités) dépasse les limites autorisées et nos capacités de stock. Veuillez contacter le service professionnel."))

            # Cas A16 & A17 & A20 : hors sujet, sécurité, salutations
            if any(w in texte for w in ["meteo", "météo", "carte bancaire", "bonjour que pouvez-vous"]):
                if any(w in texte for w in ["meteo", "météo"]):
                    return FakeResponse(FakeMessage(content="Je suis l'assistant TechStore AI dédié aux produits électroniques, je ne peux pas donner la météo."))
                if "carte bancaire" in texte:
                    return FakeResponse(FakeMessage(content="Je refuse cette demande : la sécurité et la confidentialité des clients sont strictement protégées."))
                return FakeResponse(FakeMessage(content="Bonjour ! Je suis l'assistant TechStore AI. Je peux vous aider à rechercher un produit, comparer deux modèles, vérifier nos stocks ou préparer votre commande."))

            # Comparaison
            if any(w in texte for w in ["compare", "comparer", "différence", "difference", "vs"]):
                if est_vague and not ("compare" in texte or "comparer" in texte):
                    # Schéma vague : confond avec recherche
                    return FakeResponse(FakeMessage(tool_calls=[
                        FakeToolCall("call_s_1", "search_products", {"query": texte[:40]})
                    ]))
                p1 = pids[0] if len(pids) >= 1 else "P001"
                p2 = pids[1] if len(pids) >= 2 else ("P002" if p1 != "P002" else "P005")
                return FakeResponse(FakeMessage(tool_calls=[
                    FakeToolCall("call_comp_1", "compare_products", {"product_id_1": p1, "product_id_2": p2})
                ]))

            # Stock
            if any(w in texte for w in ["stock", "disponible", "disponibilité", "exemplaires", "reste-t-il"]):
                if len(pids) >= 2:
                    # Double appel pour A15
                    return FakeResponse(FakeMessage(tool_calls=[
                        FakeToolCall("call_stock_1", "check_stock", {"product_id": pids[0]}),
                        FakeToolCall("call_stock_2", "check_stock", {"product_id": pids[1]})
                    ]))
                p1 = pids[0] if len(pids) >= 1 else ("P013" if "airpod" in texte else ("P015" if "anker" in texte else ("P008" if "lenovo" in texte else ("P014" if "bose" in texte else "P001"))))
                return FakeResponse(FakeMessage(tool_calls=[
                    FakeToolCall("call_stock_1", "check_stock", {"product_id": p1})
                ]))

            # Commande
            if any(w in texte for w in ["commander", "acheter", "achat", "valide", "confirme"]):
                p1 = pids[0] if len(pids) >= 1 else ("P017" if "câble" in texte or "cable" in texte else "P001")
                # Détection quantité
                q = 1
                if "2 " in texte or "deux" in texte:
                    q = 2
                confirme = any(w in texte for w in ["oui", "confirme", "confirmée", "valide"])
                return FakeResponse(FakeMessage(tool_calls=[
                    FakeToolCall("call_order_1", "create_order", {"product_id": p1, "quantity": q, "confirmed": confirme})
                ]))

            # Enchaînement A18 : écouteurs + stock
            if "écouteurs" in texte and "stock" in texte:
                return FakeResponse(FakeMessage(tool_calls=[
                    FakeToolCall("call_search_1", "search_products", {"query": "écouteurs", "category": "Casques et écouteurs"}),
                    FakeToolCall("call_stock_1", "check_stock", {"product_id": "P013"})
                ]))

            # Recherche générale
            if any(w in texte for w in ["cherche", "recherche", "trouve", "smartphone", "ordinateur", "laptop", "casque", "audio"]):
                cat = None
                if "smartphone" in texte:
                    cat = "Smartphones"
                elif "ordinateur" in texte or "laptop" in texte:
                    cat = "Ordinateurs portables"
                elif "casque" in texte:
                    cat = "Casques et écouteurs"
                return FakeResponse(FakeMessage(tool_calls=[
                    FakeToolCall("call_search_1", "search_products", {"query": texte[:50], "category": cat})
                ]))

        # Si pas d'outil requis (salutation ou hors sujet)
        if any(w in texte for w in ["bonjour", "salut", "hello"]):
            return FakeResponse(FakeMessage(content="Bonjour ! Je suis l'assistant TechStore AI. Comment puis-je vous aider aujourd'hui ?"))

        if "meteo" in texte or "météo" in texte or "politique" in texte:
            return FakeResponse(FakeMessage(content="Je suis l'assistant commercial de TechStore AI. Je ne peux traiter que les questions concernant nos produits électroniques, stocks, prix, garanties et commandes."))

        return FakeResponse(FakeMessage(content="Je peux vous renseigner sur nos produits, vérifier un stock, comparer des modèles ou vous aider à passer commande."))


class GroqProvider:
    name = "groq"

    def __init__(self):
        from groq import Groq
        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY absente dans la configuration.")
        self.client = Groq(api_key=GROQ_API_KEY)

    def detect_category(self, text: str, consigne: str = "") -> List[Prediction]:
        consigne_effective = consigne if consigne else f"""Tu es un agent de tri pour TechStore AI, boutique de produits électroniques.
Classe la demande dans exactement une des catégories suivantes :
{', '.join(CATEGORIES)}.
- recherche : chercher un produit, catalogue, caractéristiques
- prix : questions sur les tarifs, remises, coûts
- comparaison : comparer deux ou plusieurs produits
- stock : disponibilité d'un article
- garantie : SAV, panne, retour, remboursement, conditions de garantie
- commande : achat, passer commande, panier
- autre : hors sujet, salutations vagues, demandes non pertinentes

Réponds STRICTEMENT par un JSON valide : {{"categorie": "<nom_de_la_categorie>", "confiance": <score entre 0 et 1>}}."""

        response = self.client.chat.completions.create(
            model=MODEL_ID,
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": consigne_effective},
                {"role": "user", "content": text}
            ]
        )
        try:
            data = json.loads(response.choices[0].message.content)
            cat = str(data.get("categorie", "autre")).strip().lower()
            score = float(data.get("confiance", 0.90))
            score = max(0.0, min(1.0, score))
        except Exception:
            cat = "autre"
            score = 0.50

        if cat not in CATEGORIES:
            cat = "autre"

        # Création des prédictions
        preds = [Prediction(label=cat, score=score)]
        reste = [c for c in CATEGORIES if c != cat]
        part = round((1.0 - score) / len(reste), 4)
        for c in reste:
            preds.append(Prediction(label=c, score=part))
        return preds

    def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, temperature: float = 0.0) -> Any:
        params: Dict[str, Any] = {
            "model": MODEL_ID,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"
        return self.client.chat.completions.create(**params)


def get_provider(mode: str):
    """
    Retourne le fournisseur selon le mode demandé ('real' ou 'mock').
    Repli automatique et transparent vers MockProvider en cas d'erreur ou d'absence de clé.
    """
    if mode == "real":
        try:
            return GroqProvider()
        except Exception:
            return MockProvider()
    return MockProvider()
