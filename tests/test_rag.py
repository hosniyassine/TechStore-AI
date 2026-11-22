import pytest
import rag


def test_rag_passages_loading():
    passages = rag.charger_passages()
    assert len(passages) >= 16
    sources = set(p["source"] for p in passages)
    assert "smartphones.pdf" in sources
    assert "laptops.pdf" in sources
    assert "garantie.pdf" in sources
    assert "retour.pdf" in sources


def test_rag_retrieval():
    passages = rag.rechercher_passages("Quelle est la durée de la garantie légale ?", k=3)
    assert len(passages) == 3
    # Le passage P09 (garantie) doit être retrouvé dans les 3 premiers
    top_ids = [p["id"] for p in passages]
    assert "P09" in top_ids


def test_rag_generation_sufficient():
    passages = rag.rechercher_passages("Combien coûte le MacBook Air M3 ?", k=3)
    reponse = rag.repondre_rag("Combien coûte le MacBook Air M3 ?", passages)
    assert reponse["suffisant"] is True
    assert len(reponse["sources"]) > 0
    assert "1299" in reponse["reponse"] or "P05" in reponse["reponse"]


def test_rag_generation_insufficient_refusal():
    # Question hors base : le système doit refuser explicitement avec la formule du TP4
    passages = rag.rechercher_passages("Vendez-vous des machines à café Nespresso ?", k=3)
    reponse = rag.repondre_rag("Vendez-vous des machines à café Nespresso ?", passages)
    assert reponse["suffisant"] is False
    assert reponse["reponse"] == "Information insuffisante dans les documents disponibles."


def test_rag_metrics_calculation():
    attendus = [["P01"], ["P02"]]
    trouves_parfait = [["P01", "P03", "P04"], ["P02", "P05", "P06"]]
    assert rag.recall_at_k(attendus, trouves_parfait, k=1) == 1.0
    assert rag.mrr(attendus, trouves_parfait) == 1.0

    trouves_deuxieme = [["P03", "P01", "P04"], ["P05", "P02", "P06"]]
    assert rag.recall_at_k(attendus, trouves_deuxieme, k=1) == 0.0
    assert rag.recall_at_k(attendus, trouves_deuxieme, k=2) == 1.0
    assert rag.mrr(attendus, trouves_deuxieme) == 0.5
