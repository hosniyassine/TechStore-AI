import json
import os
import time
import shutil
from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from config import MODE, MODEL_ID, REVIEW_THRESHOLD
from providers import get_provider
import crud
import schemas
import classification
import agent
import rag
import multimedia

app = FastAPI(
    title="TechStore AI",
    description="Gestion intelligente des produits électroniques avec assistant IA (TP1 à TP5)",
    version="1.0.0"
)

# Montage des fichiers statiques pour l'interface Web
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

provider = get_provider(MODE)


# ==========================================
# 1. SANTÉ ET SYSTÈME (TP1)
# ==========================================

@app.get("/")
def read_root():
    """Redirige vers l'interface Web du Dashboard."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Bienvenue sur l'API TechStore AI. Visitez /docs pour la documentation interactive."}


@app.get("/health")
def health():
    """Endpoint de santé officiel (TP1) indiquant le mode et le fournisseur actif."""
    return {
        "status": "ok",
        "mode": MODE,
        "provider": getattr(provider, "name", "mock")
    }


@app.get("/api/info")
def system_info():
    """Informations de diagnostic pour la soutenance et le tableau de bord."""
    prods = crud.get_all_products()
    orders = crud.get_all_orders()
    return {
        "mode": MODE,
        "provider": getattr(provider, "name", "mock"),
        "model_id": MODEL_ID,
        "review_threshold": REVIEW_THRESHOLD,
        "total_produits": len(prods),
        "total_commandes": len(orders),
        "categories": crud.CATEGORIES_AUTORISEES
    }


# ==========================================
# 2. GESTION DES PRODUITS (CRUD)
# ==========================================

@app.get("/api/products", response_model=List[schemas.ProductResponse])
def list_products(
    category: Optional[str] = Query(None, description="Filtrer par catégorie"),
    search: Optional[str] = Query(None, description="Recherche textuelle"),
    max_price: Optional[float] = Query(None, description="Prix plafond")
):
    """Consulte tous les produits avec filtres optionnels."""
    return crud.get_all_products(category=category, search=search, max_price=max_price)


@app.get("/api/products/{product_id}", response_model=schemas.ProductResponse)
def get_product(product_id: str):
    """Consulte la fiche détaillée d'un produit."""
    p = crud.get_product_by_id(product_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Produit {product_id} non trouvé.")
    return p


@app.post("/api/products", response_model=schemas.ProductResponse, status_code=201)
def add_product(payload: schemas.ProductCreate):
    """Ajoute un nouveau produit au catalogue."""
    try:
        nouveau = crud.create_product(payload.model_dump())
        return nouveau
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.put("/api/products/{product_id}", response_model=schemas.ProductResponse)
def modify_product(product_id: str, payload: schemas.ProductUpdate):
    """Modifie les informations d'un produit existant."""
    modifie = crud.update_product(product_id, payload.model_dump(exclude_unset=True))
    if not modifie:
        raise HTTPException(status_code=404, detail=f"Produit {product_id} introuvable.")
    return modifie


@app.delete("/api/products/{product_id}")
def remove_product(product_id: str):
    """Supprime un produit du catalogue."""
    succes = crud.delete_product(product_id)
    if not succes:
        raise HTTPException(status_code=404, detail=f"Produit {product_id} introuvable.")
    return {"status": "success", "message": f"Produit {product_id} supprimé avec succès."}


# ==========================================
# 3. GESTION DES COMMANDES
# ==========================================

@app.get("/api/orders", response_model=List[schemas.OrderResponse])
def list_orders():
    """Affiche toutes les commandes."""
    return crud.get_all_orders()


@app.get("/api/orders/{order_id}", response_model=schemas.OrderResponse)
def get_order(order_id: str):
    """Consulte une commande spécifique."""
    cmd = crud.get_order_by_id(order_id)
    if not cmd:
        raise HTTPException(status_code=404, detail=f"Commande {order_id} non trouvée.")
    return cmd


@app.post("/api/orders")
def make_order(payload: schemas.OrderCreate):
    """
    Crée une commande.
    RÈGLE ABSOLUE : Confirmation obligatoire du client avant création réelle.
    """
    res = crud.create_order(
        product_id=payload.product_id,
        quantity=payload.quantity,
        confirmed=payload.confirmed
    )
    if res.get("statut") == "erreur":
        raise HTTPException(status_code=400, detail=res["message"])
    return res


@app.patch("/api/orders/{order_id}/status", response_model=schemas.OrderResponse)
def change_order_status(order_id: str, payload: schemas.OrderStatusUpdate):
    """Modifie le statut d'une commande (en_attente, confirmee, annulee, livree)."""
    try:
        modifie = crud.update_order_status(order_id, payload.status)
        if not modifie:
            raise HTTPException(status_code=404, detail=f"Commande {order_id} introuvable.")
        return modifie
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


# ==========================================
# 4. TP1 & TP2 : CLASSIFICATION ET ÉVALUATION
# ==========================================

@app.post("/api/classify", response_model=schemas.ClassificationResponse)
def classify_text(payload: schemas.ClassificationRequest):
    """Classe une demande client selon les 7 catégories de l'atelier 2."""
    res = classification.classer_demande(payload.text, provider=provider)
    return schemas.ClassificationResponse(
        provider=res["provider"],
        model=MODEL_ID,
        latency_ms=res["latency_ms"],
        category=res["categorie"],
        confidence=res["score"],
        requires_review=res["requires_review"],
        predictions=res["predictions"]
    )


@app.get("/api/classification/metrics")
def get_classification_metrics():
    """Retourne les métriques calculées et la comparaison de consigne (une variable à la fois)."""
    fichier_comp = os.path.join(os.path.dirname(__file__), "results", "classification_comparison.json")
    if os.path.exists(fichier_comp):
        with open(fichier_comp, "r", encoding="utf-8") as f:
            return json.load(f)
    return classification.comparer_variantes()


# ==========================================
# 5. TP5 : AGENT ET OUTILS (TOOL CALLING)
# ==========================================

@app.post("/api/agent/chat", response_model=schemas.AgentResponse)
def agent_chat(payload: schemas.AgentRequest):
    """
    Exécute l'agent autonome avec boucle de réflexion,
    appels d'outils Python et respect strict de max_tours=5.
    """
    res = agent.executer_agent(payload.message, provider=provider)
    return schemas.AgentResponse(
        reponse=res["reponse"],
        appels=res["appels"],
        tours=res["tours"],
        abandon=res["abandon"],
        latency_ms=res["latency_ms"]
    )


@app.get("/api/agent/metrics")
def get_agent_metrics():
    """Retourne le bilan d'évaluation de l'agent et la comparaison schémas précis vs vagues."""
    fichier_comp = os.path.join(os.path.dirname(__file__), "results", "agent_comparison.json")
    if os.path.exists(fichier_comp):
        with open(fichier_comp, "r", encoding="utf-8") as f:
            return json.load(f)
    return agent.comparer_schemas_agent()


# ==========================================
# 6. TP4 : RAG ET DOCUMENTS PDF
# ==========================================

@app.post("/api/rag/query", response_model=schemas.RAGResponse)
def query_rag(payload: schemas.RAGRequest):
    """
    Interroge la base documentaire (smartphones.pdf, laptops.pdf, garantie.pdf, retour.pdf).
    Retrouve les k passages et formule la réponse avec citations.
    """
    debut = time.perf_counter()
    passages = rag.rechercher_passages(payload.question, k=payload.k)
    reponse_rag = rag.repondre_rag(payload.question, passages, provider=provider)
    latence = round((time.perf_counter() - debut) * 1000, 1)

    passages_items = [
        schemas.PassageItem(
            id=p["id"],
            source=p["source"],
            titre=p["titre"],
            texte=p["texte"],
            score=p["score"]
        )
        for p in passages
    ]

    return schemas.RAGResponse(
        question=payload.question,
        reponse=reponse_rag["reponse"],
        sources=reponse_rag["sources"],
        suffisant=reponse_rag["suffisant"],
        passages=passages_items,
        latency_ms=latence
    )


@app.get("/api/rag/metrics")
def get_rag_metrics():
    """Retourne les métriques Recall@k, MRR et le diagnostic 2x2."""
    retrieval_file = os.path.join(os.path.dirname(__file__), "results", "rag_retrieval_results.json")
    generation_file = os.path.join(os.path.dirname(__file__), "results", "rag_generation_results.json")

    res_retrieval = {}
    res_gen = {}

    if os.path.exists(retrieval_file):
        with open(retrieval_file, "r", encoding="utf-8") as f:
            res_retrieval = json.load(f)
    else:
        res_retrieval = rag.evaluer_recherche_rag()

    if os.path.exists(generation_file):
        with open(generation_file, "r", encoding="utf-8") as f:
            res_gen = json.load(f)
    else:
        res_gen = rag.evaluer_chaine_rag_complete()

    return {
        "recherche": res_retrieval,
        "generation": res_gen
    }


# ==========================================
# 7. TP3 : MULTIMÉDIA (AUDIO ET IMAGE)
# ==========================================

UPLOAD_TEMP_DIR = os.path.join(os.path.dirname(__file__), "data", "temp_uploads")
os.makedirs(UPLOAD_TEMP_DIR, exist_ok=True)


@app.post("/api/multimedia/audio")
async def upload_audio(file: UploadFile = File(...)):
    """
    Réception et traitement d'un fichier audio (TP3) :
    1. Vérification format strict MP3 (415 si invalide)
    2. Vérification taille maximale 25 Mo (413 si dépassée)
    3. Transcription Whisper ASR
    4. Acheminement vers l'assistant TechStore AI
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext != ".mp3":
        raise HTTPException(
            status_code=415,
            detail=f"Format audio '{ext}' non supporté. Seul le format MP3 (.mp3) est accepté."
        )

    temp_path = os.path.join(UPLOAD_TEMP_DIR, f"temp_{int(time.time())}_{file.filename}")
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        valide, code, msg = multimedia.valider_fichier_audio(temp_path)
        if not valide:
            raise HTTPException(status_code=code, detail=msg)

        resultat = multimedia.traiter_audio_complet(temp_path)
        return resultat
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@app.post("/api/multimedia/image")
async def upload_image(file: UploadFile = File(...)):
    """
    Réception et traitement d'une image de produit (TP3) :
    1. Vérification extension .png, .jpg, .jpeg, .webp (415 si invalide)
    2. Vérification taille maximale 10 Mo (413 si dépassée)
    3. Analyse vision multimodale
    4. Proposition des produits correspondants du catalogue
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in multimedia.EXTENSIONS_IMAGE_AUTORISEES:
        raise HTTPException(
            status_code=415,
            detail=f"Format image '{ext}' non supporté. Formats acceptés : .png, .jpg, .jpeg, .webp."
        )

    temp_path = os.path.join(UPLOAD_TEMP_DIR, f"temp_{int(time.time())}_{file.filename}")
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        valide, code, msg = multimedia.valider_fichier_image(temp_path)
        if not valide:
            raise HTTPException(status_code=code, detail=msg)

        resultat = multimedia.analyser_image_produit(temp_path)
        return resultat
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
