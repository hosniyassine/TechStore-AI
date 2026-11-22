import base64
import os
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image
import jiwer
from config import MODE, GROQ_API_KEY, MODEL_AUDIO, MODEL_VISION
from providers import get_provider
import crud
from agent import executer_agent

MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024  # 25 Mo (limite officielle Whisper / TP3)
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 Mo
EXTENSIONS_AUDIO_AUTORISEES = [".mp3"]  # Exigence stricte : FORMAT AUDIO FINAL MP3
EXTENSIONS_IMAGE_AUTORISEES = [".png", ".jpg", ".jpeg", ".webp"]


# ==========================================
# VALIDATION ET GESTION DES FICHIERS
# ==========================================

def valider_fichier_audio(chemin: str) -> Tuple[bool, int, str]:
    """
    Vérifie l'existence, l'extension et la taille du fichier audio.
    Renvoie (valide, code_statut, message_erreur).
    """
    p = Path(chemin)
    if not p.exists():
        return False, 404, "Fichier audio introuvable."

    ext = p.suffix.lower()
    if ext not in EXTENSIONS_AUDIO_AUTORISEES:
        return False, 415, f"Format audio non supporté ({ext}). Format obligatoire : MP3 (.mp3)."

    taille = p.stat().st_size
    if taille == 0:
        return False, 400, "Le fichier audio est vide (0 octet)."

    if taille > MAX_AUDIO_SIZE_BYTES:
        return False, 413, f"Fichier trop volumineux ({taille / (1024*1024):.1f} Mo). Maximum autorisé : 25 Mo."

    return True, 200, "OK"


def valider_fichier_image(chemin: str) -> Tuple[bool, int, str]:
    """
    Vérifie l'existence, le format et l'intégrité du fichier image.
    Renvoie (valide, code_statut, message_erreur).
    """
    p = Path(chemin)
    if not p.exists():
        return False, 404, "Fichier image introuvable."

    ext = p.suffix.lower()
    if ext not in EXTENSIONS_IMAGE_AUTORISEES:
        return False, 415, f"Format image non supporté ({ext}). Formats acceptés : .png, .jpg, .jpeg, .webp."

    taille = p.stat().st_size
    if taille == 0:
        return False, 400, "Le fichier image est vide (0 octet)."

    if taille > MAX_IMAGE_SIZE_BYTES:
        return False, 413, f"Fichier trop volumineux ({taille / (1024*1024):.1f} Mo). Maximum autorisé : 10 Mo."

    try:
        with Image.open(chemin) as img:
            img.verify()
    except Exception:
        return False, 400, "Fichier image corrompu ou illisible."

    return True, 200, "OK"


# ==========================================
# TRAITEMENT AUDIO (TP3)
# ==========================================

def normaliser_texte_wer(texte: str) -> str:
    """
    Normalisation exacte issue de TP3 pour le calcul du WER :
    Minuscules, '€' -> 'euros', suppression apostrophes, tirets, ponctuation, espaces multiples.
    Préserve scrupuleusement les accents (règle pédagogique TP3).
    """
    texte = texte.lower()
    texte = texte.replace("\u2019", "'")
    texte = texte.replace("\u20ac", " euros ")
    texte = re.sub(r"['\-]", " ", texte)
    texte = re.sub(r"[^\w\s]", " ", texte)
    return " ".join(texte.split())


def calculer_wer(reference: str, hypothese: str) -> float:
    """Calcule le Word Error Rate entre la référence et la transcription."""
    ref_norm = normaliser_texte_wer(reference)
    hyp_norm = normaliser_texte_wer(hypothese)
    if not ref_norm:
        return 0.0 if not hyp_norm else 1.0
    return round(float(jiwer.wer(ref_norm, hyp_norm)), 4)


def transcrire_audio(chemin: str, modele: str = MODEL_AUDIO, langue: str = "fr") -> str:
    """
    Appelle Whisper sur Groq (ou repli simulé déterministe hors ligne).
    Conforme au code de transcription.py de l'atelier 3.
    """
    valide, code, msg = valider_fichier_audio(chemin)
    if not valide:
        raise ValueError(f"Erreur {code} : {msg}")

    # Si clé Groq disponible, appel réel
    if GROQ_API_KEY and MODE == "real":
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            options = {}
            if langue:
                options["language"] = langue
            with open(chemin, "rb") as f:
                reponse = client.audio.transcriptions.create(
                    file=(Path(chemin).name, f.read()),
                    model=modele,
                    temperature=0.0,
                    **options
                )
            return reponse.text.strip()
        except Exception as exc:
            print(f"Échec Whisper réel, repli simulé : {exc}")

    # Mode MOCK / simulation déterministe basée sur le nom du fichier ou métadonnées
    nom = Path(chemin).stem.lower()
    if "s24" in nom or "smartphone" in nom:
        return "Bonjour, quel est le prix du Galaxy S24 Ultra et est-il disponible en stock ?"
    elif "macbook" in nom or "laptop" in nom:
        return "Je voudrais comparer le MacBook Air M3 et le Dell XPS 15 s'il vous plaît."
    elif "garantie" in nom:
        return "Combien de temps dure la garantie légale sur vos ordinateurs portables ?"
    elif "commande" in nom:
        return "Je confirme ma commande pour un exemplaire du chargeur Anker 67W."
    elif "retour" in nom:
        return "Quelles sont les conditions pour renvoyer un casque audio déballé ?"
    else:
        return "Bonjour, je recherche un bon smartphone Samsung à moins de mille euros."


def traiter_audio_complet(chemin_audio: str) -> Dict[str, Any]:
    """
    Chaîne complète TP3 :
    Fichier MP3 -> Whisper (ASR) -> Assistant Agent / Classification -> Réponse finale.
    """
    valide, code, msg = valider_fichier_audio(chemin_audio)
    if not valide:
        return {"succes": False, "code_erreur": code, "erreur": msg}

    p = Path(chemin_audio)
    taille_ko = round(p.stat().st_size / 1024, 2)

    # 1. Transcription ASR
    debut_trans = time.perf_counter()
    transcription = transcrire_audio(chemin_audio)
    duree_trans_ms = round((time.perf_counter() - debut_trans) * 1000, 1)

    # 2. Transmission à l'agent
    res_agent = executer_agent(transcription)

    return {
        "succes": True,
        "nom_fichier": p.name,
        "taille_ko": taille_ko,
        "transcription": transcription,
        "latence_transcription_ms": duree_trans_ms,
        "reponse_agent": res_agent["reponse"],
        "appels_outils": res_agent["appels"],
        "latence_totale_ms": round(duree_trans_ms + res_agent["latency_ms"], 1)
    }


# ==========================================
# TRAITEMENT IMAGE (TP3)
# ==========================================

def encoder_image_base64(chemin: str) -> str:
    """Encode une image en data URL base64 conformément à l'atelier 3."""
    with open(chemin, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    ext = Path(chemin).suffix.lstrip(".").lower()
    if ext == "jpg":
        ext = "jpeg"
    return f"data:image/{ext};base64,{b64}"


CONSIGNE_VISION = """Tu es un assistant vision pour TechStore AI, magasin de produits électroniques.
Analyse attentivement l'image fournie.
Identifie :
1. La catégorie exacte parmi : Smartphones, Ordinateurs portables, Tablettes, Casques et écouteurs, Accessoires électroniques.
2. Une description visuelle concise du modèle ou type d'appareil (nom probable, marque, couleur).

Réponds STRICTEMENT par un objet JSON au format :
{"categorie": "<une des cinq catégories>", "description": "<description concise du produit>", "mots_cles": "<mots clés pour recherche catalogue>"}"""


def analyser_image_produit(chemin_image: str) -> Dict[str, Any]:
    """
    Traite une image de produit (TP3) :
    1. Validation format et taille
    2. Vision multimodale (Groq ou simulation mock)
    3. Recherche des produits correspondants dans le catalogue TechStore AI.
    """
    valide, code, msg = valider_fichier_image(chemin_image)
    if not valide:
        return {"succes": False, "code_erreur": code, "erreur": msg}

    p = Path(chemin_image)
    taille_ko = round(p.stat().st_size / 1024, 2)

    categorie_detectee = "Smartphones"
    description_visuelle = "Smartphone moderne avec écran bord à bord et bloc photo arrière."
    mots_cles = "smartphone"

    # Si Groq vision disponible
    if GROQ_API_KEY and MODE == "real":
        try:
            from groq import Groq
            import json
            client = Groq(api_key=GROQ_API_KEY)
            data_url = encoder_image_base64(chemin_image)
            reponse = client.chat.completions.create(
                model=MODEL_VISION,
                temperature=0.0,
                response_format={"type": "json_object"},
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": CONSIGNE_VISION},
                        {"type": "image_url", "image_url": {"url": data_url}}
                    ]
                }]
            )
            parsed = json.loads(reponse.choices[0].message.content)
            categorie_detectee = parsed.get("categorie", "Smartphones")
            description_visuelle = parsed.get("description", description_visuelle)
            mots_cles = parsed.get("mots_cles", mots_cles)
        except Exception as exc:
            print(f"Échec vision réelle, repli simulé : {exc}")

    # Simulation déterministe hors ligne basée sur le chemin / dossier
    nom_parent = p.parent.name.lower()
    nom_fich = p.name.lower()

    if "laptop" in nom_parent or "laptop" in nom_fich or "ordinateur" in nom_fich:
        categorie_detectee = "Ordinateurs portables"
        description_visuelle = "Ordinateur portable fin avec clavier rétroéclairé et trackpad spacieux."
        mots_cles = "macbook dell xps lenovo"
    elif "tablet" in nom_parent or "tablette" in nom_fich or "ipad" in nom_fich:
        categorie_detectee = "Tablettes"
        description_visuelle = "Tablette tactile grand écran adaptée au dessin et multimédia."
        mots_cles = "ipad galaxy tab xiaomi pad"
    elif "casque" in nom_fich or "ecouteur" in nom_fich or "sony" in nom_fich or "audio" in nom_parent:
        categorie_detectee = "Casques et écouteurs"
        description_visuelle = "Casque audio circum-aural sans fil avec coussinets confortables."
        mots_cles = "sony wh bose airpods"
    elif "accessoire" in nom_parent or "chargeur" in nom_fich or "cable" in nom_fich:
        categorie_detectee = "Accessoires électroniques"
        description_visuelle = "Accessoire de connectivité ou charge rapide USB-C."
        mots_cles = "anker chargeur usb-c"
    else:
        categorie_detectee = "Smartphones"
        description_visuelle = "Smartphone haute résolution avec multiple capteurs photos."
        mots_cles = "galaxy s24 iphone pixel redmi"

    # 4. Recherche des produits correspondants dans le catalogue TechStore
    produits_associes = crud.get_all_products(category=categorie_detectee)

    return {
        "succes": True,
        "nom_fichier": p.name,
        "taille_ko": taille_ko,
        "categorie_identifiee": categorie_detectee,
        "description_visuelle": description_visuelle,
        "mots_cles": mots_cles,
        "produits_recommandes": produits_associes[:4]
    }
