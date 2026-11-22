from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ==========================================
# SCHÉMAS PRODUITS & COMMANDES
# ==========================================

class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Nom du produit")
    brand: str = Field(..., min_length=1, max_length=100, description="Marque du produit")
    category: str = Field(..., min_length=2, max_length=100, description="Catégorie du produit")
    price: float = Field(..., gt=0, description="Prix en euros")
    description: str = Field(..., min_length=5, max_length=2000, description="Description détaillée")
    ram: Optional[str] = Field("N/A", description="Quantité de mémoire vive")
    storage: Optional[str] = Field("N/A", description="Capacité de stockage")
    stock: int = Field(..., ge=0, description="Quantité disponible en stock")


class ProductCreate(ProductBase):
    id: Optional[str] = Field(None, description="Identifiant produit personnalisé (ex: P018)")


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None
    ram: Optional[str] = None
    storage: Optional[str] = None
    stock: Optional[int] = Field(None, ge=0)


class ProductResponse(ProductBase):
    id: str


class OrderCreate(BaseModel):
    product_id: str = Field(..., description="Identifiant du produit à commander")
    quantity: int = Field(..., gt=0, description="Quantité souhaitée")
    confirmed: bool = Field(False, description="Confirmation explicite du client (exigée)")


class OrderStatusUpdate(BaseModel):
    status: str = Field(..., description="Nouveau statut: en_attente, confirmee, annulee, livree")


class OrderResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    quantity: int
    total_price: float
    status: str
    created_at: str


# ==========================================
# SCHÉMAS TP1 & TP2 : CLASSIFICATION
# ==========================================

class Prediction(BaseModel):
    label: str
    score: float = Field(..., ge=0, le=1)


class ClassificationRequest(BaseModel):
    text: str = Field(..., min_length=3, max_length=1000, description="Texte de la demande client")


class ClassificationResponse(BaseModel):
    provider: str
    model: str
    latency_ms: float
    category: str
    confidence: float
    requires_review: bool
    predictions: List[Prediction]


# ==========================================
# SCHÉMAS TP4 : RAG
# ==========================================

class RAGRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    k: int = Field(3, ge=1, le=5)


class PassageItem(BaseModel):
    id: str
    source: str
    titre: str
    texte: str
    score: float


class RAGResponse(BaseModel):
    question: str
    reponse: str
    sources: List[str]
    suffisant: bool
    passages: List[PassageItem]
    latency_ms: float


# ==========================================
# SCHÉMAS TP5 : AGENT ET OUTILS
# ==========================================

class AgentRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class ToolCallItem(BaseModel):
    outil: str
    arguments: Dict[str, Any]
    resultat: Any


class AgentResponse(BaseModel):
    reponse: str
    appels: List[ToolCallItem]
    tours: int
    abandon: bool
    latency_ms: float


# ==========================================
# SCHÉMAS TP3 : MULTIMÉDIA (AUDIO & IMAGE)
# ==========================================

class AudioTranscriptionResponse(BaseModel):
    transcription: str
    duree_secondes: Optional[float] = None
    taille_ko: float
    wer_estime: Optional[float] = None
    intention: Optional[str] = None
    reponse_agent: Optional[str] = None


class ImageAnalysisResponse(BaseModel):
    nom_fichier: str
    taille_ko: float
    description: str
    categorie_identifiee: str
    produits_recommandes: List[Dict[str, Any]]
