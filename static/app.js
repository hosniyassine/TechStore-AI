document.addEventListener("DOMContentLoaded", () => {
    // Initialisation
    initTabs();
    chargerInfosSysteme();
    chargerProduits();
    chargerCommandes();
    chargerMetriquesDashboard();
    initAssistant();
    initModals();
});

// ==========================================
// NAVIGATION PAR ONGLETS
// ==========================================
function initTabs() {
    const navButtons = document.querySelectorAll(".nav-btn");
    navButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            navButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            document.querySelectorAll(".tab-content").forEach(content => {
                content.classList.remove("active");
            });
            const activeSection = document.getElementById(`tab-${targetTab}`);
            if (activeSection) {
                activeSection.classList.add("active");
            }

            // Rafraîchir les données selon l'onglet
            if (targetTab === "products") chargerProduits();
            if (targetTab === "orders") chargerCommandes();
            if (targetTab === "dashboard") chargerMetriquesDashboard();
        });
    });
}

// ==========================================
// INFOS SYSTÈME ET DASHBOARD
// ==========================================
async function chargerInfosSysteme() {
    try {
        const res = await fetch("/api/info");
        const data = await res.json();
        document.getElementById("badge-mode").textContent = `Mode : ${data.mode.toUpperCase()}`;
        document.getElementById("badge-provider").textContent = `Fournisseur : ${data.provider}`;
        document.getElementById("stat-products").textContent = data.total_produits;
        document.getElementById("stat-orders").textContent = data.total_commandes;
    } catch (e) {
        console.error("Erreur chargement info système", e);
    }
}

async function chargerMetriquesDashboard() {
    try {
        // TP2 Classification
        const resClass = await fetch("/api/classification/metrics");
        const dataClass = await resClass.json();
        if (dataClass.variante_1 && dataClass.variante_2) {
            document.getElementById("metric-class-zero").textContent = `${dataClass.variante_1.bons_exemples}/25 (${(dataClass.variante_1.accuracy * 100).toFixed(1)}%)`;
            document.getElementById("metric-class-few").textContent = `${dataClass.variante_2.bons_exemples}/25 (${(dataClass.variante_2.accuracy * 100).toFixed(1)}%)`;
            document.getElementById("stat-accuracy").textContent = `${(dataClass.variante_2.accuracy * 100).toFixed(1)}%`;
            document.getElementById("classification-summary").textContent = dataClass.conclusion || "Évaluation comparative à 1 variable terminée.";
        }

        // TP4 RAG
        const resRag = await fetch("/api/rag/metrics");
        const dataRag = await resRag.json();
        if (dataRag.recherche && dataRag.generation) {
            document.getElementById("stat-rag").textContent = dataRag.recherche.mrr || "0.883";
            document.getElementById("metric-rag-recalls").textContent = `${dataRag.recherche["recall@1"]} / ${dataRag.recherche["recall@3"]}`;
            document.getElementById("metric-rag-refus").textContent = `${dataRag.generation.refus_corrects}/${dataRag.generation.questions_hors_base} (${(dataRag.generation.taux_refus_corrects * 100).toFixed(0)}%)`;
        }
    } catch (e) {
        console.error("Erreur métriques dashboard", e);
    }
}

// ==========================================
// GESTION DES PRODUITS (CRUD)
// ==========================================
let tousLesProduits = [];

async function chargerProduits() {
    const search = document.getElementById("filter-search").value.trim();
    const category = document.getElementById("filter-category").value;
    const maxPrice = document.getElementById("filter-max-price").value;

    let url = "/api/products?";
    if (search) url += `search=${encodeURIComponent(search)}&`;
    if (category) url += `category=${encodeURIComponent(category)}&`;
    if (maxPrice) url += `max_price=${encodeURIComponent(maxPrice)}&`;

    try {
        const res = await fetch(url);
        tousLesProduits = await res.json();
        afficherProduitsTable(tousLesProduits);
        remplirSelectProduits(tousLesProduits);
    } catch (e) {
        console.error("Erreur chargement produits", e);
    }
}

function afficherProduitsTable(produits) {
    const tbody = document.getElementById("products-table-body");
    tbody.innerHTML = "";

    if (produits.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding: 2rem; color: #64748b;">Aucun produit trouvé.</td></tr>`;
        return;
    }

    produits.forEach(p => {
        const tr = document.createElement("tr");
        const stockClass = p.stock === 0 ? "status-annulee" : (p.stock < 5 ? "status-en_attente" : "status-confirmee");
        tr.innerHTML = `
            <td><strong>${p.id}</strong></td>
            <td><strong>${escapeHtml(p.name)}</strong><br><small style="color:#64748b;">${escapeHtml(p.description.substring(0, 50))}...</small></td>
            <td>${escapeHtml(p.brand)}</td>
            <td><span class="tag tag-blue">${escapeHtml(p.category)}</span></td>
            <td><strong>${p.price.toFixed(2)} €</strong></td>
            <td>${escapeHtml(p.ram)} / ${escapeHtml(p.storage)}</td>
            <td><span class="status-badge ${stockClass}">${p.stock} en stock</span></td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="editerProduit('${p.id}')">✏️</button>
                <button class="btn btn-sm btn-secondary" style="color:#dc2626;" onclick="supprimerProduit('${p.id}')">🗑️</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function remplirSelectProduits(produits) {
    const select = document.getElementById("order-form-product");
    if (!select) return;
    select.innerHTML = "";
    produits.forEach(p => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = `${p.id} — ${p.name} (${p.price.toFixed(2)} €, stock: ${p.stock})`;
        select.appendChild(opt);
    });
}

// Filtres
document.getElementById("filter-search").addEventListener("input", debounce(chargerProduits, 300));
document.getElementById("filter-category").addEventListener("change", chargerProduits);
document.getElementById("filter-max-price").addEventListener("input", debounce(chargerProduits, 300));
document.getElementById("btn-reset-filters").addEventListener("click", () => {
    document.getElementById("filter-search").value = "";
    document.getElementById("filter-category").value = "";
    document.getElementById("filter-max-price").value = "";
    chargerProduits();
});

// Supprimer produit
window.supprimerProduit = async function(id) {
    if (!confirm(`Confirmez-vous la suppression du produit ${id} ?`)) return;
    try {
        const res = await fetch(`/api/products/${id}`, { method: "DELETE" });
        if (res.ok) {
            chargerProduits();
            chargerInfosSysteme();
        } else {
            const err = await res.json();
            alert("Erreur : " + err.detail);
        }
    } catch (e) {
        alert("Erreur réseau");
    }
};

// Éditer produit
window.editerProduit = function(id) {
    const p = tousLesProduits.find(item => item.id === id);
    if (!p) return;

    document.getElementById("modal-product-title").textContent = `Modifier le produit ${p.id}`;
    document.getElementById("prod-form-id").value = p.id;
    document.getElementById("prod-form-name").value = p.name;
    document.getElementById("prod-form-brand").value = p.brand;
    document.getElementById("prod-form-category").value = p.category;
    document.getElementById("prod-form-price").value = p.price;
    document.getElementById("prod-form-stock").value = p.stock;
    document.getElementById("prod-form-ram").value = p.ram || "N/A";
    document.getElementById("prod-form-storage").value = p.storage || "N/A";
    document.getElementById("prod-form-description").value = p.description;

    document.getElementById("modal-product").classList.add("active");
};

// Formulaire Produit (Ajout ou Modification)
document.getElementById("form-product").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("prod-form-id").value;
    const body = {
        name: document.getElementById("prod-form-name").value.trim(),
        brand: document.getElementById("prod-form-brand").value.trim(),
        category: document.getElementById("prod-form-category").value,
        price: parseFloat(document.getElementById("prod-form-price").value),
        stock: parseInt(document.getElementById("prod-form-stock").value),
        ram: document.getElementById("prod-form-ram").value.trim() || "N/A",
        storage: document.getElementById("prod-form-storage").value.trim() || "N/A",
        description: document.getElementById("prod-form-description").value.trim(),
    };

    try {
        let res;
        if (id) {
            res = await fetch(`/api/products/${id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body)
            });
        } else {
            res = await fetch("/api/products", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body)
            });
        }

        if (res.ok) {
            document.getElementById("modal-product").classList.remove("active");
            chargerProduits();
            chargerInfosSysteme();
        } else {
            const err = await res.json();
            alert("Erreur : " + (err.detail || JSON.stringify(err)));
        }
    } catch (e) {
        alert("Erreur réseau");
    }
});

// ==========================================
// GESTION DES COMMANDES
// ==========================================
async function chargerCommandes() {
    try {
        const res = await fetch("/api/orders");
        const commandes = await res.json();
        const tbody = document.getElementById("orders-table-body");
        tbody.innerHTML = "";

        if (commandes.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2rem; color: #64748b;">Aucune commande enregistrée.</td></tr>`;
            return;
        }

        commandes.forEach(c => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${c.id}</strong></td>
                <td>${escapeHtml(c.product_name)} <small style="color:#64748b;">(${c.product_id})</small></td>
                <td><strong>${c.quantity}</strong></td>
                <td><strong>${c.total_price.toFixed(2)} €</strong></td>
                <td><span class="status-badge status-${c.status}">${c.status}</span></td>
                <td><small>${new Date(c.created_at).toLocaleDateString()} ${new Date(c.created_at).toLocaleTimeString()}</small></td>
                <td>
                    <select class="input-field input-sm" onchange="changerStatutCommande('${c.id}', this.value)">
                        <option value="confirmee" ${c.status === "confirmee" ? "selected" : ""}>Confirmer</option>
                        <option value="en_attente" ${c.status === "en_attente" ? "selected" : ""}>En attente</option>
                        <option value="livree" ${c.status === "livree" ? "selected" : ""}>Livrée</option>
                        <option value="annulee" ${c.status === "annulee" ? "selected" : ""}>Annuler</option>
                    </select>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Erreur chargement commandes", e);
    }
}

window.changerStatutCommande = async function(orderId, newStatus) {
    try {
        const res = await fetch(`/api/orders/${orderId}/status`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: newStatus })
        });
        if (res.ok) {
            chargerCommandes();
            chargerProduits();
        } else {
            const err = await res.json();
            alert("Erreur : " + err.detail);
        }
    } catch (e) {
        alert("Erreur réseau");
    }
};

// Formulaire création commande
document.getElementById("form-order").addEventListener("submit", async (e) => {
    e.preventDefault();
    const pid = document.getElementById("order-form-product").value;
    const qty = parseInt(document.getElementById("order-form-qty").value);
    const confirmed = document.getElementById("order-form-confirmed").checked;
    const feedbackBox = document.getElementById("order-feedback");

    feedbackBox.style.display = "block";
    feedbackBox.style.background = "#eff6ff";
    feedbackBox.style.color = "#1e40af";
    feedbackBox.textContent = "Traitement de la commande en cours...";

    try {
        const res = await fetch("/api/orders", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ product_id: pid, quantity: qty, confirmed: confirmed })
        });
        const data = await res.json();

        if (res.ok) {
            if (data.statut === "confirmation_requise") {
                feedbackBox.style.background = "#fffbeb";
                feedbackBox.style.color = "#92400e";
                feedbackBox.innerHTML = `⚠️ <strong>Confirmation exigée :</strong><br>${data.message}`;
            } else if (data.statut === "succes") {
                feedbackBox.style.background = "#dcfce7";
                feedbackBox.style.color = "#166534";
                feedbackBox.innerHTML = `✅ <strong>Succès :</strong> ${data.message} (Stock restant: ${data.nouveau_stock})`;
                chargerCommandes();
                chargerProduits();
                chargerInfosSysteme();
                setTimeout(() => {
                    document.getElementById("modal-order").classList.remove("active");
                    feedbackBox.style.display = "none";
                }, 2000);
            }
        } else {
            feedbackBox.style.background = "#fee2e2";
            feedbackBox.style.color = "#991b1b";
            feedbackBox.textContent = "Erreur : " + (data.detail || "Échec création");
        }
    } catch (e) {
        feedbackBox.style.background = "#fee2e2";
        feedbackBox.style.color = "#991b1b";
        feedbackBox.textContent = "Erreur de connexion";
    }
});

// ==========================================
// ASSISTANT IA & MULTIMÉDIA
// ==========================================
function initAssistant() {
    const sendBtn = document.getElementById("btn-send-message");
    const textarea = document.getElementById("chat-textarea");
    const modeSelect = document.getElementById("select-ai-mode");

    modeSelect.addEventListener("change", () => {
        const mode = modeSelect.value;
        const label = document.getElementById("assistant-mode-label");
        if (mode === "agent") label.textContent = "Mode : Agent avec Tools (TP5)";
        if (mode === "rag") label.textContent = "Mode : RAG Documentaire (TP4)";
        if (mode === "classify") label.textContent = "Mode : Classification Seule (TP2)";
    });

    sendBtn.addEventListener("click", envoyerMessage);
    textarea.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            envoyerMessage();
        }
    });

    document.getElementById("btn-clear-chat").addEventListener("click", () => {
        const container = document.getElementById("chat-messages");
        container.innerHTML = `
            <div class="message message-bot">
                <div class="message-bubble">
                    Historique effacé. Comment puis-je vous aider ?
                </div>
            </div>
        `;
        document.getElementById("rag-sources-container").innerHTML = `<p class="text-muted">Les sources citées apparaîtront ici.</p>`;
        document.getElementById("tools-calls-container").innerHTML = `<p class="text-muted">Aucun outil exécuté pour le moment.</p>`;
    });

    // Audio upload
    const audioInput = document.getElementById("audio-file-input");
    audioInput.addEventListener("change", async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        await envoyerAudio(file);
        audioInput.value = "";
    });

    // Image upload
    const imageInput = document.getElementById("image-file-input");
    imageInput.addEventListener("change", async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        await envoyerImage(file);
        imageInput.value = "";
    });
}

function ajouterMessage(texte, emetteur = "user") {
    const container = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.className = `message message-${emetteur}`;
    div.innerHTML = `<div class="message-bubble">${escapeHtml(texte).replace(/\n/g, "<br>")}</div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

async function envoyerMessage() {
    const textarea = document.getElementById("chat-textarea");
    const texte = textarea.value.trim();
    if (!texte) return;

    textarea.value = "";
    ajouterMessage(texte, "user");

    const mode = document.getElementById("select-ai-mode").value;

    try {
        if (mode === "agent") {
            const res = await fetch("/api/agent/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: texte })
            });
            const data = await res.json();
            ajouterMessage(data.reponse, "bot");
            afficherOutilsExecutes(data.appels);
        } else if (mode === "rag") {
            const res = await fetch("/api/rag/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question: texte, k: 3 })
            });
            const data = await res.json();
            ajouterMessage(data.reponse, "bot");
            afficherSourcesRag(data.passages, data.sources);
        } else {
            const res = await fetch("/api/classify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: texte })
            });
            const data = await res.json();
            const rep = `Catégorie identifiée : [${data.category.toUpperCase()}] (Confiance : ${(data.confidence * 100).toFixed(1)}%, Revue requise : ${data.requires_review ? 'OUI' : 'NON'})`;
            ajouterMessage(rep, "bot");
        }
    } catch (e) {
        ajouterMessage("Erreur lors de la communication avec le serveur.", "bot");
    }
}

function afficherOutilsExecutes(appels) {
    const container = document.getElementById("tools-calls-container");
    if (!appels || appels.length === 0) {
        container.innerHTML = `<p class="text-muted">Aucun outil requis pour cette réponse.</p>`;
        return;
    }
    container.innerHTML = "";
    appels.forEach(a => {
        const div = document.createElement("div");
        div.className = "tool-badge";
        div.innerHTML = `
            <strong>⚡ ${a.outil}</strong>
            <div class="tool-args">args: ${escapeHtml(JSON.stringify(a.arguments))}</div>
        `;
        container.appendChild(div);
    });
}

function afficherSourcesRag(passages, sourcesCites) {
    const container = document.getElementById("rag-sources-container");
    if (!passages || passages.length === 0) {
        container.innerHTML = `<p class="text-muted">Aucun passage trouvé.</p>`;
        return;
    }
    container.innerHTML = "";
    passages.forEach(p => {
        const isCited = sourcesCites.includes(p.id);
        const div = document.createElement("div");
        div.className = "source-item";
        div.style.borderColor = isCited ? "var(--primary)" : "#e2e8f0";
        div.innerHTML = `
            <div class="source-tag">[${p.id}] ${escapeHtml(p.titre)} ${isCited ? "⭐ Citée" : ""} (Score: ${p.score})</div>
            <p style="font-size:0.75rem; color:#475569; margin-top:0.2rem;">${escapeHtml(p.texte.substring(0, 110))}...</p>
        `;
        container.appendChild(div);
    });
}

// Upload Audio MP3
async function envoyerAudio(file) {
    ajouterMessage(`🎙️ Envoi du fichier audio : ${file.name} (${(file.size / 1024).toFixed(1)} Ko)...`, "user");
    const formData = new FormData();
    formData.append("file", file);

    const multimediaBox = document.getElementById("multimedia-result-box");
    multimediaBox.innerHTML = `<em>Traitement audio Whisper ASR en cours...</em>`;

    try {
        const res = await fetch("/api/multimedia/audio", {
            method: "POST",
            body: formData
        });
        const data = await res.json();

        if (res.ok) {
            ajouterMessage(`🗣️ Transcription : "${data.transcription}"`, "bot");
            ajouterMessage(`🤖 Réponse : ${data.reponse_agent}`, "bot");
            multimediaBox.innerHTML = `
                <div class="source-item">
                    <strong>Fichier audio :</strong> ${escapeHtml(data.nom_fichier)}<br>
                    <strong>Taille :</strong> ${data.taille_ko} Ko<br>
                    <strong>Latence ASR :</strong> ${data.latence_transcription_ms} ms<br>
                    <strong>Latence totale :</strong> ${data.latence_totale_ms} ms
                </div>
            `;
            if (data.appels_outils) afficherOutilsExecutes(data.appels_outils);
        } else {
            ajouterMessage(`❌ Erreur audio (${res.status}) : ${data.detail || "Échec"}`, "bot");
            multimediaBox.innerHTML = `<span style="color:#dc2626;">Erreur ${res.status} : ${data.detail}</span>`;
        }
    } catch (e) {
        ajouterMessage("Erreur réseau lors de l'envoi de l'audio.", "bot");
    }
}

// Upload Image
async function envoyerImage(file) {
    ajouterMessage(`📷 Envoi de l'image produit : ${file.name} (${(file.size / 1024).toFixed(1)} Ko)...`, "user");
    const formData = new FormData();
    formData.append("file", file);

    const multimediaBox = document.getElementById("multimedia-result-box");
    multimediaBox.innerHTML = `<em>Analyse d'image par vision multimodale...</em>`;

    try {
        const res = await fetch("/api/multimedia/image", {
            method: "POST",
            body: formData
        });
        const data = await res.json();

        if (res.ok) {
            ajouterMessage(`🔍 Produit détecté : [${data.categorie_identifiee}] — ${data.description_visuelle}`, "bot");
            let recs = data.produits_recommandes.map(p => `• ${p.name} (${p.price} €)`).join("<br>");
            ajouterMessage(`Voici les modèles correspondants dans notre boutique :<br>${recs}`, "bot");

            multimediaBox.innerHTML = `
                <div class="source-item">
                    <strong>Image :</strong> ${escapeHtml(data.nom_fichier)}<br>
                    <strong>Catégorie :</strong> <span class="tag tag-blue">${data.categorie_identifiee}</span><br>
                    <strong>Produits suggérés :</strong> ${data.produits_recommandes.length} trouvés
                </div>
            `;
        } else {
            ajouterMessage(`❌ Erreur image (${res.status}) : ${data.detail || "Échec"}`, "bot");
            multimediaBox.innerHTML = `<span style="color:#dc2626;">Erreur ${res.status} : ${data.detail}</span>`;
        }
    } catch (e) {
        ajouterMessage("Erreur réseau lors de l'envoi de l'image.", "bot");
    }
}

// ==========================================
// GESTION DES MODALS
// ==========================================
function initModals() {
    // Modal Produit
    const modalProd = document.getElementById("modal-product");
    document.getElementById("btn-open-add-product").addEventListener("click", () => {
        document.getElementById("modal-product-title").textContent = "Ajouter un produit";
        document.getElementById("form-product").reset();
        document.getElementById("prod-form-id").value = "";
        modalProd.classList.add("active");
    });
    document.getElementById("btn-close-product-modal").addEventListener("click", () => modalProd.classList.remove("active"));
    document.getElementById("btn-cancel-product").addEventListener("click", () => modalProd.classList.remove("active"));

    // Modal Commande
    const modalOrder = document.getElementById("modal-order");
    document.getElementById("btn-open-create-order").addEventListener("click", () => {
        document.getElementById("form-order").reset();
        document.getElementById("order-feedback").style.display = "none";
        modalOrder.classList.add("active");
    });
    document.getElementById("btn-close-order-modal").addEventListener("click", () => modalOrder.classList.remove("active"));
    document.getElementById("btn-cancel-order").addEventListener("click", () => modalOrder.classList.remove("active"));

    window.addEventListener("click", (e) => {
        if (e.target === modalProd) modalProd.classList.remove("active");
        if (e.target === modalOrder) modalOrder.classList.remove("active");
    });
}

// Utilitaires
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
