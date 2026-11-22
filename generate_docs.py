import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import crud

DOCS_DIR = os.path.join(os.path.dirname(__file__), "data", "documents")
os.makedirs(DOCS_DIR, exist_ok=True)


def generer_pdf(nom_fichier: str, titre_doc: str, sections: list):
    """Génère un fichier PDF professionnel et lisible avec ReportLab."""
    chemin = os.path.join(DOCS_DIR, nom_fichier)
    doc = SimpleDocTemplate(chemin, pagesize=letter, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()

    style_titre = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor('#1e3a8a'))
    style_section = ParagraphStyle('SecTitle', parent=styles['Heading2'], fontSize=13, leading=16, textColor=colors.HexColor('#2563eb'), spaceBefore=12, spaceAfter=6)
    style_corps = ParagraphStyle('BodyTextCustom', parent=styles['Normal'], fontSize=10, leading=14, textColor=colors.HexColor('#1f2937'))

    elements = [
        Paragraph(titre_doc, style_titre),
        Spacer(1, 15)
    ]

    for sec in sections:
        elements.append(Paragraph(sec["titre"], style_section))
        elements.append(Paragraph(sec["texte"], style_corps))
        elements.append(Spacer(1, 10))

    doc.build(elements)
    print(f"Généré : {chemin}")


def generer_tous_les_documents():
    """Génère automatiquement les 4 documents officiels de TechStore AI."""
    produits = crud.get_all_products()

    # 1. SMARTPHONES.PDF
    smartphones = [p for p in produits if p.get("category") == "Smartphones"]
    sec_smartphones = []
    for sp in smartphones:
        sec_smartphones.append({
            "titre": f"## {sp['name']} ({sp['id']})",
            "texte": f"Marque : {sp['brand']}. Prix officiel : {sp['price']:.2f} € TTC. "
                     f"Mémoire RAM : {sp['ram']}. Stockage interne : {sp['storage']}. "
                     f"Description technique : {sp['description']} "
                     f"Disponibilité en magasin : {sp['stock']} unités en stock."
        })
    generer_pdf("smartphones.pdf", "TechStore AI — Catalogue Officiel des Smartphones", sec_smartphones)

    # 2. LAPTOPS.PDF
    laptops = [p for p in produits if p.get("category") == "Ordinateurs portables"]
    sec_laptops = []
    for lp in laptops:
        sec_laptops.append({
            "titre": f"## {lp['name']} ({lp['id']})",
            "texte": f"Marque : {lp['brand']}. Prix officiel : {lp['price']:.2f} € TTC. "
                     f"Mémoire RAM : {lp['ram']}. Stockage SSD : {lp['storage']}. "
                     f"Description technique : {lp['description']} "
                     f"Disponibilité en magasin : {lp['stock']} unités en stock."
        })
    generer_pdf("laptops.pdf", "TechStore AI — Catalogue Officiel des Ordinateurs Portables", sec_laptops)

    # 3. GARANTIE.PDF
    sec_garantie = [
        {
            "titre": "## Durée légale et contractuelle de garantie",
            "texte": "Tous les produits électroniques neufs vendus chez TechStore AI bénéficient de la garantie légale de conformité d'une durée stricte de 2 ans (24 mois) à compter de la date de livraison. Pour les ordinateurs portables Apple et Dell, une extension de garantie 'TechStore Care+' de 1 an supplémentaire (soit 3 ans au total) est disponible en option pour 129 euros."
        },
        {
            "titre": "## Couverture de la garantie",
            "texte": "La garantie couvre intégralement les pannes matérielles, défauts de fabrication de la carte mère, dysfonctionnements spontanés de l'écran (pixels morts hors chocs) et les défaillances de batterie si sa capacité descend sous 80% au cours de la première année. Les réparations sont effectuées avec des pièces d'origine certifiées."
        },
        {
            "titre": "## Exclusions formelles de garantie",
            "texte": "La garantie ne s'applique pas en cas d'oxydation ou d'immersion dans un liquide (même pour les appareils certifiés IP68), de casse d'écran consécutive à une chute ou un choc mécanique, d'ouverture ou modification non autorisée de l'appareil, ou d'utilisation d'un chargeur non homologué."
        },
        {
            "titre": "## Procédure de prise en charge SAV",
            "texte": "Pour activer la garantie, le client doit présenter sa facture d'achat ou son numéro de commande (ex: CMD-1001). Le diagnostic technique initial est réalisé sous 48 heures ouvrées en magasin ou par retour atelier. Si le produit n'est pas réparable sous 15 jours calendaires, un échange à neuf ou un avoir immédiat est délivré."
        }
    ]
    generer_pdf("garantie.pdf", "TechStore AI — Politique et Conditions de Garantie SAV", sec_garantie)

    # 4. RETOUR.PDF
    sec_retour = [
        {
            "titre": "## Délai légal de rétractation",
            "texte": "Conformément à la réglementation européenne sur le commerce électronique, vous disposez d'un délai légal de 14 jours calendaires à compter de la réception de votre colis pour exercer votre droit de rétractation, sans justification nécessaire ni pénalité."
        },
        {
            "titre": "## État exigé des produits retournés",
            "texte": "Le produit retourné doit être dans son état neuf complet, non endommagé, réinitialisé sans compte utilisateur verrouillé (compte Apple iCloud ou Google dissocié), dans son emballage d'origine intact avec tous les câbles, manuels et accessoires fournis. Les écouteurs intra-auriculaires descellés ne peuvent être repris pour des raisons strictes d'hygiène."
        },
        {
            "titre": "## Modalités et frais de retour",
            "texte": "Les retours sont totalement gratuits en point relais partenaire en utilisant le bon de retour prépayé généré depuis votre espace client. Si le client choisit un envoi postal express par ses propres moyens, les frais postaux restent à sa charge."
        },
        {
            "titre": "## Délais et moyens de remboursement",
            "texte": "Le remboursement complet du produit et des frais de livraison standard initiaux est effectué dans un délai de 5 à 7 jours ouvrés après réception et vérification de conformité du produit retourné dans notre entrepôt. Le remboursement s'effectue automatiquement sur le même moyen de paiement que celui utilisé lors de la commande."
        }
    ]
    generer_pdf("retour.pdf", "TechStore AI — Conditions de Retour et de Rétractation", sec_retour)


if __name__ == "__main__":
    generer_tous_les_documents()
