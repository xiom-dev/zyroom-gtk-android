// ZyRoom-web : la page. Elle reproduit l'ecran de ZyRoom-GTK (window.py) ;
// la lecture des flux, les noms, les categories et les tris sont ceux de
// l'application, executes par Pyodide dans travail.js (pont outils/zr_web.py).
//
// Ce qui vient d'ou :
// - un personnage : https://api.ryzom.com/character.php, avec la cle que le
//   joueur a collee ; elle reste dans son navigateur ;
// - le hall de guilde : zyroom.php, qui garde la cle de la guilde et ne
//   repond qu'a un membre connecte (meme jeton que la page des MP) ;
// - la saison : time.php de l'API ; le redemarrage : zyroom.php?quoi=statut
//   (le serveur de Ryzom ne laisse pas une page web le lire directement).
(function () {
"use strict";

const $ = (s) => document.querySelector(s);
const API = "https://api.ryzom.com";
const GUILDE = { sorte: "guild", id: "105906237", nom: "La Lune Eternelle" };
// Comme Settings.PALIERS_ZOOM et ICONE_NORMALE.
const PALIERS = [80, 100, 120, 140, 160, 180, 200];
const ICONE = 48;
const TRIS = ["Ordre d'origine", "Type", "Écosystème", "Classe", "Qualité", "Volume",
              "Quantité", "Prix", "Nom"];
// Comme window.IMAGES_CONTENANTS.
const IMAGES = [["bag", "sac.png"], ["room", "appartement.png"], ["chest", "coffre.png"]];

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;",
    '"': "&quot;", "'": "&#39;" }[c]));
}
function lire(cle, defaut) {
  try { const v = localStorage.getItem(cle); return v ? JSON.parse(v) : defaut; } catch (e) { return defaut; }
}
function garder(cle, valeur) {
  try { localStorage.setItem(cle, JSON.stringify(valeur)); } catch (e) {}
}
// Comme ui_commun._norm : minuscule sans accents.
function norm(t) { return t.normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase(); }
const deux = (n) => String(n).padStart(2, "0");

// ------------------------------------------------------------ worker

const travail = new Worker("travail.js" + (document.currentScript ? new URL(document.currentScript.src).search : ""));
let numero = 0;
const attentes = new Map();
travail.onmessage = (ev) => {
  const d = ev.data;
  const a = attentes.get(d.id);
  attentes.delete(d.id);
  if (a) { if (d.ok) a.ok(d.valeur); else a.ko(new Error(d.erreur)); }
};
function appeler(op, ...args) {
  return new Promise((ok, ko) => {
    const id = ++numero;
    attentes.set(id, { ok, ko });
    travail.postMessage({ id, op, args });
  });
}

// ------------------------------------------------------------ etat

const Z = {
  // Le jeton de la page des MP, tel qu'elle le range (texte brut, pas JSON).
  jeton: (() => { try { return localStorage.getItem("mp-jeton") || ""; } catch (e) { return ""; } })(),
  pret: false,
  meta: null,
  persos: lire("zr-persos", []),
  courante: lire("zr-entite", ""),
  ent: null,
  contenant: 0,
  synchro: new Set(),
  page: "inventaire",
  cherche: "",
  tri: lire("zr-tri", [1, false]),
  zoom: lire("zr-zoom", 100),
  f: null,
  categories: [],
  attentes: 0,
  // Le dernier perso et la derniere guilde vus : Competences et Effectif
  // s'ouvrent quelle que soit l'entite choisie (page_skills, page_roster).
  derniers: {},
};

function filtresVierges() {
  return { bonus: new Set([0, 1, 2, 3]), qmin: 0, qmax: 500, cadenas: false, avecBonus: false,
           vente: false, types: new Set(), classes: new Set([0, 1, 2, 3, 4, 5]),
           ecos: new Set([0, 1, 2, 3, 4, 5, 6]), equips: new Set([...Array(12).keys()]) };
}
Z.f = filtresVierges();

function entites() {
  return [...Z.persos.map((p) => ({ sorte: "character", id: p.id, nom: p.nom, cle: p.cle, image: p.image })),
          Object.assign({ image: lire("zr-image-guilde", "") }, GUILDE)];
}
function entiteCourante() {
  const liste = entites();
  return liste.find((e) => e.sorte + ":" + e.id === Z.courante) || liste[0];
}

function attendre(oui) {
  Z.attentes = Math.max(0, Z.attentes + (oui ? 1 : -1));
  $("#attente").hidden = Z.attentes === 0;
}

// ------------------------------------------------------------ connexion

function ouvrirPorte(message) {
  $("#porte-message").textContent = message || "";
  if (!$("#porte").open) $("#porte").showModal();
}
$("#porte-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  $("#porte-message").textContent = "Vérification…";
  try {
    const r = await fetch("../mp/mp.php", { method: "POST", cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "entrer", nom: $("#porte-nom").value, mdp: $("#porte-mdp").value }) });
    const rep = await r.json().catch(() => ({}));
    if (!r.ok) {
      $("#porte-message").textContent = rep.erreur === "nom ou mot de passe" ? "Pseudo ou mot de passe incorrect."
        : rep.erreur ? rep.erreur.charAt(0).toUpperCase() + rep.erreur.slice(1) + "." : "Refusé.";
      return;
    }
    Z.jeton = rep.jeton;
    try { localStorage.setItem("mp-jeton", Z.jeton); } catch (e) {}
    $("#porte-mdp").value = "";
    $("#porte").close();
    Z.synchro.clear();
    choisirEntite(Z.courante);
  } catch (souci) {
    $("#porte-message").textContent = "Serveur injoignable.";
  }
});
$("#porte").addEventListener("cancel", (ev) => ev.preventDefault());
$("#m-sortir").addEventListener("click", () => {
  Z.jeton = "";
  try { localStorage.removeItem("mp-jeton"); } catch (e) {}
  fermerPops();
  ouvrirPorte("Déconnecté.");
});

// ------------------------------------------------------------ flux

function cacheXml(e) { return "zr-xml-" + e.sorte + "-" + e.id; }

// Les flux de l'API vont dans IndexedDB : celui du hall pese pres d'un Mo,
// et le stockage simple du navigateur (localStorage) le refusait sans bruit.
const base = new Promise((ok, ko) => {
  try {
    const r = indexedDB.open("zyroom", 1);
    r.onupgradeneeded = () => r.result.createObjectStore("flux");
    r.onsuccess = () => ok(r.result);
    r.onerror = () => ko(r.error);
  } catch (er) { ko(er); }
});
async function fluxGarde(cle) {
  try {
    const db = await base;
    return await new Promise((ok) => {
      const r = db.transaction("flux").objectStore("flux").get(cle);
      r.onsuccess = () => ok(r.result || null);
      r.onerror = () => ok(null);
    });
  } catch (er) { return null; }
}
async function garderFlux(cle, valeur) {
  try {
    const db = await base;
    const t = db.transaction("flux", "readwrite").objectStore("flux");
    if (valeur === null) t.delete(cle); else t.put(valeur, cle);
  } catch (er) { /* un cache manquant se refait a la synchro */ }
}

async function telecharger(e) {
  if (e.sorte === "character") {
    const r = await fetch(API + "/character.php?apikey=" + encodeURIComponent(e.cle), { cache: "no-store" });
    if (!r.ok) throw new Error("API Ryzom " + r.status);
    return { xml: await r.text(), quand: Date.now() };
  }
  const r = await fetch("zyroom.php", { cache: "no-store", headers: { "X-MP": Z.jeton } });
  if (r.status === 401) { const e2 = new Error("401"); e2.porte = true; throw e2; }
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).erreur || "zyroom.php " + r.status);
  const releve = Number(r.headers.get("X-Releve")) * 1000;
  return { xml: await r.text(), quand: releve || Date.now() };
}

async function lireFlux(e, flux) {
  const ent = JSON.parse(await appeler("entite", flux.xml, e.sorte));
  if (ent.erreur) throw new Error(ent.erreur);
  ent.quand = flux.quand;
  return ent;
}

async function choisirEntite(code) {
  const liste = entites();
  const e = liste.find((x) => x.sorte + ":" + x.id === code) || liste[0];
  Z.courante = e.sorte + ":" + e.id;
  garder("zr-entite", Z.courante);
  dessinerEntites();
  $("#b-retrait").disabled = e.sorte !== "character";
  $("#b-synchro").disabled = false;
  if (!Z.pret) return;
  // Comme l'application : le cache s'affiche aussitot, puis on interroge
  // l'API la premiere fois qu'on ouvre l'entite dans la session.
  const garde = await fluxGarde(cacheXml(e));
  if (garde && garde.xml) {
    try { montrer(e, await lireFlux(e, garde), false); } catch (souci) { /* le flux frais suivra */ }
  } else {
    Z.ent = null;
    dessinerTout();
  }
  if (!Z.synchro.has(Z.courante)) synchroniser();
}

async function synchroniser() {
  const e = entiteCourante();
  Z.synchro.add(e.sorte + ":" + e.id);
  attendre(true);
  try {
    const flux = await telecharger(e);
    const ent = await lireFlux(e, flux);
    garderFlux(cacheXml(e), flux);
    await journaliser(e, flux.xml);
    if (Z.courante === e.sorte + ":" + e.id) montrer(e, ent, true);
  } catch (souci) {
    if (souci.porte) ouvrirPorte("Connexion requise.");
    else etat("Échec de la synchro : " + souci.message);
  } finally {
    attendre(false);
  }
}

function montrer(e, ent, frais) {
  const meme = Z.ent && Z.ent.sorte === ent.sorte && Z.ent.id === ent.id;
  const cle = meme && Z.ent.contenants[Z.contenant] ? Z.ent.contenants[Z.contenant].cle : null;
  Z.ent = ent;
  Z.derniers[ent.sorte] = ent;
  // Le contenant se retrouve par sa cle, pas par son rang (window._rang_du_contenant).
  Z.contenant = 0;
  if (cle) {
    const i = ent.contenants.findIndex((c) => c.cle === cle);
    if (i >= 0) Z.contenant = i;
  }
  // L'image de l'entite pour le menu : portrait du perso, embleme de la guilde.
  if (frais && ent.portrait) {
    if (e.sorte === "character") {
      const p = Z.persos.find((x) => x.id === e.id);
      if (p) { p.image = ent.portrait; p.nom = ent.nom; garder("zr-persos", Z.persos); }
    } else garder("zr-image-guilde", ent.portrait);
  }
  dessinerTout();
}

// ------------------------------------------------------------ menus deroulants

function fermerPops(sauf) {
  document.querySelectorAll(".pop").forEach((p) => { if (p !== sauf) p.hidden = true; });
}
document.addEventListener("click", (ev) => {
  if (!ev.target.closest(".menu, .choix, .filtres")) fermerPops();
});
document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") fermerPops(); });

// Un selecteur avec images, comme les Gtk.DropDown a fabrique de l'application.
function selecteur(zone, entrees, courant, choisi) {
  const actuel = entrees[courant] || { texte: "—" };
  zone.innerHTML = '<button type="button">' + (actuel.img ? '<img src="' + esc(actuel.img) + '" alt="">' : "")
    + "<span>" + esc(actuel.texte) + '</span><svg class="chevron" viewBox="0 0 24 24"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2"/></svg></button>'
    + '<div class="pop" hidden>' + entrees.map((x, i) => '<button type="button" data-i="' + i + '"'
      + (i === courant ? ' aria-current="true"' : "") + ">" + (x.img ? '<img src="' + esc(x.img) + '" alt="">' : '<span style="width:30px"></span>')
      + esc(x.texte) + "</button>").join("") + "</div>";
  const pop = zone.querySelector(".pop");
  zone.firstElementChild.onclick = () => { fermerPops(pop); pop.hidden = !pop.hidden; };
  pop.onclick = (ev) => {
    const b = ev.target.closest("[data-i]");
    if (!b) return;
    pop.hidden = true;
    choisi(Number(b.dataset.i));
  };
}

function dessinerEntites() {
  const liste = entites();
  const i = Math.max(0, liste.findIndex((e) => e.sorte + ":" + e.id === Z.courante));
  selecteur($("#choix-entite"), liste.map((e) => ({ img: e.image, texte: e.nom })), i,
            (n) => choisirEntite(liste[n].sorte + ":" + liste[n].id));
}

function imageContenant(c) {
  if (c.cle.startsWith("animal")) return "symboles/" + (/zig/i.test(c.nom) ? "zig.png" : "mektoub.png");
  const trouve = IMAGES.find(([p]) => c.cle.startsWith(p));
  return trouve ? "symboles/" + trouve[1] : "";
}
// Comme window._remplissage.
function remplissage(c) {
  return c.capacite > 0 ? " (" + Math.round(c.volume / c.capacite * 100) + "%)" : "";
}

function dessinerContenants() {
  const ent = Z.ent;
  const zone = $("#choix-contenant");
  if (!ent) { zone.innerHTML = ""; return; }
  selecteur(zone, ent.contenants.map((c) => ({ img: imageContenant(c), texte: c.nom + remplissage(c) })),
            Z.contenant, (n) => { Z.contenant = n; dessinerInventaire(); });
}

// ------------------------------------------------------------ l'inventaire

function dessinerTout() {
  dessinerEntites();
  dessinerContenants();
  dessinerEntete();
  if (Z.page === "inventaire") dessinerInventaire();
  else if (Z.page === "journal") dessinerJournal(true);
  else dessinerBonus();
}

function dessinerEntete() {
  const ent = Z.ent;
  const argent = ent && ent.argent ? Number(ent.argent) : NaN;
  $("#dappers").textContent = Number.isFinite(argent) ? argent.toLocaleString("fr-FR").replace(/ /g, " ") + " dappers" : "";
  $("#bourse").hidden = !Number.isFinite(argent);
  const guilde = ent && ent.sorte === "guild";
  $("#motd").hidden = !guilde;
  if (guilde) {
    $("#motd-texte").textContent = ent.motd || "Aucun message de guilde";
    $("#motd-texte").style.opacity = ent.motd ? 1 : .6;
  }
  const p = $("#portrait");
  p.hidden = !(ent && ent.portrait);
  if (ent && ent.portrait) p.src = ent.portrait;
}

function pageInventaire() {
  if ($("#grille-zone")) return;
  $("#page").innerHTML = '<div class="volume"><span>Volume :</span><div class="jauge"><div id="jauge"></div></div><span id="volume"></span></div>'
    + '<div class="outils"><input type="search" id="cherche" placeholder="Rechercher : nom, ou qualité (ex. œil 220)">'
    + '<span class="menu filtres"><button type="button" id="b-filtres">Filtres <svg class="chevron" viewBox="0 0 24 24"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2"/></svg></button>'
    + '<div class="pop" id="pop-filtres" hidden></div></span>'
    + '<span>Trier :</span><select id="tri">' + TRIS.map((t, i) => '<option value="' + i + '">' + t + "</option>").join("") + "</select>"
    + '<button type="button" id="b-sens" title="Ordre croissant/décroissant"></button>'
    + '<button type="button" id="b-reinit">Réinit.</button></div>'
    + '<div class="grille-zone" id="grille-zone"></div>';
  $("#cherche").value = Z.cherche;
  // Entrer dans une recherche ou en sortir change les contenants montres, donc
  // les familles du filtre (window._apply_filter rappelle _display_inventory).
  $("#cherche").addEventListener("input", () => { Z.cherche = $("#cherche").value; majCategories(); dessinerGrille(); });
  $("#tri").value = String(Z.tri[0]);
  $("#tri").addEventListener("change", () => { Z.tri[0] = Number($("#tri").value); garder("zr-tri", Z.tri); dessinerGrille(); });
  $("#b-sens").textContent = Z.tri[1] ? "↑" : "↓";
  $("#b-sens").addEventListener("click", () => {
    Z.tri[1] = !Z.tri[1];
    $("#b-sens").textContent = Z.tri[1] ? "↑" : "↓";
    garder("zr-tri", Z.tri);
    dessinerGrille();
  });
  $("#b-reinit").addEventListener("click", () => {
    // Comme window._on_reset_filter : la fenetre telle qu'au lancement.
    Z.cherche = "";
    $("#cherche").value = "";
    Z.f = filtresVierges();
    Z.tri = [1, false];
    garder("zr-tri", Z.tri);
    $("#tri").value = "1";
    $("#b-sens").textContent = "↓";
    dessinerFiltres();
    dessinerGrille();
  });
  $("#b-filtres").addEventListener("click", () => { const p = $("#pop-filtres"); fermerPops(p); p.hidden = !p.hidden; });
  $("#pop-filtres").addEventListener("change", surFiltre);
  $("#pop-filtres").addEventListener("input", surFiltre);
  const zone = $("#grille-zone");
  zone.addEventListener("mouseover", surSurvol);
  zone.addEventListener("mousemove", placerBulle);
  zone.addEventListener("mouseleave", () => { $("#bulle").hidden = true; });
}

function dessinerInventaire() {
  pageInventaire();
  dessinerContenants();
  const ent = Z.ent;
  const c = ent && ent.contenants[Z.contenant];
  // La jauge, comme window._update_volume_gauge.
  if (c && c.capacite > 0) {
    const pct = c.volume / c.capacite * 100;
    $("#jauge").parentElement.hidden = false;
    $("#jauge").style.width = Math.min(pct, 100) + "%";
    $("#jauge").classList.toggle("plein", pct >= 100);
    $("#volume").textContent = Math.round(c.volume) + " / " + c.capacite + "  (" + Math.round(pct) + "%)" + (pct >= 90 ? " ⚠" : "");
  } else {
    $("#jauge").parentElement.hidden = true;
    $("#volume").textContent = c ? Math.round(c.volume) + "  (capacité inconnue)" : "";
  }
  majCategories();
  dessinerGrille();
}

// Les familles presentes, comme window._maj_categories : tout se recoche
// quand la liste change.
function majCategories() {
  const ent = Z.ent;
  const trouvees = new Set();
  if (ent) {
    const liste = Z.cherche.trim() ? ent.contenants : [ent.contenants[Z.contenant]].filter(Boolean);
    for (const c of liste) for (const o of c.objets) trouvees.add(o.categorie);
  }
  const triees = [...trouvees].sort((a, b) => a < b ? -1 : a > b ? 1 : 0);
  if (JSON.stringify(triees) !== JSON.stringify(Z.categories)) {
    Z.categories = triees;
    Z.f.types = new Set(triees);
  }
  dessinerFiltres();
}

function goutte(couleur) {
  return '<svg class="goutte" viewBox="0 0 11 14"><path d="M5.5 1 C4.2 3.6 1.2 6.2 1.2 8.9 A4.3 4.3 0 0 0 9.8 8.9 C9.8 6.2 6.8 3.6 5.5 1 Z" fill="'
    + couleur + '" stroke="rgba(0,0,0,.75)" stroke-width="1"/></svg>';
}

function dessinerFiltres() {
  const f = Z.f;
  const m = Z.meta;
  if (!m || !$("#pop-filtres")) return;
  const groupe = (titre, noms, ensemble, cle, valeurs) => "<h4>" + titre + "</h4>" + noms.map((n, i) => {
    const v = valeurs ? valeurs[i] : i;
    return '<label><input type="checkbox" data-g="' + cle + '" data-v="' + esc(v) + '"' + (ensemble.has(v) ? " checked" : "") + "> " + esc(n) + "</label>";
  }).join("");
  $("#pop-filtres").innerHTML = "<h4>Bonus</h4>" + m.specialites.map(([l, c], i) => '<label><input type="checkbox" data-g="bonus" data-v="' + i + '"'
      + (f.bonus.has(i) ? " checked" : "") + "> " + goutte(c) + " " + esc(l) + "</label>").join("")
    + '<div class="q">Qualité <input type="number" data-f="qmin" min="0" max="500" step="10" value="' + f.qmin + '"> à '
    + '<input type="number" data-f="qmax" min="0" max="500" step="10" value="' + f.qmax + '"></div>'
    + '<label><input type="checkbox" data-f="cadenas"' + (f.cadenas ? " checked" : "") + "> Cadenas</label>"
    + '<label><input type="checkbox" data-f="avecBonus"' + (f.avecBonus ? " checked" : "") + "> Avec bonus</label>"
    + '<label><input type="checkbox" data-f="vente"' + (f.vente ? " checked" : "") + "> En vente</label>"
    + groupe("Type d'objet", Z.categories, f.types, "types", Z.categories)
    + groupe("Classe", m.classes, f.classes, "classes")
    + groupe("Écosystème", m.ecosystemes, f.ecos, "ecos")
    + groupe("Équipement", m.equipements, f.equips, "equips");
}

function surFiltre(ev) {
  const t = ev.target;
  if (t.dataset.g) {
    const ens = Z.f[t.dataset.g];
    const v = t.dataset.g === "types" ? t.dataset.v : Number(t.dataset.v);
    if (t.checked) ens.add(v); else ens.delete(v);
  } else if (t.dataset.f) {
    Z.f[t.dataset.f] = t.type === "checkbox" ? t.checked : Number(t.value) || 0;
  } else return;
  dessinerGrille();
}

// Comme window._apply_filter.
function retenu(o, mot, qualites) {
  const f = Z.f;
  if (mot && !o.cle.includes(mot)) return false;
  if (qualites.size && !qualites.has(o.q)) return false;
  if (!(f.qmin <= o.q && o.q <= f.qmax)) return false;
  if (!f.types.has(o.categorie)) return false;
  if (!f.ecos.has(o.eco)) return false;
  if (!f.classes.has(o.classe)) return false;
  if (o.equip >= 0 && !f.equips.has(o.equip)) return false;
  if (f.cadenas && !o.cadenas) return false;
  if (f.avecBonus && !o.bonus.length) return false;
  // specialites.passe_le_filtre : toutes cochees, rien n'est trie.
  if (f.bonus.size < 4) {
    const noms = Z.meta.specialites.map(([l]) => l);
    if (!o.bonus.some(([l]) => f.bonus.has(noms.indexOf(l)))) return false;
  }
  if (f.vente && !o.vente) return false;
  return true;
}

// Comme models.decouper_recherche : un nombre isole est une qualite.
function decouper(texte) {
  const qualites = new Set();
  const reste = texte.replace(/(^|\s)(\d+)(?=\s|$)/g, (m, avant, n) => { qualites.add(Number(n)); return avant + " "; });
  return [reste.split(/\s+/).filter(Boolean).join(" "), qualites];
}

function ordre(c) {
  const [rang, desc] = Z.tri;
  if (!rang) return c.objets.map((_o, i) => i);
  return c.ordres[rang + (desc ? "desc" : "asc")] || c.objets.map((_o, i) => i);
}

function caseHtml(o, ci, oi) {
  const echelle = 1;
  let gouttes = "";
  if (o.bonus.length) {
    // specialites._pas : bord a bord tant qu'elles tiennent au-dessus de la quantite.
    const n = o.bonus.length;
    const pas = n < 2 ? 14 : Math.min(14, (38 - 14) / (n - 1));
    gouttes = '<svg class="gouttes" width="' + 11 * echelle + '" height="' + ((n - 1) * pas + 14) * echelle
      + '" viewBox="0 0 11 ' + ((n - 1) * pas + 14) + '">'
      + o.bonus.map((_b, i) => i).reverse().map((i) => '<g transform="translate(0 ' + i * pas + ')"><path d="M5.5 1 C4.2 3.6 1.2 6.2 1.2 8.9 A4.3 4.3 0 0 0 9.8 8.9 C9.8 6.2 6.8 3.6 5.5 1 Z" fill="'
        + o.bonus[i][2] + '" stroke="rgba(0,0,0,.75)" stroke-width="1"/></g>').join("") + "</svg>";
  }
  return '<div class="case" data-c="' + ci + '" data-o="' + oi + '"><img class="objet" loading="lazy" src="' + esc(o.icone) + '" alt="">'
    + gouttes + (o.sort ? '<img class="sort" src="' + esc(o.sort) + '" alt="">' : "") + "</div>";
}

function dessinerGrille() {
  const zone = $("#grille-zone");
  if (!zone) return;
  const ent = Z.ent;
  if (!ent) {
    zone.innerHTML = '<div class="vide">' + (Z.pret ? "Synchronisation…" : "Chargement de ZyRoom… (la première fois, le navigateur télécharge Python, une dizaine de Mo)") + "</div>";
    majEtat();
    return;
  }
  const [mot, qualites] = decouper(norm(Z.cherche));
  const cherche = Z.cherche.trim() !== "";
  let h = "";
  // Une recherche cherche dans tous les contenants a la fois (window._display_inventory).
  const contenants = cherche ? ent.contenants.map((c, i) => [c, i]) : [[ent.contenants[Z.contenant], Z.contenant]];
  for (const [c, ci] of contenants) {
    if (!c) continue;
    const cases = ordre(c).filter((oi) => retenu(c.objets[oi], mot, qualites)).map((oi) => caseHtml(c.objets[oi], ci, oi));
    if (cherche) {
      if (!cases.length) continue;
      h += '<div class="section">' + esc(c.nom) + " — " + cases.length + " résultat(s)</div>";
    }
    h += '<div class="grille">' + cases.join("") + "</div>";
  }
  zone.innerHTML = h || '<div class="vide">' + (cherche ? "Aucun résultat." : "") + "</div>";
  majEtat();
}

// ------------------------------------------------------------ l'infobulle

function surSurvol(ev) {
  const caseEl = ev.target.closest(".case");
  const b = $("#bulle");
  if (!caseEl || !Z.ent) { b.hidden = true; return; }
  const o = Z.ent.contenants[Number(caseEl.dataset.c)].objets[Number(caseEl.dataset.o)];
  b.innerHTML = esc(o.bulle.join("\n"))
    + o.bonus.map(([l, v, c]) => '<div class="bonus">' + goutte(c) + esc(l + " +" + v) + "</div>").join("")
    + (o.enchant ? '<div style="margin-top:4px">' + esc(o.enchant) + "</div>" : "");
  b.hidden = false;
  placerBulle(ev);
}
function placerBulle(ev) {
  const b = $("#bulle");
  if (b.hidden) return;
  const x = Math.min(ev.clientX + 14, window.innerWidth - b.offsetWidth - 8);
  const y = ev.clientY + 18 + b.offsetHeight > window.innerHeight ? ev.clientY - b.offsetHeight - 10 : ev.clientY + 18;
  b.style.left = x + "px";
  b.style.top = y + "px";
}

// ------------------------------------------------------------ la ligne d'etat

function etat(texte) { $("#etat").textContent = texte; }

// Comme config.format_last_sync.
function formatSynchro(quand) {
  if (!quand) return "jamais synchronisé";
  const d = new Date(quand);
  const auj = new Date();
  const jour = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const ecart = Math.round((jour(auj) - jour(d)) / 86400000);
  const heure = deux(d.getHours()) + "h" + deux(d.getMinutes());
  if (ecart === 0) return "aujourd'hui à " + heure;
  if (ecart === 1) return "hier à " + heure;
  return "le " + deux(d.getDate()) + "/" + deux(d.getMonth() + 1) + " à " + heure;
}

// Comme window._presence.
function presence(ent) {
  if (!ent.connexion && !ent.deconnexion) return "";
  if (ent.connexion > ent.deconnexion) return "🟢 en ligne";
  const minutes = Math.floor((Date.now() / 1000 - ent.deconnexion) / 60);
  if (minutes < 1) return "vu à l'instant";
  if (minutes < 60) return "vu il y a " + minutes + " min";
  if (minutes < 1440) return "vu il y a " + Math.floor(minutes / 60) + " h";
  if (minutes < 10080) return "vu il y a " + Math.floor(minutes / 1440) + " j";
  const d = new Date(ent.deconnexion * 1000);
  return "vu le " + deux(d.getDate()) + "/" + deux(d.getMonth() + 1);
}

function majEtat() {
  const ent = Z.ent;
  if (!ent) return;
  const c = ent.contenants[Z.contenant];
  const vu = presence(ent);
  etat(ent.nom + (ent.guilde ? " - " + ent.guilde : "") + (vu ? " · " + vu : "")
       + "\n" + (c ? c.nom : "") + " · synchro " + formatSynchro(ent.quand));
}

// ------------------------------------------------------------ saison et redemarrage

// Comme meteo.duree(minutes, unite=True).
function duree(minutes) {
  if (minutes <= 0) return "moins d'une minute";
  if (minutes < 60) return minutes + " min";
  let h = Math.floor(minutes / 60);
  const reste = deux(minutes % 60);
  if (h < 24) return h + " h " + reste + " min";
  const j = Math.floor(h / 24);
  h %= 24;
  return j + " j " + h + " h " + reste + " min";
}
// Comme meteo.moment_du_changement.
function momentChangement(minutes) {
  const quand = new Date(Date.now() + Math.max(0, minutes) * 60000);
  const heure = deux(quand.getHours()) + ":" + deux(quand.getMinutes());
  const jours = Math.round((new Date(quand.getFullYear(), quand.getMonth(), quand.getDate())
    - new Date(new Date().getFullYear(), new Date().getMonth(), new Date().getDate())) / 86400000);
  if (jours <= 0) return "aujourd'hui à " + heure;
  if (jours === 1) return "demain à " + heure;
  return "le " + deux(quand.getDate()) + "/" + deux(quand.getMonth() + 1) + " à " + heure;
}
// Comme meteo.moment_du_redemarrage.
function momentRedemarrage(minutes) {
  const quand = new Date(Date.now() - Math.max(0, minutes) * 60000);
  quand.setMinutes(0, 0, 0);
  const heure = "vers " + quand.getHours() + " h";
  const auj = new Date();
  const jours = Math.round((new Date(auj.getFullYear(), auj.getMonth(), auj.getDate())
    - new Date(quand.getFullYear(), quand.getMonth(), quand.getDate())) / 86400000);
  if (jours <= 0) return "aujourd'hui " + heure;
  if (jours === 1) return "hier " + heure;
  return "le " + deux(quand.getDate()) + "/" + deux(quand.getMonth() + 1) + " " + heure;
}

async function majSaison() {
  try {
    const xml = await (await fetch(API + "/time.php?format=xml", { cache: "no-store" })).text();
    const t = JSON.parse(await appeler("saison", xml));
    const minutes = Math.round(t.minutes_to_next);
    $("#saison").textContent = t.next_season_name + " dans " + duree(minutes) + " — " + momentChangement(minutes);
  } catch (souci) { /* la saison reviendra au prochain tour */ }
  try {
    const r = await fetch("zyroom.php?quoi=statut", { cache: "no-store", headers: { "X-MP": Z.jeton } });
    if (r.ok) {
      const s = await r.json();
      // ryzom_api.minutes_depuis_redemarrage : « 12d 19h ».
      const m = /^(?:(\d+)\s*d)?\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?$/.exec(String(s[2] || "").trim());
      if (m && (m[1] || m[2] || m[3])) {
        const minutes = ((Number(m[1] || 0) * 24) + Number(m[2] || 0)) * 60 + Number(m[3] || 0);
        $("#reboot").textContent = "Reboot " + momentRedemarrage(minutes);
      }
    }
  } catch (souci) { /* idem */ }
}

// ------------------------------------------------------------ le journal
//
// Un personnage : le navigateur tient son journal, en comparant chaque releve
// au precedent (window._relever_en_silence). Le hall : celui que le releve
// publie tous les quarts d'heure sur GitHub, qui voit plus que la page.

const DEPOT = "https://raw.githubusercontent.com/xiom-dev/zyroom-gtk-android/journaux/";
// Comme movements._MAX_LINES et _TRIM_TO, a l'echelle du stockage d'un navigateur.
const MAX_LIGNES = 6000, GARDEES = 4000;
const J = { cle: "", cherche: "", mode: 0, compte: 0 };

function cleJournal(e) { return e.sorte + "-" + e.id; }

async function journaliser(e, xml) {
  if (e.sorte !== "character") return;
  const cle = cleJournal(e);
  let avant = "";
  try { avant = localStorage.getItem("zr-instantane-" + cle) || ""; } catch (er) {}
  const r = JSON.parse(await appeler("releve", xml, e.sorte, avant));
  let lignes = [];
  try { lignes = (localStorage.getItem("zr-journal-" + cle) || "").split("\n").filter(Boolean); } catch (er) {}
  if (r.lignes.length) {
    lignes = lignes.concat(r.lignes);
    if (lignes.length > MAX_LIGNES) lignes = lignes.slice(-GARDEES);
    try { localStorage.setItem("zr-journal-" + cle, lignes.join("\n")); } catch (er) {}
  }
  try { localStorage.setItem("zr-instantane-" + cle, JSON.stringify(r.instantane)); } catch (er) {}
  if (Z.page === "journal" && J.cle === cle) chargerJournal();
}

async function chargerJournal() {
  const e = entiteCourante();
  const cle = cleJournal(e);
  J.cle = cle;
  let texte = "";
  if (e.sorte === "guild") {
    attendre(true);
    try {
      const r = await fetch(DEPOT + "guild-" + e.id + ".jsonl", { cache: "no-cache" });
      if (r.ok) texte = await r.text();
    } catch (er) { /* pas de reseau : journal vide */ }
    attendre(false);
  } else {
    try { texte = localStorage.getItem("zr-journal-" + cle) || ""; } catch (er) {}
  }
  if (J.cle !== cle) return;
  J.compte = await appeler("charger_journal", cle, texte, lire("zr-journal-vide-" + cle, 0));
  montrerJournal();
}

function pageJournal() {
  if ($("#journal-zone")) return;
  $("#page").innerHTML = '<div class="outils"><input type="search" id="j-cherche" placeholder="Rechercher dans le journal…">'
    + '<select id="j-mode"><option value="0">Tout</option><option value="1">Entrées</option><option value="2">Sorties</option></select>'
    + '<button type="button" id="j-copier" title="Copier les lignes affichées">Copier</button>'
    + '<button type="button" id="j-vider" title="Effacer le journal de cette entité">Vider</button></div>'
    + '<div class="grille-zone" id="journal-zone"></div><div class="j-etat" id="j-etat"></div>';
  $("#j-cherche").value = J.cherche;
  $("#j-mode").value = String(J.mode);
  $("#j-cherche").addEventListener("input", () => { J.cherche = $("#j-cherche").value; montrerJournal(); });
  $("#j-mode").addEventListener("change", () => { J.mode = Number($("#j-mode").value); montrerJournal(); });
  $("#j-copier").addEventListener("click", async () => {
    const texte = await appeler("copier_journal", J.cle, J.cherche, J.mode);
    if (!texte) return;
    try {
      await navigator.clipboard.writeText(texte);
      $("#j-etat").textContent = texte.split("\n").length + " lignes copiées.";
    } catch (er) { $("#j-etat").textContent = "Copie refusée par le navigateur."; }
  });
  $("#j-vider").addEventListener("click", () => {
    const e = entiteCourante();
    if (!confirm("Vider le journal ?\n\nLes " + J.compte + " mouvements enregistrés pour " + e.nom
      + " seront perdus. L'API ne permet pas de les reconstruire.")) return;
    // Le hall vient du releve publie : on retient jusqu'ou il a ete vide.
    garder("zr-journal-vide-" + J.cle, Date.now() / 1000);
    try { localStorage.removeItem("zr-journal-" + J.cle); } catch (er) {}
    chargerJournal();
  });
}

function dessinerJournal(recharger) {
  pageJournal();
  if (recharger || J.cle !== cleJournal(entiteCourante())) {
    $("#journal-zone").innerHTML = '<div class="vide">Lecture du journal…</div>';
    $("#j-etat").textContent = "";
    if (Z.pret) chargerJournal();
  }
  majEtat();
}

async function montrerJournal() {
  const cle = J.cle;
  const v = JSON.parse(await appeler("vue_journal", cle, J.cherche, J.mode));
  if (cle !== J.cle || !$("#journal-zone")) return;
  // Un tableau sans en-tetes, comme le Gtk.ColumnView du journal.
  $("#journal-zone").innerHTML = '<table class="journal"><tbody>' + v.lignes.map((l) =>
    '<tr' + (l.jour ? ' class="jour"' : "") + ' title="' + esc(l.texte) + '">'
    + '<td class="date">' + esc(l.quand) + '</td><td class="faible">' + esc(l.contenant) + "</td>"
    + '<td class="qte ' + (l.delta > 0 ? "plus" : "moins") + '">' + esc(l.quantite) + "</td>"
    + "<td>" + esc(l.nom) + '</td><td class="ico-j"><img loading="lazy" src="' + esc(l.argent ? "symboles/dappers.png" : l.icone) + '" alt=""></td>'
    + '<td class="faible">' + (l.q ? "Q" + l.q : "") + "</td></tr>").join("") + "</tbody></table>";
  $("#journal-zone").scrollTop = 0;
  $("#j-etat").textContent = v.etat;
}

// ------------------------------------------------------------ Bonus

function dessinerBonus() {
  if (Z.page === "competences") dessinerCompetences();
  else if (Z.page === "effectif") dessinerEffectif();
  else if (Z.page === "perdu") dessinerPerdu();
  else if (Z.page === "avant-postes") dessinerAvantPostes();
  else if (Z.page === "meteo") dessinerMeteo();
  else dessinerAutrePage();
  majEtat();
}

// L'entite d'une sorte : celle qu'on regarde, sinon la derniere vue, sinon
// celle que le navigateur garde en cache (window._entite_en_cache).
async function entiteDe(sorte) {
  if (Z.ent && Z.ent.sorte === sorte) return { ent: Z.ent, ailleurs: false };
  if (Z.derniers[sorte]) return { ent: Z.derniers[sorte], ailleurs: true };
  for (const e of entites().filter((x) => x.sorte === sorte)) {
    const garde = await fluxGarde(cacheXml(e));
    if (!garde || !garde.xml) continue;
    try {
      const ent = await lireFlux(e, garde);
      Z.derniers[sorte] = ent;
      return { ent, ailleurs: true };
    } catch (er) { /* suivante */ }
  }
  // Le hall, lui, se demande toujours au serveur : pas besoin de l'avoir
  // ouvert avant, contrairement a l'application.
  if (sorte === "guild") {
    try {
      const e = entites().find((x) => x.sorte === "guild");
      const flux = await telecharger(e);
      const ent = await lireFlux(e, flux);
      garderFlux(cacheXml(e), flux);
      Z.derniers.guild = ent;
      return { ent, ailleurs: true };
    } catch (er) { /* hors ligne */ }
  }
  return null;
}

const zebre = (i) => (i % 2 === 0 ? " zebre" : "");

// --- Competences (page_skills.py)

const C = { cherche: "", mode: 0, ouvertes: new Set() };

async function dessinerCompetences() {
  if (!$("#c-liste")) {
    $("#page").innerHTML = '<div class="outils"><input type="search" id="c-cherche" placeholder="Rechercher une compétence…">'
      + '<select id="c-mode" title="« En cours » ne garde que les niveaux entamés"><option value="0">Tout</option><option value="1">En cours</option></select>'
      + '<button type="button" id="c-tout">Tout déplier</button></div>'
      + '<div class="grille-zone liste" id="c-liste"></div><div class="j-etat" id="c-etat"></div>';
    $("#c-cherche").value = C.cherche;
    $("#c-mode").value = String(C.mode);
    $("#c-cherche").addEventListener("input", () => { C.cherche = $("#c-cherche").value; dessinerCompetences(); });
    $("#c-mode").addEventListener("change", () => { C.mode = Number($("#c-mode").value); dessinerCompetences(); });
    $("#c-liste").addEventListener("click", (ev) => {
      const l = ev.target.closest("[data-code]");
      if (!l) return;
      if (C.ouvertes.has(l.dataset.code)) C.ouvertes.delete(l.dataset.code); else C.ouvertes.add(l.dataset.code);
      dessinerCompetences();
    });
    $("#c-tout").addEventListener("click", async () => {
      const t = await entiteDe("character");
      if (C.ouvertes.size) C.ouvertes.clear();
      else if (t) t.ent.competences.filter((n) => n.enfants).forEach((n) => C.ouvertes.add(n.code));
      dessinerCompetences();
    });
  }
  const trouve = Z.pret ? await entiteDe("character") : null;
  const arbre = trouve ? trouve.ent.competences : [];
  if (!arbre.length) {
    $("#c-liste").innerHTML = "";
    $("#c-tout").disabled = true;
    $("#c-etat").textContent = "Aucun personnage consulté pour l'instant : ouvrez-en un une fois, et son arbre "
      + "restera consultable d'ici. L'API ne donne les compétences que pour un personnage, et seulement si la clé accorde ce module.";
    return;
  }
  $("#c-tout").disabled = false;
  const mot = norm(C.cherche.trim());
  const filtre = mot !== "" || C.mode === 1;
  let lignes;
  if (filtre) {
    lignes = arbre.filter((n) => (C.mode !== 1 || n.avance) && (!mot || norm(n.nom).includes(mot)));
  } else {
    // skills.visible : un parent ouvert et lui-meme visible.
    const vus = new Set();
    lignes = arbre.filter((n) => {
      if (n.parent === null || (vus.has(n.parent) && C.ouvertes.has(n.parent))) { vus.add(n.code); return true; }
      return false;
    });
  }
  $("#c-tout").textContent = C.ouvertes.size ? "Tout replier" : "Tout déplier";
  $("#c-tout").hidden = filtre;
  const points = trouve.ent.points || {};
  $("#c-liste").innerHTML = lignes.map((n, i) => {
    const racine = n.profondeur === 0 && !filtre;
    const ouvrable = n.enfants && !filtre;
    const pts = racine ? points[n.code] : null;
    return '<div class="ligne-c' + zebre(i) + (ouvrable ? '" data-code="' + esc(n.code) : "") + '">'
      + '<div class="c-ligne" style="padding-left:' + (8 + (filtre ? 0 : n.profondeur * 14)) + 'px">'
      + '<span class="fleche">' + (ouvrable ? (C.ouvertes.has(n.code) ? "▾" : "▸") : "") + "</span>"
      + '<span class="c-nom' + (racine ? " titre-c" : "") + (n.fini ? " fini" : "") + '">' + esc(n.nom) + "</span>"
      + (n.avance ? '<span class="c-barre"><span style="width:' + n.avance + '%"></span></span>' : "")
      + '<span class="c-niveau' + (n.fini ? " fini" : "") + '">' + n.niveau + (n.avance ? " · " + n.avance + " %" : "") + "</span></div>"
      + (pts ? '<div class="c-points">' + pts[0].toLocaleString("fr-FR").replace(/\u202f/g, " ") + " pts · "
        + pts[1].toLocaleString("fr-FR").replace(/\u202f/g, " ") + " dépensés</div>" : "")
      + "</div>";
  }).join("");
  const nb = arbre.length;
  $("#c-etat").textContent = (trouve.ailleurs ? trouve.ent.nom + " · " : "") + nb + " compétences, " + lignes.length + " affichées";
}

// --- Effectif (page_roster.py)

const R = { vue: "effectif", cherche: "", registre: null };
// page_roster.SIGNES : la couleur porte le sens, le triangle le confirme.
const SIGNES = { arrivee: ["▲", "tri-arrivee", "arrivée"], depart: ["▼", "tri-depart", "départ"],
                 "grade-haut": ["▲", "tri-grade", "montée de grade"], "grade-bas": ["▼", "tri-retro", "rétrogradation"] };

async function chargerRegistre(gid) {
  if (R.registre && R.registre.gid === gid) return R.registre;
  let texte = "";
  try {
    const r = await fetch(DEPOT + "roster-" + gid + ".jsonl", { cache: "no-cache" });
    if (r.ok) texte = await r.text();
  } catch (er) { /* pas de reseau */ }
  R.registre = Object.assign(JSON.parse(await appeler("registre", gid, texte)), { gid });
  return R.registre;
}

async function dessinerEffectif() {
  if (!$("#r-liste")) {
    $("#page").innerHTML = '<div class="outils"><span class="lies"><button type="button" data-vue="effectif">Effectif</button>'
      + '<button type="button" data-vue="mouvements">Arrivées et départs</button></span>'
      + '<input type="search" id="r-cherche" placeholder="Rechercher un membre…"><span class="r-etat" id="r-etat"></span></div>'
      + '<div class="grille-zone liste" id="r-liste"></div>';
    $("#r-cherche").value = R.cherche;
    $("#r-cherche").addEventListener("input", () => { R.cherche = $("#r-cherche").value; dessinerEffectif(); });
    document.querySelectorAll("[data-vue]").forEach((b) => b.addEventListener("click", () => { R.vue = b.dataset.vue; dessinerEffectif(); }));
  }
  document.querySelectorAll("[data-vue]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.vue === R.vue)));
  $("#r-cherche").hidden = R.vue !== "effectif";
  const trouve = Z.pret ? await entiteDe("guild") : null;
  if (!trouve) {
    $("#r-liste").innerHTML = "";
    $("#r-etat").textContent = "Aucune guilde consultée pour l'instant : ouvrez-en une une fois, et son effectif restera consultable d'ici.";
    return;
  }
  const ent = trouve.ent;
  const reg = await chargerRegistre(ent.id);
  // Zero ne s'ecrit pas (_compter_roster).
  document.querySelector('[data-vue="effectif"]').textContent = ent.nb_membres ? "Effectif · " + ent.nb_membres : "Effectif";
  document.querySelector('[data-vue="mouvements"]').textContent = reg.lignes.length ? "Arrivées et départs · " + reg.lignes.length : "Arrivées et départs";
  const morceaux = [];
  if (trouve.ailleurs) morceaux.push(ent.nom);
  if (R.vue === "mouvements") morceaux.push("journal des " + reg.jours + " derniers jours");
  $("#r-etat").textContent = morceaux.join(" · ");
  if (R.vue === "mouvements") {
    const legende = '<div class="legende">' + ["arrivee", "depart", "grade-haut", "grade-bas"].map((k) =>
      '<span><span class="' + SIGNES[k][1] + '">' + SIGNES[k][0] + "</span> " + SIGNES[k][2] + "</span>").join("")
      + '<span class="note">départs et grades : date du relevé</span></div>';
    $("#r-liste").innerHTML = legende + (reg.lignes.length ? reg.lignes.map((c, i) => {
      const d = new Date(c.at * 1000);
      return '<div class="r-ligne' + zebre(i) + '"><span class="r-date">' + deux(d.getDate()) + "/" + deux(d.getMonth() + 1)
        + " " + deux(d.getHours()) + ":" + deux(d.getMinutes()) + '</span><span class="' + SIGNES[c.sens][1] + '">'
        + SIGNES[c.sens][0] + "</span><span>" + esc(c.texte) + "</span></div>";
    }).join("") : '<div class="vide">Aucun mouvement depuis le premier relevé. Le registre compare l\'effectif d\'une '
      + "synchronisation à l'autre : l'API ne garde aucune histoire, seule l'application en tient une.</div>");
    return;
  }
  const mot = norm(R.cherche.trim());
  const groupes = ent.effectif.map(([g, n]) => [g, n.filter((x) => !mot || norm(x).includes(mot))]).filter(([, n]) => n.length);
  $("#r-liste").innerHTML = groupes.length ? groupes.map(([grade, noms], i) =>
    '<div class="r-groupe' + zebre(i) + '"><div class="r-titre">' + esc(grade) + " · " + noms.length + '</div><div class="r-noms">'
    + noms.map((x) => "<span>" + esc(x) + "</span>").join("") + "</div></div>").join("")
    : '<div class="vide">Aucun membre de ce nom.</div>';
}

// --- La carte d'Atys (page_betes._peindre_carte, page_cartes)
//
// Une image de 4000 x 3000, agrandie a la molette, au pincement ou aux
// boutons, deplacee au glisse. `points(ctx, e, mx, my)` dessine par-dessus.

const ZOOM_MAX = 16, PAS_ZOOM = 1.15, SEUIL_GROUPE = 40;
const CERNE = "rgb(15,20,23)";
let imageAtys = null;
function chargerAtys() {
  if (!imageAtys) {
    imageAtys = new Image();
    imageAtys.src = "cartes/atys.webp";
  }
  return imageAtys;
}

function carteAtys(canvas, points) {
  const etat = { zoom: 1, gx: 0, gy: 0 };
  const img = chargerAtys();
  function borner() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    const e = Math.min(w / 4000, h / 3000) * etat.zoom;
    const dx = Math.max(0, (4000 * e - w) / 2), dy = Math.max(0, (3000 * e - h) / 2);
    etat.gx = Math.max(-dx, Math.min(dx, etat.gx));
    etat.gy = Math.max(-dy, Math.min(dy, etat.gy));
  }
  function dessiner() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h) return;
    const r = window.devicePixelRatio || 1;
    canvas.width = Math.round(w * r);
    canvas.height = Math.round(h * r);
    const ctx = canvas.getContext("2d");
    ctx.setTransform(r, 0, 0, r, 0, 0);
    ctx.clearRect(0, 0, w, h);
    if (!img.complete || !img.naturalWidth) { img.onload = dessiner; return; }
    const e = Math.min(w / 4000, h / 3000) * etat.zoom;
    const mx = (w - 4000 * e) / 2 + etat.gx, my = (h - 3000 * e) / 2 + etat.gy;
    ctx.save();
    ctx.beginPath(); ctx.rect(0, 0, w, h); ctx.clip();
    ctx.drawImage(img, mx, my, 4000 * e, 3000 * e);
    points(ctx, e, mx, my, w, h);
    ctx.restore();
  }
  function zoomer(f, cx, cy) {
    const avant = etat.zoom;
    etat.zoom = Math.max(1, Math.min(ZOOM_MAX, etat.zoom * f));
    const rapport = etat.zoom / avant;
    etat.gx *= rapport; etat.gy *= rapport;
    borner(); dessiner();
  }
  canvas.addEventListener("wheel", (ev) => { ev.preventDefault(); zoomer(ev.deltaY > 0 ? 1 / PAS_ZOOM : PAS_ZOOM); }, { passive: false });
  // Glisse a la souris comme au doigt ; a deux doigts, le pincement.
  const doigts = new Map();
  let depart = null, pince = null;
  canvas.addEventListener("pointerdown", (ev) => {
    canvas.setPointerCapture(ev.pointerId);
    doigts.set(ev.pointerId, [ev.clientX, ev.clientY]);
    depart = [ev.clientX, ev.clientY, etat.gx, etat.gy];
    if (doigts.size === 2) { const [a, b] = [...doigts.values()]; pince = [Math.hypot(a[0] - b[0], a[1] - b[1]), etat.zoom]; }
  });
  canvas.addEventListener("pointermove", (ev) => {
    if (!doigts.has(ev.pointerId)) return;
    doigts.set(ev.pointerId, [ev.clientX, ev.clientY]);
    if (doigts.size === 2 && pince) {
      const [a, b] = [...doigts.values()];
      const d = Math.hypot(a[0] - b[0], a[1] - b[1]);
      zoomer((pince[1] * d / pince[0]) / etat.zoom);
    } else if (depart && etat.zoom > 1) {
      etat.gx = depart[2] + ev.clientX - depart[0];
      etat.gy = depart[3] + ev.clientY - depart[1];
      borner(); dessiner();
    }
  });
  const fin = (ev) => { doigts.delete(ev.pointerId); if (doigts.size < 2) pince = null; if (!doigts.size) depart = null; };
  canvas.addEventListener("pointerup", fin);
  canvas.addEventListener("pointercancel", fin);
  new ResizeObserver(() => { borner(); dessiner(); }).observe(canvas);
  return { dessiner, etat };
}

// Un nom blanc cerne de noir sur ses huit cotes (page_betes._marqueur).
function nomCerne(ctx, texte, x, y) {
  ctx.font = "13px Cantarell, 'Noto Sans', sans-serif";
  ctx.fillStyle = CERNE;
  for (const dx of [-1, 0, 1]) for (const dy of [-1, 0, 1]) if (dx || dy) ctx.fillText(texte, x + dx * 1.2, y + dy * 1.2);
  ctx.fillStyle = "#fff";
  ctx.fillText(texte, x, y);
}
function cible(ctx, x, y, coeur) {
  for (const [r, c] of [[7, CERNE], [5.5, "#fff"], [3, coeur]]) {
    ctx.fillStyle = c; ctx.beginPath(); ctx.arc(x, y, r, 0, 6.2832); ctx.fill();
  }
}

// --- Perdu ? (page_betes.py)

let cartePerdu = null;
async function dessinerPerdu() {
  if (!$("#p-carte")) {
    $("#page").innerHTML = '<div class="grille-zone liste perdu"><canvas id="p-carte"></canvas>'
      + '<div class="p-entete" id="p-entete"></div><div class="p-colonnes"><div id="p-mek"></div><div id="p-zig"></div></div></div>';
    cartePerdu = carteAtys($("#p-carte"), (ctx, e, mx, my, w, h) => {
      const ent = cartePerdu.ent;
      if (!ent) return;
      if (ent.pixel) {
        const x = mx + ent.pixel[0] * e, y = my + ent.pixel[1] * e;
        cible(ctx, x, y, "rgb(59,156,255)");
        nomCerne(ctx, ent.nom, x + 11, y - 7);
      }
      // Les betes trop proches n'en font qu'une.
      const groupes = new Map();
      for (const b of ent.betes.filter((x) => x.dehors && x.pixel)) {
        const x = mx + b.pixel[0] * e, y = my + b.pixel[1] * e;
        const cle = Math.floor(x / SEUIL_GROUPE) + ":" + Math.floor(y / SEUIL_GROUPE);
        if (!groupes.has(cle)) groupes.set(cle, [x, y, []]);
        groupes.get(cle)[2].push(b);
      }
      for (const [x, y, liste] of groupes.values()) {
        cible(ctx, x, y, "rgb(255,46,46)");
        nomCerne(ctx, (liste[0].nom || liste[0].etiquette) + (liste.length > 1 ? " +" + (liste.length - 1) : ""), x + 11, y - 7);
      }
    });
  }
  const trouve = Z.ent && Z.ent.sorte === "character" ? { ent: Z.ent } : (Z.pret ? await entiteDe("character") : null);
  const ent = trouve ? trouve.ent : null;
  cartePerdu.ent = ent;
  const betes = ent ? ent.betes : [];
  const dehors = betes.filter((b) => b.dehors).length;
  $("#p-carte").hidden = !ent || (!dehors && !ent.pixel);
  $("#p-entete").textContent = !dehors ? "Aucune bête dehors : toutes sont rangées."
    : dehors === 1 ? "1 bête dehors" : dehors + " bêtes dehors";
  const lieux = { landscape: "dehors", stable: "à l'écurie", "": "état inconnu" };
  const colonne = (titre, liste) => '<div class="p-titre">' + titre + " · " + liste.length + "</div>"
    + (liste.length ? liste.map((b, i) => {
      const lieu = lieux[b.statut] !== undefined ? lieux[b.statut] : b.statut;
      let detail = b.nom ? b.etiquette + " · " + lieu : lieu;
      if (b.satiete > 0) detail += " · satiété " + Math.trunc(b.satiete);
      return '<div class="p-bete' + zebre(i) + '"><b>' + esc(b.nom || b.etiquette) + '</b><div class="faible">' + esc(detail) + "</div></div>";
    }).join("") : '<div class="faible p-vide">aucune</div>');
  $("#p-mek").innerHTML = colonne("Mektoubs", betes.filter((b) => !b.zig));
  $("#p-zig").innerHTML = colonne("Zigs", betes.filter((b) => b.zig));
  cartePerdu.dessiner();
}

// --- Avant-postes (page_outposts.py)
//
// L'annuaire public (guilds.php, sans cle) n'est demande qu'a l'ouverture de
// l'ecran et sur « Actualiser » : il pese un demi-mega-octet.

const OP = { vue: 0, charge: false };

// Les deux fleches qui tournent (page_outposts._dessiner_pastille), en SVG.
function pastille(texte) {
  const cote = 20, cx = 10, cy = 10, r = cote * 0.31, t = cote * 0.15, barbe = t * 1.2;
  const rad = (d) => d * Math.PI / 180;
  let d = "", pointes = "";
  for (const [a0, a1] of [[25, 155], [205, 335]]) {
    d += "M" + (cx + r * Math.cos(rad(a0))) + " " + (cy + r * Math.sin(rad(a0)))
      + " A" + r + " " + r + " 0 0 1 " + (cx + r * Math.cos(rad(a1))) + " " + (cy + r * Math.sin(rad(a1))) + " ";
    const a = rad(a1), b = rad(a1 + 28);
    pointes += '<path d="M' + (cx + (r + barbe) * Math.cos(a)) + " " + (cy + (r + barbe) * Math.sin(a))
      + " L" + (cx + (r - barbe) * Math.cos(a)) + " " + (cy + (r - barbe) * Math.sin(a))
      + " L" + (cx + r * Math.cos(b)) + " " + (cy + r * Math.sin(b)) + ' Z" fill="#7fb3a2"/>';
  }
  return '<svg class="pastille" viewBox="0 0 20 20"><title>' + esc(texte) + '</title><path d="' + d
    + '" fill="none" stroke="#7fb3a2" stroke-width="' + t + '" stroke-linecap="round"/>' + pointes + "</svg>";
}
function quandCourt(at) {
  const d = new Date(at * 1000);
  return deux(d.getDate()) + "/" + deux(d.getMonth() + 1) + " " + deux(d.getHours()) + ":" + deux(d.getMinutes());
}

async function chargerAnnuaire() {
  $("#op-etat").textContent = "Lecture de l'annuaire des guildes…";
  $("#op-actualiser").disabled = true;
  try {
    const r = await fetch(API + "/guilds.php", { cache: "no-store" });
    if (!r.ok) throw new Error("API Ryzom " + r.status);
    const res = JSON.parse(await appeler("charger_annuaire", await r.text(), JSON.stringify(lire("zr-op", {}))));
    garder("zr-op", res.fichiers);
    OP.charge = true;
  } catch (er) {
    $("#op-etat").textContent = "Annuaire indisponible : " + er.message;
  }
  $("#op-actualiser").disabled = false;
}

async function dessinerAvantPostes(forcer) {
  if (!$("#op-zone")) {
    $("#page").innerHTML = '<div class="outils"><select id="op-vue"><option value="0">Qui tient quoi</option>'
      + '<option value="1">Journal des prises</option></select>'
      + '<button type="button" id="op-actualiser" title="Redemander l\'annuaire des guildes">Actualiser</button>'
      + '<span class="faible op-etat" id="op-etat"></span></div><div class="op-zone" id="op-zone"></div>';
    $("#op-vue").value = String(OP.vue);
    $("#op-vue").addEventListener("change", () => { OP.vue = Number($("#op-vue").value); dessinerAvantPostes(); });
    $("#op-actualiser").addEventListener("click", () => dessinerAvantPostes(true));
  }
  if (!Z.pret) return;
  if (!OP.charge || forcer) await chargerAnnuaire();
  if (!OP.charge) return;
  // Sur une guilde son nom, sur un perso celui de sa guilde (_ma_guilde).
  const ent = Z.ent;
  const maGuilde = ent ? (ent.sorte === "guild" ? ent.nom : ent.guilde) || "" : "";
  const v = JSON.parse(await appeler("vue_avant_postes", JSON.stringify(lire("zr-op", {})), maGuilde, OP.vue === 1));
  garder("zr-op", v.fichiers);
  // Le compte des prises qui nous concernent, dans le menu (_maj_compteur_prises).
  $("#op-vue").options[1].textContent = "Journal des prises" + (v.non_lus ? " (" + v.non_lus + ")" : "");
  const zone = $("#op-zone");
  if (v.journal) {
    $("#op-etat").textContent = "";
    zone.className = "op-zone grille-zone liste";
    if (!v.prises.length) {
      zone.innerHTML = '<div class="vide">' + (v.premier ? "Premier relevé : rien à comparer. Les changements de main apparaîtront à partir du prochain."
        : "Aucun changement de main depuis le premier relevé.") + "</div>";
      return;
    }
    const guilde = (nom, img, gagne) => nom ? '<span class="' + (gagne ? "tri-arrivee" : "tri-depart") + '">' + (gagne ? "▲" : "▼") + "</span> "
      + (img ? '<img class="embleme" src="' + esc(img) + '" alt="">' : '<span class="embleme"></span>')
      + ' <span style="color:' + (gagne ? "#4caf50" : "var(--or)") + '">' + esc(nom) + "</span>" : "";
    zone.innerHTML = '<table class="op-journal"><tbody>' + v.prises.map((c, i) => '<tr class="' + zebre(i) + '"><td>'
      + quandCourt(c.at) + "&nbsp;&nbsp; " + esc(c.nom) + "</td><td>" + guilde(c.de, c.embleme_de, false) + "</td><td>"
      + guilde(c.vers, c.embleme_vers, true) + "</td></tr>").join("") + "</tbody></table>";
    return;
  }
  $("#op-etat").textContent = v.entete;
  zone.className = "op-zone op-colonnes";
  const colonne = (peuples) => {
    let rang = 0;
    return '<div class="grille-zone liste"><table class="op"><tbody>' + peuples.map(([nom, liste]) =>
      '<tr><td></td><td colspan="' + (v.pastilles ? 5 : 4) + '" class="op-peuple">' + esc(nom) + "</td><td></td></tr>"
      + liste.map((o) => '<tr class="' + zebre(rang++) + '"><td class="op-bord"></td>'
        + '<td><img class="embleme" src="' + esc(o.embleme) + '" alt=""></td>'
        + (v.pastilles ? "<td>" + (o.change ? pastille(o.change.texte + " (" + quandCourt(o.change.at) + ")") : "") + "</td>" : "")
        + '<td class="' + (o.mien ? "fini" : "") + '">' + esc(o.nom) + '</td><td class="faible op-niv">' + (o.niveau || "—")
        + '</td><td class="' + (o.mien ? "fini" : "") + '">' + esc(o.guilde) + '</td><td class="op-bord"></td></tr>').join("")).join("")
      + "</tbody></table>" + (peuples === v.peuples.slice(2) && v.orphelins ? '<div class="faible op-hors">Hors carte : ' + esc(v.orphelins) + "</div>" : "")
      + "</div>";
  };
  zone.innerHTML = colonne(v.peuples.slice(0, 2)) + colonne(v.peuples.slice(2));
}

// --- Meteo / forage (page_meteo.py, page_gisements.py)
//
// Comme ZyRoom-Qt : la courbe, ce qui sort et les gisements, d'apres le
// releve publie (forage.json) ; ni le bouton du releve, ni les MP a verifier.

const M = { charge: false, enCours: false, vue: null, minuteur: null, ouverte: null };

async function chargerMeteo() {
  if (M.enCours) return;
  M.enCours = true;
  if ($("#m-actualiser")) $("#m-actualiser").disabled = true;
  try {
    const continents = await appeler("meteo_continents");
    const [m, t, f] = await Promise.all([
      fetch(API + "/weather.php?continent=" + continents + "&cycles=40&offset=6", { cache: "no-store" }).then((r) => r.text()),
      fetch(API + "/time.php?format=xml", { cache: "no-store" }).then((r) => r.text()).catch(() => ""),
      fetch(DEPOT + "forage.json", { cache: "no-cache" }).then((r) => (r.ok ? r.text() : "")).catch(() => ""),
    ]);
    await appeler("meteo_charger", m, t, f);
    M.charge = true;
  } catch (er) {
    if ($("#m-entete")) $("#m-entete").textContent = "Météo indisponible : " + er.message;
  }
  M.enCours = false;
  if ($("#m-actualiser")) $("#m-actualiser").disabled = false;
}

async function dessinerMeteo(forcer) {
  if (!$("#m-courbe")) {
    $("#page").innerHTML = '<div class="outils"><span class="m-entete" id="m-entete">Lecture de la météo…</span>'
      + '<button type="button" id="m-actualiser">Actualiser</button></div>'
      + '<canvas id="m-courbe"></canvas><div class="m-titre" id="m-titre"></div><div class="m-zones" id="m-zones"></div>';
    $("#m-actualiser").addEventListener("click", () => dessinerMeteo(true));
    $("#m-zones").addEventListener("click", (ev) => {
      const a = ev.target.closest("[data-gisement]");
      if (a) { ev.preventDefault(); ouvrirGisement(a.dataset.gisement); }
    });
    new ResizeObserver(() => courbe()).observe($("#m-courbe"));
  }
  if (!Z.pret) return;
  if (!M.charge || forcer) await chargerMeteo();
  if (!M.charge) return;
  await majMeteo();
  // Le temps d'Atys avance tout seul : on recale toutes les dix secondes,
  // sans rien redemander tant que la prevision remplit la courbe.
  if (!M.minuteur) M.minuteur = setInterval(() => { if (Z.page === "meteo") majMeteo(); }, 10000);
}

async function majMeteo() {
  const v = JSON.parse(await appeler("meteo_vue"));
  if (v.vide) return;
  M.vue = v;
  if (v.recharger && !M.enCours) chargerMeteo();
  if (!$("#m-courbe")) return;
  if (v.entete) {
    $("#m-entete").innerHTML = "humidité <b>" + esc(v.entete.taux) + "</b>"
      + (v.entete.pendant ? "<b> pendant " + esc(v.entete.pendant) + "</b>" : "")
      + "&nbsp;&nbsp; — &nbsp;&nbsp;" + esc(v.entete.decor);
  }
  courbe();
  $("#m-titre").textContent = v.zones ? "MP qui pop maintenant" : "";
  $("#m-zones").innerHTML = (v.zones || []).map(([zone, blocs]) => '<div class="m-zone"><div class="m-tete zebre">' + esc(zone)
    + '</div><div class="m-corps">' + (blocs.length ? blocs.map((b) => '<div class="m-mot ' + (b.a_confirmer ? "a-confirmer" : "peuple") + '">'
      + esc(b.mot) + '</div><div class="m-grille">' + b.familles.map(([fam, img, mats]) => '<div class="m-fam"><div class="faible">'
        + esc(fam) + "</div>" + (img ? '<img src="' + esc(img) + '" alt="">' : "") + '</div><div class="m-mats">'
        + mats.map(([m, lien]) => lien ? '<a href="#" data-gisement="' + esc(lien) + '">' + esc(m) + "</a>" : esc(m)).join(", ")
        + "</div>").join("") + "</div>").join("") : '<div class="faible">Pas encore relevé</div>') + "</div></div>").join("");
  if (M.ouverte) majGisement();
}

// La courbe d'humidite (page_meteo._dessiner_courbe) : des paliers relies
// en oblique la derniere heure de chaque cycle, les nuits en bandes, les
// seuils du jeu en pointille, le present fige a 15 % de la largeur.
function courbe() {
  const c = $("#m-courbe");
  const v = M.vue;
  if (!c || !v || v.cycles.length < 2) return;
  const w = c.clientWidth, h = c.clientHeight;
  const r = window.devicePixelRatio || 1;
  c.width = Math.round(w * r); c.height = Math.round(h * r);
  const ctx = c.getContext("2d");
  ctx.setTransform(r, 0, 0, r, 0, 0);
  ctx.clearRect(0, 0, w, h);
  const FEN = 40, ANCRE = 0.15, mg = 34, mb = 20;
  const large = w - mg, haut = h - mb;
  const gauche = v.heure_atys - ANCRE * FEN;
  const X = (hr) => mg + large * (hr - gauche) / FEN;
  const Y = (val) => haut * (1 - Math.min(1, Math.max(0, val)));
  const HPC = v.heures_par_cycle, TR = v.transition;
  ctx.save();
  ctx.beginPath(); ctx.rect(mg, 0, large, haut); ctx.clip();
  ctx.fillStyle = "rgba(255,255,255,.06)";
  for (let hr = Math.floor(gauche) - 1; hr <= Math.floor(gauche + FEN) + 2; hr++) {
    const hd = ((hr % 24) + 24) % 24;
    if (hd >= 22 || hd < 3) ctx.fillRect(X(hr), 0, large / FEN, haut);
  }
  const trace = () => {
    for (const [cy, val] of v.cycles) {
      const debut = cy * HPC;
      ctx.lineTo(X(debut), Y(val));
      ctx.lineTo(X(debut + HPC - TR), Y(val));
    }
  };
  ctx.beginPath();
  ctx.moveTo(X(v.cycles[0][0] * HPC), haut);
  trace();
  ctx.lineTo(X((v.cycles[v.cycles.length - 1][0] + 1) * HPC), haut);
  ctx.closePath();
  ctx.fillStyle = "rgba(64,122,105,.35)"; ctx.fill();
  ctx.beginPath(); trace();
  ctx.strokeStyle = "rgb(89,173,148)"; ctx.lineWidth = 2; ctx.stroke();
  ctx.restore();
  ctx.font = "10px Cantarell, 'Noto Sans', sans-serif";
  ctx.lineWidth = 1;
  for (const [g, t] of [[0.334, "33,4"], [0.666, "66,6"]]) {
    ctx.strokeStyle = "rgba(255,255,255,.18)"; ctx.beginPath(); ctx.moveTo(mg, Y(g)); ctx.lineTo(w, Y(g)); ctx.stroke();
    ctx.fillStyle = "rgba(255,255,255,.35)"; ctx.fillText(t, 2, Y(g) - 3);
  }
  ctx.setLineDash([4, 4]);
  v.seuils.forEach((s, i) => {
    ctx.strokeStyle = "rgba(230,102,102,.55)"; ctx.beginPath(); ctx.moveTo(mg, Y(s)); ctx.lineTo(w, Y(s)); ctx.stroke();
    ctx.fillStyle = "rgba(255,255,255,.55)"; ctx.fillText(["16,7", "50", "83,4"][i], 2, Y(s) - 3);
  });
  ctx.setLineDash([]);
  ctx.strokeStyle = "rgb(232,194,89)"; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(X(v.heure_atys), 0); ctx.lineTo(X(v.heure_atys), haut); ctx.stroke();
  ctx.strokeStyle = "rgba(255,255,255,.35)"; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(mg, haut); ctx.lineTo(w, haut); ctx.stroke();
  // L'heure reelle tous les quarts d'heure, un tiret toutes les cinq minutes.
  const maintenant = new Date();
  const repere = new Date(maintenant); repere.setMinutes(0, 0, 0); repere.setHours(repere.getHours() - 1);
  for (let i = 0; i < 48; i++) {
    repere.setMinutes(repere.getMinutes() + 5);
    const atys = v.heure_atys + (repere - maintenant) / 60000 / v.minutes_par_heure;
    if (atys < gauche || atys > gauche + FEN) continue;
    const ecrite = repere.getMinutes() % 15 === 0;
    ctx.strokeStyle = "rgba(255,255,255," + (ecrite ? .62 : .42) + ")";
    ctx.beginPath(); ctx.moveTo(X(atys), haut); ctx.lineTo(X(atys), haut + (ecrite ? 6 : 4)); ctx.stroke();
    if (!ecrite) continue;
    ctx.fillStyle = "rgba(255,255,255,.55)";
    const texte = deux(repere.getHours()) + "h" + (repere.getMinutes() ? deux(repere.getMinutes()) : "");
    ctx.fillText(texte, Math.min(w - 30, Math.max(0, X(atys) - 14)), h - 4);
  }
}

// --- La carte d'un gisement

async function ouvrirGisement(adresse) {
  let d = $("#gisement");
  if (!d) {
    d = document.createElement("dialog");
    d.id = "gisement";
    d.className = "gisement";
    d.innerHTML = '<div class="g-tete"><strong id="g-titre"></strong><button type="button" id="g-fermer">Fermer</button></div>'
      + '<div id="g-entete"></div><div class="g-note" id="g-maintenant"></div><div class="g-note" id="g-apres"></div>'
      + '<canvas id="g-carte"></canvas><div class="g-lieux" id="g-lieux"></div>'
      + '<div class="g-note faible">Positions : relevé de ballisticmystix.net, avec l\'accord de son auteur</div>';
    document.body.appendChild(d);
    d.querySelector("#g-fermer").addEventListener("click", () => d.close());
    d.addEventListener("close", () => { M.ouverte = null; });
    M.carte = carteAtys(d.querySelector("#g-carte"), (ctx, e, mx, my, w, h) => {
      const g = M.ouverte;
      if (!g) return;
      if (!M.carte.etat.cadre && w) cadrer(w, h, g.points);
      // Les points trop proches n'en font qu'un ; les gris d'abord, les verts par-dessus.
      const vus = new Map();
      for (const [px, py, lieu, actif] of g.points) {
        const x = mx + px * e, y = my + py * e;
        const cle = Math.floor(x / SEUIL_GROUPE) + ":" + Math.floor(y / SEUIL_GROUPE);
        if (!vus.has(cle)) vus.set(cle, [x, y, lieu, actif, 0]);
        vus.get(cle)[4]++;
      }
      for (const vert of [false, true]) {
        for (const [x, y, lieu, actif, n] of vus.values()) {
          if (actif !== vert) continue;
          for (const [rr, col] of [[6.5, CERNE], [4, actif ? "rgb(71,209,92)" : "rgb(148,148,153)"]]) {
            ctx.fillStyle = col; ctx.beginPath(); ctx.arc(x, y, rr, 0, 6.2832); ctx.fill();
          }
          nomCerne(ctx, n === 1 ? lieu : lieu + " ×" + n, x + 10, y - 6);
        }
      }
    });
  }
  M.ouverte = { adresse };
  M.carte.etat.cadre = false;
  await majGisement();
  if (!d.open) d.showModal();
  M.carte.dessiner();
}

// Le cadrage du premier affichage (page_gisements._cadre_gisement).
function cadrer(w, h, points) {
  const etat = M.carte.etat;
  etat.cadre = true;
  if (!points.length) return;
  const xs = points.map((p) => p[0]), ys = points.map((p) => p[1]);
  const cx = (Math.min(...xs) + Math.max(...xs)) / 2, cy = (Math.min(...ys) + Math.max(...ys)) / 2;
  const large = Math.max(Math.max(...xs) - Math.min(...xs), 300), haute = Math.max(Math.max(...ys) - Math.min(...ys), 260);
  const base = Math.min(w / 4000, h / 3000);
  const voulue = Math.min(0.55 * w / large, 0.55 * h / haute);
  etat.zoom = Math.min(ZOOM_MAX, Math.max(1, voulue / base));
  const e = base * etat.zoom;
  const dx = Math.max(0, (4000 * e - w) / 2), dy = Math.max(0, (3000 * e - h) / 2);
  etat.gx = Math.max(-dx, Math.min(dx, e * (2000 - cx)));
  etat.gy = Math.max(-dy, Math.min(dy, e * (1500 - cy)));
}

async function majGisement() {
  const g = JSON.parse(await appeler("gisement", M.ouverte.adresse));
  M.ouverte = Object.assign({ adresse: M.ouverte.adresse }, g);
  $("#g-titre").textContent = g.titre;
  $("#g-entete").innerHTML = "<b>" + esc(g.mot) + "</b> &nbsp;·&nbsp; " + g.nombre + (g.nombre > 1 ? " gisements" : " gisement");
  $("#g-maintenant").textContent = g.maintenant;
  $("#g-apres").textContent = g.apres;
  $("#g-lieux").innerHTML = g.lieux.map(([l, actif]) => '<span class="' + (actif ? "" : "faible") + '">' + esc(l) + "</span>").join("");
  M.carte.dessiner();
}

// ------------------------------------------------------------ les autres pages

function dessinerAutrePage() {
  const noms = { journal: "Journal", competences: "Compétences", effectif: "Effectif", perdu: "Perdu ?",
                 "avant-postes": "Avant-postes", meteo: "Météo / forage" };
  $("#page").innerHTML = '<div class="page-autre">' + esc(noms[Z.page] || Z.page) + " — à venir dans ZyRoom-web.</div>";
}

function allerA(page) {
  Z.page = page;
  document.querySelectorAll(".nav [data-page]").forEach((b) => b.setAttribute("aria-pressed",
    String(b.dataset.page === page || (b.dataset.page === "bonus" && !["inventaire", "journal"].includes(page)))));
  $("#page").innerHTML = "";
  if (page === "inventaire") dessinerInventaire();
  else if (page === "journal") dessinerJournal(true);
  else dessinerBonus();
}
document.querySelectorAll(".nav [data-page]").forEach((b) => b.addEventListener("click", () => {
  if (b.dataset.page === "bonus") { const p = $("#pop-bonus"); fermerPops(p); p.hidden = !p.hidden; return; }
  allerA(b.dataset.page);
}));
$("#pop-bonus").addEventListener("click", (ev) => {
  const b = ev.target.closest("[data-bonus]");
  if (!b) return;
  fermerPops();
  allerA(b.dataset.bonus);
});

// ------------------------------------------------------------ barre du haut

// Le zoom grossit toute l'application, texte compris, comme dans ZyRoom-GTK
// (« je veux que le zoom grossisse entierement les applis ») : la propriete
// CSS zoom fait exactement cela. Les icones restent donc a 48 px CSS.
function appliquerZoom() {
  document.body.style.zoom = Z.zoom / 100;
}
function zoomer(sens) {
  const i = PALIERS.indexOf(Z.zoom);
  Z.zoom = PALIERS[Math.max(0, Math.min(PALIERS.length - 1, (i < 0 ? 1 : i) + sens))];
  garder("zr-zoom", Z.zoom);
  appliquerZoom();
}
$("#b-moins").addEventListener("click", () => zoomer(-1));
$("#b-plus").addEventListener("click", () => zoomer(1));
$("#b-synchro").addEventListener("click", () => { synchroniser(); majSaison(); });
$("#b-menu").addEventListener("click", () => { const p = $("#pop-menu"); fermerPops(p); p.hidden = !p.hidden; });
$("#m-apropos").addEventListener("click", () => { fermerPops(); $("#apropos").showModal(); });

$("#b-retrait").addEventListener("click", () => {
  const e = entiteCourante();
  if (e.sorte !== "character" || !confirm("Retirer " + e.nom + " de ce navigateur ?")) return;
  Z.persos = Z.persos.filter((p) => p.id !== e.id);
  garder("zr-persos", Z.persos);
  garderFlux(cacheXml(e), null);
  Z.ent = null;
  choisirEntite("");
});

$("#b-ajout").addEventListener("click", () => {
  $("#ajout-cle").value = "";
  $("#ajout-message").textContent = "";
  $("#ajout").showModal();
});
$("#ajout-annuler").addEventListener("click", () => $("#ajout").close());
$("#ajout-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const cle = $("#ajout-cle").value.trim();
  // ryzom_api.is_api_key : quarante et un signes, « c » pour un personnage.
  if (!/^[A-Za-z0-9]{41}$/.test(cle) || cle[0] !== "c") {
    $("#ajout-message").textContent = cle[0] === "g" ? "C'est une clé de guilde : le hall est déjà là."
      : "Une clé de personnage fait 41 caractères et commence par « c ».";
    return;
  }
  $("#ajout-message").textContent = "Vérification auprès de l'API…";
  try {
    const flux = await telecharger({ sorte: "character", cle });
    const ent = await lireFlux({ sorte: "character" }, flux);
    if (!Z.persos.some((p) => p.id === ent.id)) Z.persos.push({ id: ent.id, nom: ent.nom, cle, image: ent.portrait });
    garder("zr-persos", Z.persos);
    garderFlux(cacheXml({ sorte: "character", id: ent.id }), flux);
    await journaliser({ sorte: "character", id: ent.id }, flux.xml);
    $("#ajout").close();
    Z.synchro.add("character:" + ent.id);
    Z.courante = "character:" + ent.id;
    garder("zr-entite", Z.courante);
    montrer({ sorte: "character", id: ent.id }, ent, true);
  } catch (souci) {
    $("#ajout-message").textContent = "Refusée : " + souci.message;
  }
});

// ------------------------------------------------------------ demarrage

appliquerZoom();
dessinerEntites();
if (!Z.jeton) ouvrirPorte();
appeler("demarrer").then((meta) => {
  Z.meta = JSON.parse(meta);
  Z.pret = true;
  $("#page").innerHTML = "";
  pageInventaire();
  choisirEntite(Z.courante);
  majSaison();
  // Toutes les trois minutes, comme _refresh_season_tick.
  setInterval(majSaison, 3 * 60 * 1000);
}).catch((souci) => {
  $("#page").innerHTML = '<div class="chargement">ZyRoom n\'a pas pu démarrer : ' + esc(souci.message) + "</div>";
});
})();
