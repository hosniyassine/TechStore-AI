import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from main import app
import multimedia

client = TestClient(app)


def test_wer_normalization_and_calculation():
    ref = "Ma facture est de 89 euros"
    hyp = "ma facture est de 89 €"
    # Grâce à la normalisation de l'atelier 3, "89 €" devient "89 euros"
    assert multimedia.normaliser_texte_wer(hyp) == "ma facture est de 89 euros"
    assert multimedia.calculer_wer(ref, hyp) == 0.0


def test_audio_format_validation_415():
    # Un fichier non-MP3 doit être rejeté avec 415
    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        f.write(b"data")
        f.flush()
        valide, code, msg = multimedia.valider_fichier_audio(f.name)
        assert valide is False
        assert code == 415


def test_audio_empty_file_400():
    with tempfile.NamedTemporaryFile(suffix=".mp3") as f:
        f.flush()
        valide, code, msg = multimedia.valider_fichier_audio(f.name)
        assert valide is False
        assert code == 400


def test_audio_too_large_413():
    # Simulation d'un fichier trop grand
    with tempfile.NamedTemporaryFile(suffix=".mp3") as f:
        f.seek(multimedia.MAX_AUDIO_SIZE_BYTES + 10)
        f.write(b"0")
        f.flush()
        valide, code, msg = multimedia.valider_fichier_audio(f.name)
        assert valide is False
        assert code == 413


def test_image_format_validation_415():
    with tempfile.NamedTemporaryFile(suffix=".bmp") as f:
        f.write(b"data")
        f.flush()
        valide, code, msg = multimedia.valider_fichier_image(f.name)
        assert valide is False
        assert code == 415


def test_audio_endpoint_upload():
    # Test avec un fichier MP3 synthétique valide
    with tempfile.NamedTemporaryFile(suffix=".mp3") as f:
        f.write(b"\xFF\xFB\x90\x44" + b"\x00" * 500)  # En-tête MP3 minimal
        f.flush()
        with open(f.name, "rb") as upload_file:
            r = client.post("/api/multimedia/audio", files={"file": ("smartphone_question.mp3", upload_file, "audio/mpeg")})
            assert r.status_code == 200
            data = r.json()
            assert data["succes"] is True
            assert "transcription" in data
            assert "reponse_agent" in data


def test_image_endpoint_upload():
    from PIL import Image
    import io
    # Création d'une image PNG valide en mémoire
    img = Image.new("RGB", (100, 100), color="blue")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)

    r = client.post("/api/multimedia/image", files={"file": ("laptop_test.png", img_byte_arr, "image/png")})
    assert r.status_code == 200
    data = r.json()
    assert data["succes"] is True
    assert "categorie_identifiee" in data
    assert "produits_recommandes" in data
