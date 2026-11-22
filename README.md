# ⚡ TechStore AI — Gestion Intelligente des Produits Électroniques avec Assistant IA

Projet universitaire complet de Machine Learning Appliqué (Licence 3 - DSI), développé en respectant scrupuleusement les consignes des **TP1 à TP5** et du **Guide Projet**.

---

## 📋 Table des Matières

1. [Présentation du Projet](#-présentation-du-projet)
2. [Conformité aux 6 Points Essentiels du Guide](#-conformité-aux-6-points-essentiels-du-guide)
3. [Points Bonus Réalisés](#-points-bonus-réalisés)
4. [Architecture et Organisation des Fichiers](#-architecture-et-organisation-des-fichiers)
5. [Installation et Configuration](#-installation-et-configuration)
6. [Lancement de l'Application](#-lancement-de-lapplication)
7. [Exécution des Tests et Résultats](#-exécution-des-tests-et-résultats)
8. [Guide des Fonctionnalités Pédagogiques](#-guide-des-fonctionnalités-pédagogiques)
9. [Fichiers Multimédia : Emplacements et Instructions](#-fichiers-multimédia--emplacements-et-instructions)

---

## 🎯 Présentation du Projet

**TechStore AI** est une application Web moderne couplée à une API FastAPI permettant de :
- Gérer le catalogue d'un magasin d'électronique (CRUD complet de produits et catégories).
- Gérer les commandes clients avec une **règle stricte de confirmation préalable** et mise à jour du stock.
- Fournir un assistant client IA autonome capable de :
  * Classifier les intentions (recherche, prix, comparaison, stock, garantie, commande, autre).
  * Répondre aux questions techniques et SAV à partir de documents PDF officiels (**RAG**).
  * Exécuter des actions métier via des outils réels en Python (**Tool Calling / Agent**).
  * Traiter des requêtes vocales (**Audio MP3**) et des captures/photos de produits (**Images**).

---

## 🛡️ Conformité aux 6 Points Essentiels du Guide

| # | Consigne du Guide | Implémentation dans TechStore AI | Emplacement dans le Code |
|---|---|---|---|
| **1** | **Contrat Pydantic & Mode Mock/Real** | Schémas Pydantic stricts indépendants du fournisseur. Fournisseur `MockProvider` déterministe hors ligne et `GroqProvider` en mode réel. Clé dans `.env`. | `schemas.py`, `providers.py`, `config.py` |
| **2** | **Sortie contrainte & Règle métier** | Énumération stricte des 7 catégories. Réponse au format JSON forcé. Règle métier de sécurité qui intercepte et refuse les requêtes malveillantes avant le modèle. | `classification.py` (`verifier_regle_metier_securite`), `providers.py` |
| **3** | **Savoir dire « Je ne sais pas »** | Champ `requires_review = True` dès que la confiance est inférieure à `REVIEW_THRESHOLD = 0.60`. Formule stricte de refus RAG : *"Information insuffisante dans les documents disponibles."* si information absente. | `classification.py`, `rag.py` |
| **4** | **Agent avec au moins 3 outils JSON Schema** | 4 outils décrits en JSON Schema (`search_products`, `compare_products`, `check_stock`, `create_order`). Boucle limitée à `max_tours = 5`. Sécurité absolue : commande impossible sans accord explicite. | `outils.py`, `agent.py` |
| **5** | **Mesurer sur un jeu annoté** | 25 exemples annotés pour la classification (`data/classification.csv`), 20 tâches pour l'agent (`data/agent_tasks.csv`), 20 questions RAG (`data/rag_questions.csv`). Métriques calculées par scripts Python. | `evaluation.py`, `classification.py`, `rag.py`, `agent.py` |
| **6** | **Comparer en changeant 1 seule variable** | Comparaison Zero-shot vs Few-shot pour la classification (**+7 exemples**, +0.305 Macro-F1). Comparaison Schémas Précis vs Vagues pour l'agent (**+2 tâches réussies**). Écarts chiffrés en nombre d'exemples. | `results/classification_comparison.json`, `results/agent_comparison.json` |

---

## 🎁 Points Bonus Réalisés

- **Contenu Multimédia (+2 points)** : Endpoints `/api/multimedia/audio` et `/api/multimedia/image`. Validation stricte du type MIME et de l'extension (erreur **415** si format non supporté) et de la taille maximale (erreur **413** si > 25 Mo audio ou > 10 Mo image).
- **RAG avec Sources (+2 points)** : 4 documents PDF officiels générés (`smartphones.pdf`, `laptops.pdf`, `garantie.pdf`, `retour.pdf`). Indexation vectorielle locale avec `fastembed` (MiniLM-L12-v2, 384 dim). Mesure de la recherche (`Recall@1=0.800`, `Recall@3=0.933`, `Recall@5=1.000`, `MRR=0.883`). Citations des passages `[P01]...[P16]`.
- **Diagnostic des Échecs (+1 point)** : Tableaux 2x2 implémentés pour le RAG (`OK`, `Génération`, `Chance`, `Recherche`) et pour l'Agent (`OK`, `Rédaction`, `Détour`, `Outils`).
- **Latence Mesurée (+1 point)** : Mesure systématique avec `time.perf_counter()` pour chaque composant (min, médiane, max conservées dans les rapports).

---

## 📂 Architecture et Organisation des Fichiers

```
techstore ai/
│
├── main.py                    # Application FastAPI, routes API et fichiers statiques
├── config.py                  # Chargement .env et constantes de configuration
├── schemas.py                 # Contrats de données Pydantic (produits, commandes, IA)
├── providers.py               # Fournisseurs d'inférence (MockProvider déterministe et GroqProvider)
├── crud.py                    # Logique métier CRUD produits et commandes sécurisées
├── classification.py          # Classifieur d'intentions et protocole d'évaluation (TP2)
├── evaluation.py              # Calcul manuel des métriques (Accuracy, Précision, Rappel, F1, Macro-F1, Matrice)
├── rag.py                     # Chaîne RAG documentaire : embeddings MiniLM, cosinus, Recall@k, MRR (TP4)
├── agent.py                   # Boucle autonome de l'agent avec gestion de tool_call_id et max_tours=5 (TP5)
├── outils.py                  # Fonctions Python et spécifications JSON Schema des 4 outils
├── multimedia.py              # Traitement vocal Whisper, calcul WER jiwer et vision produit (TP3)
├── generate_docs.py           # Générateur automatique des 4 documents PDF officiels
│
├── data/
│   ├── products.json          # Catalogue initial des 17 produits
│   ├── orders.json            # Commandes enregistrées
│   ├── classification.csv     # Jeu de test annoté (25 exemples avec cas difficiles/refus)
│   ├── agent_tasks.csv        # Jeu de test annoté agent (20 tâches variées)
│   ├── rag_questions.csv      # Jeu de test annoté RAG (20 questions dont 5 hors-base)
│   ├── passages.csv           # 16 passages découpés et référencés des documents PDF
│   ├── documents/             # Les 4 documents PDF générés
│   ├── images/                # Dossiers organisés pour vos images réelles
│   └── audio/                 # Dossiers organisés pour vos enregistrements MP3 réels
│
├── results/                   # Résultats réels des évaluations sauvegardés en JSON
│   ├── classification_zero_shot.json
│   ├── classification_few_shot.json
│   ├── classification_comparison.json
│   ├── agent_schemas_precis.json
│   ├── agent_schemas_vagues.json
│   ├── agent_comparison.json
│   ├── rag_retrieval_results.json
│   └── rag_generation_results.json
│
├── static/                    # Interface Web utilisateur (Single Page Application)
│   ├── index.html             # Structure HTML5 avec les 4 vues (Dashboard, Produits, Commandes, Assistant)
│   ├── style.css              # Feuille de style moderne et responsive
│   └── app.js                 # Logique JavaScript interactive (CRUD, Chat, Multimédia)
│
├── tests/                     # Suite de tests automatisés pytest
│   ├── test_api.py            # Tests des endpoints FastAPI (/health, /api/info, 422, etc.)
│   ├── test_crud.py           # Tests du cycle de vie produit et commandes sécurisées
│   ├── test_classification.py # Tests du classifieur et des règles métier
│   ├── test_agent.py          # Tests de la boucle de l'agent et des outils
│   ├── test_rag.py            # Tests de la recherche vectorielle et refus documentaire
│   └── test_multimedia.py     # Tests de validation (413, 415), WER et pipelines
│
├── .env                       # Variables locales d'exécution (non versionné)
├── .env.example               # Modèle des variables documentées
├── .gitignore                 # Exclusions Git
├── requirements.txt           # Dépendances Python
└── README.md                  # Documentation complète du projet
```

---

## ⚙️ Installation et Configuration

### Prérequis
- Python 3.11 ou version ultérieure
- Système d'exploitation : Linux, Windows ou macOS

### 1. Cloner le dépôt et créer l'environnement virtuel
```bash
python3 -m venv .venv
source .venv/bin/activate       # Sur Linux / macOS
# .venv\Scripts\Activate.ps1    # Sur Windows PowerShell
```

### 2. Installer les dépendances
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Configurer les variables d'environnement
Copiez `.env.example` en `.env` :
```bash
cp .env.example .env
```
Contenu de `.env` :
```ini
INFERENCE_MODE=mock
GROQ_API_KEY=
MODEL_ID=openai/gpt-oss-20b
MODEL_VISION=qwen/qwen3.8-27b
MODEL_AUDIO=whisper-large-v3-turbo
REVIEW_THRESHOLD=0.60
```
> **Remarque :** En mode `mock` (`INFERENCE_MODE=mock`), l'ensemble du projet fonctionne **intégralement hors ligne**, sans clé API, sans GPU et sans connexion Internet. Si vous disposez d'une clé Groq, renseignez `GROQ_API_KEY=gsk_...` et `INFERENCE_MODE=real`.

---

## 🚀 Lancement de l'Application

### 1. Démarrer le serveur FastAPI
```bash
.venv/bin/uvicorn main:app --reload --port 8000
```

### 2. Accéder à l'application
- **Interface Web interactive** : Ouvrez votre navigateur sur [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Documentation interactive Swagger** : [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Contrôle de santé** : [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 🧪 Exécution des Tests et Résultats

### 1. Lancer la suite de tests automatisés (pytest)
```bash
.venv/bin/pytest -v
```
**Résultat :** `32 passed in 4.33s` (100% des tests au vert).

### 2. Exécuter les scripts de mesure réels
Pour régénérer les fichiers de résultats dans `results/` :
```bash
# TP2 : Classification & Comparaison (1 variable : consigne zero-shot vs few-shot)
.venv/bin/python classification.py

# TP5 : Agent & Comparaison (1 variable : schémas précis vs vagues)
.venv/bin/python agent.py

# TP4 : Recherche vectorielle (Recall@k, MRR) et chaîne RAG complète
.venv/bin/python rag.py
```

### 3. Synthèse des résultats réels obtenus

#### A. TP2 — Classification (25 exemples)
- **Zero-shot** : 15/25 corrects (60.0%) — Macro-F1 : 0.5619
- **Few-shot** : 22/25 corrects (88.0%) — Macro-F1 : 0.8667
- **Écart mesuré à 1 variable** : **+7 exemples** (+0.3048 Macro-F1)

#### B. TP4 — RAG & Recherche Documentaire
- **Recall@1** : 0.800
- **Recall@3** : 0.933
- **Recall@5** : 1.000
- **MRR** : 0.883
- **Refus corrects sur questions hors base** : 5/5 (100.0%)
- **Diagnostic 2x2** : OK = 12 · Génération = 2 · Chance = 0 · Recherche = 1

#### C. TP5 — Agent avec Tools (20 tâches)
- **Schémas Précis** : 19/20 tâches réussies (95.0%) — Bons outils : 19/20 (95.0%)
- **Schémas Vagues** : 17/20 tâches réussies (85.0%) — Bons outils : 17/20 (85.0%)
- **Écart mesuré à 1 variable** : **+2 tâches** (+10.0% de décision)
- **Commandes non autorisées** : **0** (sécurité absolue garantie)
- **Diagnostic 2x2** : OK = 19 · Rédaction = 0 · Détour = 1 · Outils = 0

---

## 💡 Guide des Fonctionnalités Pédagogiques

### 1. Tableau de Bord (Dashboard)
Affiche l'état du système, le mode actif, le nombre de produits et commandes, ainsi que les panneaux de métriques pédagogiques (TP2, TP4, TP5).

### 2. Gestion des Produits (CRUD)
- Filtrage en temps réel par mots-clés, catégorie ou prix maximum.
- Ajout de produit via formulaire modal sécurisé.
- Modification des prix, caractéristiques et stocks.
- Suppression de produit avec confirmation.

### 3. Gestion des Commandes
- Liste des commandes avec statuts colorés (`confirmee`, `en_attente`, `livree`, `annulee`).
- Règle de confirmation : si la case *"Confirmation formelle du client"* n'est pas cochée, l'API renvoie un avertissement sans créer la commande.
- Décrémentation automatique du stock dès confirmation.

### 4. Assistant IA & Multimédia
- **Mode Agent (TP5)** : Posez une question comme *"Compare le P001 et le P002"* ou *"Vérifie le stock de P013"*. L'agent appelle les outils Python adéquats et affiche le déroulement dans le panneau latéral.
- **Mode RAG (TP4)** : Interrogez la base documentaire (ex: *"Combien de temps dure la garantie légale ?"*). L'assistant répond avec citation des sources `[P09]` et affiche les extraits correspondants.
- **Import Audio MP3 (TP3)** : Cliquez sur le micro 🎙️ pour téléverser une question vocale au format `.mp3`. L'audio est transcrit par Whisper ASR et transmis à l'assistant.
- **Import Image Produit (TP3)** : Cliquez sur l'appareil photo 📷 pour téléverser une photo d'appareil. L'image est analysée par vision multimodale et les produits correspondants du catalogue sont automatiquement suggérés.

---

## 📁 Fichiers Multimédia : Emplacements et Instructions

Toutes les fonctionnalités Image et Audio sont déjà développées, validées et testées.
Voici la liste précise des fichiers de démonstration que vous pouvez ajouter pour vos présentations finales :

### A. Fichiers Images à ajouter
Dossier racine des images : `data/images/`

| Nom exact | Extension | Dossier exact | Contenu attendu | Dimensions recommandées | Fonctionnalité testée |
|---|---|---|---|---|---|
| `s24_ultra.png` | `.png` | `data/images/smartphones/` | Photo nette d'un smartphone moderne avec bloc caméra | ~800x800 px, < 5 Mo | Détection catégorie Smartphones & recherche Galaxy |
| `macbook_air.jpg` | `.jpg` | `data/images/laptops/` | Photo d'un ordinateur portable ouvert avec clavier visible | ~1024x768 px, < 5 Mo | Détection catégorie Laptops & recommandation MacBook |
| `ipad_pro.png` | `.png` | `data/images/tablets/` | Photo d'une tablette tactile avec écran allumé ou éteint | ~800x800 px, < 5 Mo | Détection catégorie Tablettes & recommandation iPad |
| `sony_casque.jpg` | `.jpg` | `data/images/accessories/` | Photo d'un casque audio arceau sans fil | ~800x800 px, < 5 Mo | Détection catégorie Casques & écouteurs |
| `trop_lourd.png` | `.png` | `data/images/test/` | N'importe quelle image dont le poids dépasse 10 Mo | > 10 Mo | Test de refus d'erreur HTTP **413** (Payload Too Large) |
| `mauvais_format.bmp`| `.bmp` | `data/images/test/` | Fichier image au format Bitmap non autorisé | Quelconque | Test de refus d'erreur HTTP **415** (Unsupported Media) |

### B. Fichiers Audio à enregistrer ou générer (Format MP3 obligatoire)
Dossier racine de l'audio : `data/audio/`

| Nom exact | Extension | Dossier exact | Phrase exacte à prononcer | Langue | Durée recommandée | Fonctionnalité testée |
|---|---|---|---|---|---|---|
| `Q01_prix_s24.mp3` | `.mp3` | `data/audio/questions/` | *"Bonjour, quel est le prix du Galaxy S24 Ultra et est-il disponible en stock ?"* | Français | 3 à 6 secondes | Chaîne Whisper -> Intention Prix/Stock -> Réponse Agent |
| `Q02_comparatif.mp3` | `.mp3` | `data/audio/questions/` | *"Je voudrais comparer le MacBook Air M3 et le Dell XPS 15 s'il vous plaît."* | Français | 4 à 7 secondes | Chaîne Whisper -> Intention Comparaison -> Tool compare_products |
| `Q03_garantie.mp3` | `.mp3` | `data/audio/questions/` | *"Combien de temps dure la garantie légale sur vos ordinateurs portables ?"* | Français | 3 à 5 secondes | Chaîne Whisper -> RAG documentaire (garantie.pdf) |
| `Q04_commande.mp3` | `.mp3` | `data/audio/questions/` | *"Je confirme ma commande pour un exemplaire du chargeur Anker 67W."* | Français | 3 à 5 secondes | Chaîne Whisper -> Commande confirmée (create_order) |
| `Q05_hors_sujet.mp3` | `.mp3` | `data/audio/questions/` | *"Quel temps fait-il demain après-midi à Paris ?"* | Français | 2 à 4 secondes | Chaîne Whisper -> Détection hors sujet -> Refus poli sans outil |
| `trop_lourd.mp3` | `.mp3` | `data/audio/test/` | Fichier MP3 artificiellement volumineux (> 25 Mo) | Audio | > 25 Mo | Test de refus d'erreur HTTP **413** (Payload Too Large) |
| `format_rejete.wav`| `.wav` | `data/audio/test/` | Fichier audio avec extension `.wav` | Audio | Quelconque | Test de refus d'erreur HTTP **415** (Format MP3 obligatoire) |
