// L'onglet KipeeCraft de la page des MP.
//
// Le calcul est celui de kipeecraft-py, en Python, dans un Web Worker
// (travail.js + Pyodide) : cette page ne fait qu'afficher et demander. Le
// lien avec le hall passe par les variables de index.html -- `stock` (fiche
// -> piles) et `noms.mp` (MP KipeeCraft -> fiches du jeu).
//
// Ce qui est propre a chaque joueur (recette en cours, materiaux ecartes,
// formules retouchees) reste dans son navigateur : rien ne part au serveur.
(function () {
"use strict";

// ------------------------------------------------------------ worker

// Le meme jeton de version que kc.js lui-meme, pour relire le worker avec.
const VERSION = document.currentScript ? new URL(document.currentScript.src).search : "";
let travail = null;
let numero = 0;
const attentes = new Map();
let surAvance = null;

function appeler(op, ...args) {
  return new Promise((ok, ko) => {
    const id = ++numero;
    attentes.set(id, { ok, ko });
    travail.postMessage({ id, op, args });
  });
}
async function appelerJson(op, ...args) { return JSON.parse(await appeler(op, ...args)); }

function lancer() {
  if (travail) return;
  travail = new Worker("kc/travail.js" + VERSION);
  travail.onmessage = (ev) => {
    const d = ev.data;
    if (d.avance) { if (surAvance) surAvance(d.avance); return; }
    const a = attentes.get(d.id);
    attentes.delete(d.id);
    if (a) { if (d.ok) a.ok(d.valeur); else a.ko(new Error(d.erreur)); }
  };
  travail.onerror = (ev) => { S.erreur = ev.message || "worker en panne"; dessiner(); };
  appeler("demarrer", lire("kc-retouches", {}))
    .then((texte) => { preparer(JSON.parse(texte)); dessiner(); recalculer(); })
    .catch((souci) => { S.erreur = souci.message; dessiner(); });
}

// ------------------------------------------------------------ etat

function lire(cle, defaut) {
  try { const v = localStorage.getItem(cle); return v ? JSON.parse(v) : defaut; } catch (e) { return defaut; }
}
function garder(cle, valeur) {
  try { localStorage.setItem(cle, JSON.stringify(valeur)); } catch (e) {}
}

const RACES = ["Indifférente", "Fyros", "Matis", "Tryker", "Zoraï"];
const COLONNES = [["", "—"], ["moyennes", "Matériaux"], ["precraft", "Précraft"],
                  ["precraftx", "Précraft exact"], ["postcraft", "Postcraft"],
                  ["postcraftx", "Postcraft exact"]];
const ICONES = new Set(("amber bark beak blank bone bud claw eye fang fiber flesh hoof horn larva "
  + "leather ligament mandible moss mushroom nail oil pelvis resin rostrum sap secretion seed "
  + "shell skin spine sting tail tooth trunk whiskers wing woodnode wood").split(" "));
// Dans les listes, l'ordre des filtres de la page : Primes, Desert, Foret...
const ORDRE_E = [6, 4, 2, 5, 3, 7, 1];

const S = {
  meta: null, erreur: "",
  sous: lire("kc-sous", "simu"),
  prefs: Object.assign({ qualite: 250, rite: false, qformule: 0, gauche: "precraft",
                         droite: "postcraft" }, lire("kc-prefs", {})),
  palier: "HIGH",
  recette: null,
  resultat: null,
  detail: false,
  ecartes: new Set(lire("kc-ecartes", [])),
  choix: null,
  dernierGrade: 5,
  bij: null, bijRes: null, bijEnCours: false, bijAvance: "",
  base: { piece: "", grade: 0, eco: 0, origine: 0, texte: "", hall: false, ecartes: true },
  form: null,
  audit: null, auditEnCours: false,
};

let index = new Map();   // "piece|cle" -> materiau

function preparer(meta) {
  S.meta = meta;
  index = new Map();
  for (const [piece, liste] of Object.entries(meta.materiaux)) {
    for (const m of liste) { m.p = piece; index.set(piece + "|" + m.k, m); }
  }
  const gardee = lire("kc-recette", null);
  const plan = gardee && planDe(gardee.plan);
  if (plan && gardee.cases && gardee.cases.length === plan.pieces.length) {
    // Une MP disparue de la base ne doit pas casser la recette entiere.
    gardee.cases = gardee.cases.map((c, i) => c.filter(([k]) => index.has(plan.pieces[i][0] + "|" + k)));
    S.recette = gardee;
    S.palier = plan.palier;
  } else {
    nouvelle(S.meta.plans.find((p) => p.palier === S.palier));
  }
  S.base.piece = S.base.piece || "blade";
  const bijoux = plansBijoux();
  S.bij = Object.assign(bijVierge(bijoux[bijoux.length - 1].id), lire("kc-bijouterie", {}));
}

function planDe(id) { return S.meta.plans.find((p) => p.id === Number(id)); }
function plansBijoux() {
  return S.meta.plans.filter((p) => p.pieces.length === 2 && p.pieces[0][0] === "jewelsetting"
                                    && p.pieces[1][0] === "jewel");
}
function nouvelle(plan) {
  S.recette = { plan: plan.id, option: plan.options[0] || 0, commentaire: "",
                cases: plan.pieces.map(() => []) };
  S.palier = plan.palier;
  sauverRecette();
}
function sauverRecette() { garder("kc-recette", S.recette); }

// ------------------------------------------------------------ outils

const nfr = (n, d) => n.toLocaleString("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d });
function materiau(piece, cle) { return index.get(piece + "|" + cle); }
function nomComplet(m) {
  return S.meta.grades[m.g][0] + " " + S.meta.ecos[m.e][0] + " " + m.n + " " + m.tl;
}
function ecoClasse(m) { return "eco-" + S.meta.ecos[m.e][1]; }
function icone(type) {
  const n = type.toLowerCase();
  return "kc/icones/" + (ICONES.has(n) ? n : "unknown") + ".png";
}
function qualites(m) {
  if (m.q0 < 0 && m.q1 < 0) return "";
  if (m.q0 < 0) return "≤ " + m.q1;
  if (m.q1 < 0) return "≥ " + m.q0;
  return m.q0 + "–" + m.q1;
}
function ecarte(m) { return m.i || S.ecartes.has(m.p + "|" + m.k); }

// Ce que le hall en a, en piles de qualite >= qmin. null : MP sans fiche
// connue du jeu, on ne sait pas la compter.
function auHall(cle, qmin) {
  const e = (typeof noms === "object" && noms.mp) ? noms.mp[cle] : null;
  if (!e) return null;
  let n = 0;
  for (const f of e.fiches) for (const [q, k] of (stock.get(f) || [])) if (q >= (qmin || 0)) n += k;
  return n;
}
function hallHtml(cle, qmin) {
  const n = auHall(cle, qmin);
  if (n === null) return '<span class="faible">—</span>';
  return n ? '<span class="kc-hall">' + nombre(n) + "</span>" : '<span class="faible">0</span>';
}

function telecharger(nom, texte) {
  // KipeeCraft lit du Windows-1252 : on ecrit octet par octet ce qui y tient.
  const octets = new Uint8Array(texte.length);
  for (let i = 0; i < texte.length; i++) {
    const c = texte.charCodeAt(i);
    octets[i] = c < 256 ? c : 63;
  }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([octets], { type: "application/octet-stream" }));
  a.download = nom.replace(/[\\/:*?"<>|]+/g, "-");
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
}
function choisirFichier(extension) {
  return new Promise((ok) => {
    const i = document.createElement("input");
    i.type = "file";
    i.accept = extension;
    i.addEventListener("change", async () => {
      const f = i.files[0];
      if (!f) return;
      ok({ nom: f.name, texte: new TextDecoder("windows-1252").decode(await f.arrayBuffer()) });
    });
    i.click();
  });
}
function options(plan, valeur) {
  const intitules = plan.intitule.split(" / ");
  return plan.options.map((o) => '<option value="' + o + '"' + (o === valeur ? " selected" : "") + ">"
    + esc(plan.options.length === intitules.length ? intitules[plan.options.indexOf(o)] : "Variante " + o)
    + "</option>").join("");
}
function selecteur(attr, liste, valeur, extra) {
  return "<select " + attr + (extra || "") + ">" + liste.map(([v, t]) => '<option value="' + esc(v) + '"'
    + (String(v) === String(valeur) ? " selected" : "") + ">" + esc(t) + "</option>").join("") + "</select>";
}

// ------------------------------------------------------------ dessin

let racine = null;

function dessiner() {
  if (!racine || !racine.isConnected) return;
  if (S.erreur) {
    racine.innerHTML = '<p class="inconnue">KipeeCraft n\'a pas pu démarrer : ' + esc(S.erreur) + "</p>";
    return;
  }
  if (!S.meta) {
    racine.innerHTML = '<p class="kc-attente">Chargement de KipeeCraft… La première fois, le navigateur '
      + "télécharge Python (une dizaine de Mo) ; ensuite il le garde.</p>";
    return;
  }
  const onglets = [["simu", "Simulateur"], ["bij", "Bijouterie"], ["base", "Base de matériaux"],
                   ["form", "Formules"], ["audit", "Audit"]];
  racine.innerHTML = '<div class="onglets kc-sous">' + onglets.map(([k, t]) =>
    '<button type="button" data-kc="sous" data-v="' + k + '" aria-pressed="' + (S.sous === k) + '">'
    + t + "</button>").join("") + '<span class="faible kc-resume">' + esc(S.meta.resume) + "</span></div>"
    + '<div id="kc-corps">' + ({ simu: vueSimu, bij: vueBij, base: vueBase, form: vueForm,
                                 audit: vueAudit }[S.sous] || vueSimu)() + "</div>";
  if (S.sous === "form" && !S.form) chargerFormules();
}

// ------------------------------------------------------------ simulateur

function vueSimu() {
  const plan = planDe(S.recette.plan);
  const p = S.prefs;
  const plans = S.meta.plans.filter((x) => x.palier === S.palier);
  return '<div class="kc-barre">'
    + selecteur('data-kc="palier"', S.meta.paliers, S.palier, ' title="Palier de qualité"')
    + selecteur('data-kc="plan"', plans.map((x) => [x.id, x.intitule]), plan.id, ' title="Objet à fabriquer"')
    + (plan.options.length > 1 ? '<select data-kc="option" title="Variante">' + options(plan, S.recette.option) + "</select>" : "")
    + '<button type="button" data-kc="vider">Vider</button>'
    + '<button type="button" data-kc="ouvrir">Ouvrir un .kc</button>'
    + '<button type="button" data-kc="enregistrer">Télécharger le .kc</button>'
    + "</div>"
    + '<div class="kc-barre kc-reglages">'
    + '<label title="Qualité visée de l\'objet ; les matériaux peuvent l\'abaisser">Qualité <input type="number" data-kc="pref" data-v="qualite" min="1" max="250" value="' + p.qualite + '"></label>'
    + '<label title="Valeur de &lt;quality&gt; dans les formules (dégâts, protections maximales). 0 : part fixe seulement">Q des formules <input type="number" data-kc="pref" data-v="qformule" min="0" max="250" value="' + p.qformule + '"></label>'
    + '<label title="Rite de durabilité : +20 % de durabilité"><input type="checkbox" data-kc="pref" data-v="rite"' + (p.rite ? " checked" : "") + "> Rite</label>"
    + "</div>"
    + '<div class="kc-simu"><div class="kc-gauche" id="kc-apercu">' + vueApercu() + "</div>"
    + '<div class="kc-droite" id="kc-pieces">' + vuePieces() + "</div></div>";
}

function vueApercu() {
  const plan = planDe(S.recette.plan);
  const r = S.resultat;
  let resume = "Recette vide — choisis des matériaux.";
  if (r && !r.vide) {
    const morceaux = ["Q" + r.qualite, r.grade ? S.meta.grades[r.grade][0] : "—",
                      r.couleur ? S.meta.couleurs[r.couleur][0] : "—",
                      "moyenne " + nfr(r.moyenne, 1) + " %", "coût " + r.cout];
    if (r.boost > 1) morceaux.push("boost ×" + nfr(r.boost, 4));
    else if (r.perdu > 0.005) morceaux.push(nfr(r.perdu, 2) + " perdu");
    morceaux.push(r.complete ? "complète" : "incomplète");
    resume = morceaux.join(" · ");
  }
  const choixCol = (cote) => selecteur('data-kc="colonne" data-v="' + cote + '"', COLONNES, S.prefs[cote]);
  let lignes = "";
  for (const s of plan.stats) {
    const pc = r ? r.precraft[s] : undefined;
    const classe = pc == null ? "" : pc < 21 ? "kc-bas" : pc >= 90 ? "kc-haut" : "";
    lignes += '<tr class="' + classe + '"><td class="n">' + valeur(r, s, S.prefs.gauche)
      + '</td><td class="n">' + valeur(r, s, S.prefs.droite) + "</td><td>" + esc(S.meta.stats[s][0]) + "</td></tr>";
  }
  return "<h2>" + esc(plan.complet) + "</h2>"
    + '<p class="kc-ligne">' + esc(resume) + "</p>"
    + (r && r.erreur ? '<p class="inconnue">' + esc(r.erreur) + "</p>" : "")
    + (r && !r.formules ? '<p class="faible">Pas de formules de postcraft pour ce plan.</p>' : "")
    + '<table class="kc-stats"><thead><tr><th class="n">' + choixCol("gauche") + '</th><th class="n">'
    + choixCol("droite") + "</th><th>Caractéristique</th></tr></thead><tbody>" + lignes + "</tbody></table>"
    + '<label class="kc-com">Commentaire<textarea data-kc="commentaire" rows="3">' + esc(S.recette.commentaire) + "</textarea></label>"
    + '<p><button type="button" data-kc="detail" aria-pressed="' + S.detail + '">Détail de la recette</button></p>'
    + (S.detail ? vueDetail() : "");
}

// Les colonnes arrondies tronquent, comme l'original : 94,77 s'y lit 94.
function valeur(r, stat, colonne) {
  if (!r || !colonne) return "";
  const exacte = colonne.endsWith("x");
  const v = r[exacte ? colonne.slice(0, -1) : colonne][stat];
  if (v == null) return "";
  return exacte ? nfr(v, 2) : String(Math.trunc(v));
}

// Le tableau croise de l'original : une colonne par materiau employe.
function vueDetail() {
  const plan = planDe(S.recette.plan);
  const employes = [];
  S.recette.cases.forEach((c, i) => c.forEach(([k, n]) => employes.push([plan.pieces[i][0], materiau(plan.pieces[i][0], k), n])));
  if (!employes.length) return '<p class="faible">Recette vide.</p>';
  let h = '<div class="cadre"><table class="kc-detail"><thead><tr><th class="n">unités</th><th>caractéristique</th>'
    + employes.map(([, m, n]) => '<th class="n" title="' + esc(nomComplet(m)) + '"><span class="' + ecoClasse(m) + '">'
      + esc(m.n) + "</span><br>×" + n + "</th>").join("") + '<th class="n">moyenne</th></tr></thead><tbody>';
  const r = S.resultat;
  for (const s of plan.stats) {
    const porteurs = employes.reduce((t, [p, , n]) => t + (S.meta.pieces[p].stats.includes(s) ? n : 0), 0);
    h += '<tr><td class="n">' + (porteurs ? porteurs + "×" : "—") + "</td><td>" + esc(S.meta.stats[s][0]) + "</td>"
      + employes.map(([p, m]) => {
        const rang = S.meta.pieces[p].stats.indexOf(s);
        return '<td class="n">' + (rang < 0 ? '<span class="faible">·</span>' : m.v[rang]) + "</td>";
      }).join("")
      + '<td class="n">' + (r && r.moyennes[s] != null ? nfr(r.moyennes[s], 2) : "") + "</td></tr>";
  }
  return h + "</tbody></table></div>";
}

function vuePieces() {
  const plan = planDe(S.recette.plan);
  return plan.pieces.map(([piece, voulu], i) => {
    const cases = S.recette.cases[i];
    const pose = cases.reduce((t, [, n]) => t + n, 0);
    return '<div class="kc-piece"><div class="kc-titre"><b>' + esc(S.meta.pieces[piece].nom) + " "
      + pose + "/" + voulu + "</b><span></span></div><div class=\"kc-cases\">"
      + cases.map(([k, n], j) => caseHtml(materiau(piece, k), n, i, j)).join("")
      + (pose < voulu ? '<button type="button" class="kc-case kc-vide" data-kc="ajouter" data-i="' + i
        + '" title="Choisir un matériau (' + (voulu - pose) + ' libre(s))">+</button>' : "")
      + "</div></div>";
  }).join("") + '<p class="faible kc-aide">Clic sur une case pleine : remplacer ou retirer. Clic droit : retirer.</p>';
}

function caseHtml(m, n, i, j) {
  const q = m.q1 >= 0 ? "Q" + m.q1 : "";
  return '<button type="button" class="kc-case" data-kc="case" data-i="' + i + '" data-j="' + j + '"'
    + ' style="border-color:var(--eco-' + S.meta.ecos[m.e][1] + ', #909090)"'
    + ' title="' + esc(nomComplet(m) + "\n" + n + " unité(s)\nQualité " + (qualites(m) || "inconnue")) + '">'
    + '<img src="' + icone(m.t) + '" alt="">'
    + '<span class="kc-c-nom">' + esc(m.n.toUpperCase()) + "</span>"
    + (q ? '<span class="kc-c-q">' + q + "</span>" : "")
    + '<span class="kc-c-x">x' + n + "</span>"
    + '<span class="kc-c-g kc-coul-' + S.meta.couleurs[m.c][1] + '">' + esc(S.meta.grades[m.g][1]) + "</span></button>";
}

async function recalculer() {
  if (!S.meta) return;
  try {
    S.resultat = await appelerJson("calculer", Object.assign({}, S.recette, {
      qualite: S.prefs.qualite, rite: S.prefs.rite, qformule: S.prefs.qformule }));
  } catch (souci) {
    S.resultat = null;
    bandeau("Calcul impossible : " + souci.message, true);
  }
  const zone = document.getElementById("kc-apercu");
  if (zone) zone.innerHTML = vueApercu();
}

function apresChangement() {
  sauverRecette();
  const zone = document.getElementById("kc-pieces");
  if (zone) zone.innerHTML = vuePieces();
  recalculer();
}

// ------------------------------------------------------------ choix d'un materiau

function ouvrirChoix(i, j) {
  const plan = planDe(S.recette.plan);
  const [piece, voulu] = plan.pieces[i];
  const cases = S.recette.cases[i];
  const pose = cases.reduce((t, [, n]) => t + n, 0);
  const actuel = j == null ? null : cases[j];
  const m = actuel ? materiau(piece, actuel[0]) : null;
  const libre = voulu - pose + (actuel ? actuel[1] : 0);
  if (libre <= 0) return;
  S.choix = Object.assign({ fores: true, lootes: true, ecartes: true, hall: false, qmin: 0,
                            eco: 0, texte: "" }, S.choix || {}, {
    i, j, piece, libre, quantite: actuel ? actuel[1] : libre,
    grade: m ? m.g : S.dernierGrade, sel: m ? m.k : null });
  let d = document.getElementById("kc-choix");
  if (!d) {
    d = document.createElement("dialog");
    d.id = "kc-choix";
    document.body.appendChild(d);
    d.addEventListener("click", surClicChoix);
    d.addEventListener("dblclick", (ev) => {
      const l = ev.target.closest("[data-k]");
      if (l) { S.choix.sel = l.dataset.k; valider(); }
    });
    d.addEventListener("input", surSaisieChoix);
    d.addEventListener("change", surSaisieChoix);
    d.addEventListener("close", () => { S.choix.ouvert = false; });
  }
  dessinerChoix(true);
  d.showModal();
  S.choix.ouvert = true;
}

function listeChoix() {
  const c = S.choix;
  const texte = c.texte.trim().toLowerCase();
  return S.meta.materiaux[c.piece].filter((m) =>
    m.g === c.grade && (c.fores || m.o !== 0) && (c.lootes || m.o !== 1)
    && (!c.eco || m.e === c.eco) && (c.ecartes || !ecarte(m))
    && (!c.qmin || m.q1 < 0 || m.q1 >= c.qmin)
    && (!texte || nomComplet(m).toLowerCase().includes(texte) || m.t.toLowerCase().includes(texte))
    && (!c.hall || auHall(m.k, c.qmin) > 0))
    .sort((a, b) => ORDRE_E.indexOf(a.e) - ORDRE_E.indexOf(b.e) || a.n.localeCompare(b.n));
}

function dessinerChoix(tout) {
  const c = S.choix;
  const d = document.getElementById("kc-choix");
  const liste = listeChoix();
  const lignes = liste.map((m) => {
    const moy = m.v.reduce((t, v) => t + v, 0) / (m.v.length || 1);
    return '<tr data-k="' + esc(m.k) + '" class="' + (m.k === c.sel ? "kc-sel" : "") + (ecarte(m) ? " kc-ecarte" : "") + '">'
      + '<td><img src="' + icone(m.t) + '" alt="" class="kc-mini"></td>'
      + '<td><span class="' + ecoClasse(m) + '">' + esc(m.n + " " + m.tl) + "</span>"
      + ' <span class="faible">' + esc(S.meta.ecos[m.e][0]) + (m.o ? " · looté" : "") + "</span></td>"
      + '<td class="n faible">' + qualites(m) + '</td><td class="n">' + nfr(moy, 1) + '</td><td class="n">'
      + hallHtml(m.k, c.qmin) + "</td></tr>";
  }).join("");
  const tableau = '<table class="kc-liste"><thead><tr><th></th><th>Matériau</th><th class="n">Q</th>'
    + '<th class="n" title="Moyenne de ses caractéristiques">moy.</th><th class="n" title="Au hall de guilde, qualité ≥ Q min">hall</th></tr></thead><tbody>'
    + (lignes || '<tr><td colspan="5" class="faible">Aucun matériau.</td></tr>') + "</tbody></table>";
  if (!tout) {
    d.querySelector(".kc-choix-liste").innerHTML = tableau;
    d.querySelector(".kc-choix-stats").innerHTML = statsChoix();
    d.querySelector(".kc-nb").textContent = liste.length + " matériau(x)";
    return;
  }
  const ecos = [[0, "Toutes régions"], ...ORDRE_E.map((e) => [e, S.meta.ecos[e][0]])];
  d.innerHTML = '<div class="kc-choix-tete"><strong>' + esc(S.meta.pieces[c.piece].nom) + "</strong>"
    + '<label>Quantité <input type="number" data-c="quantite" min="1" max="' + c.libre + '" value="' + c.quantite + '"></label>'
    + '<button type="button" data-c="min">Min</button><button type="button" data-c="max">Max</button>'
    + '<span class="kc-nb faible"></span><span class="kc-espace"></span>'
    + (c.j != null ? '<button type="button" class="danger" data-c="retirer">Retirer</button>' : "")
    + '<button type="button" data-c="annuler">Annuler</button>'
    + '<button type="button" class="principal" data-c="ok">' + (c.j != null ? "Remplacer" : "OK") + "</button></div>"
    + '<div class="onglets">' + [5, 4, 3, 2, 1].map((g) => '<button type="button" data-c="grade" data-v="' + g
      + '" aria-pressed="' + (c.grade === g) + '">' + esc(S.meta.grades[g][0]) + "</button>").join("") + "</div>"
    + '<div class="kc-barre">'
    + '<input type="search" data-c="texte" placeholder="Chercher" value="' + esc(c.texte) + '">'
    + selecteur('data-c="eco"', ecos, c.eco)
    + '<label>Q min <input type="number" data-c="qmin" min="0" max="300" step="10" value="' + c.qmin + '"></label>'
    + '<label><input type="checkbox" data-c="fores"' + (c.fores ? " checked" : "") + "> Foragé</label>"
    + '<label><input type="checkbox" data-c="lootes"' + (c.lootes ? " checked" : "") + "> Looté</label>"
    + '<label><input type="checkbox" data-c="ecartes"' + (c.ecartes ? " checked" : "") + "> Écartés</label>"
    + '<label title="Seulement ce que le hall a, en qualité ≥ Q min"><input type="checkbox" data-c="hall"' + (c.hall ? " checked" : "") + "> Au hall</label>"
    + "</div>"
    + '<div class="kc-choix-corps"><div class="kc-choix-liste cadre"></div><div class="kc-choix-stats"></div></div>';
  dessinerChoix(false);
  const sel = d.querySelector("tr.kc-sel");
  if (sel) sel.scrollIntoView({ block: "center" });
}

function statsChoix() {
  const c = S.choix;
  const m = c.sel ? materiau(c.piece, c.sel) : null;
  if (!m) return '<p class="faible">Choisis un matériau pour voir ses caractéristiques.</p>';
  const stats = S.meta.pieces[c.piece].stats;
  const n = auHall(m.k, 0);
  return '<h3 class="' + ecoClasse(m) + '">' + esc(nomComplet(m)) + "</h3>"
    + '<p class="faible">' + (m.o ? "Looté" : "Foragé") + " · " + esc(S.meta.couleurs[m.c][0])
    + (qualites(m) ? " · Q " + qualites(m) : "") + "<br>Au hall : "
    + (n === null ? "fiche du jeu inconnue" : nombre(n) + (c.qmin ? " (dont " + nombre(auHall(m.k, c.qmin)) + " en Q ≥ " + c.qmin + ")" : ""))
    + "</p><table>" + stats.map((s, i) => "<tr><td>" + esc(S.meta.stats[s][0]) + '</td><td class="n">'
      + m.v[i] + "</td></tr>").join("") + "</table>";
}

function surClicChoix(ev) {
  const c = S.choix;
  const ligne = ev.target.closest("[data-k]");
  if (ligne) {
    c.sel = ligne.dataset.k;
    ev.currentTarget.querySelectorAll("tr.kc-sel").forEach((t) => t.classList.remove("kc-sel"));
    ligne.classList.add("kc-sel");
    ev.currentTarget.querySelector(".kc-choix-stats").innerHTML = statsChoix();
    return;
  }
  const b = ev.target.closest("button[data-c]");
  if (!b) return;
  const quoi = b.dataset.c;
  const d = ev.currentTarget;
  if (quoi === "grade") { c.grade = Number(b.dataset.v); S.dernierGrade = c.grade; dessinerChoix(true); }
  else if (quoi === "min" || quoi === "max") {
    c.quantite = quoi === "min" ? 1 : c.libre;
    d.querySelector('[data-c="quantite"]').value = c.quantite;
  } else if (quoi === "annuler") d.close();
  else if (quoi === "retirer") { retirer(c.i, c.j); d.close(); }
  else if (quoi === "ok") valider();
}

function surSaisieChoix(ev) {
  const c = S.choix;
  const t = ev.target;
  const quoi = t.dataset && t.dataset.c;
  if (!quoi) return;
  if (quoi === "quantite") { c.quantite = Math.max(1, Math.min(c.libre, Number(t.value) || 1)); return; }
  if (t.type === "checkbox") c[quoi] = t.checked;
  else if (quoi === "texte") c.texte = t.value;
  else c[quoi] = Number(t.value) || 0;
  if (ev.type === "input" && t.type === "number") return;    // on attend la fin de la saisie
  dessinerChoix(false);
}

function valider() {
  const c = S.choix;
  if (!c.sel) { bandeau("Choisis d'abord un matériau", true); return; }
  const n = Math.max(1, Math.min(c.libre, Number(document.querySelector('#kc-choix [data-c="quantite"]').value) || 1));
  const cases = S.recette.cases[c.i];
  if (c.j == null) cases.push([c.sel, n]); else cases[c.j] = [c.sel, n];
  document.getElementById("kc-choix").close();
  apresChangement();
}

function retirer(i, j) {
  S.recette.cases[i].splice(j, 1);
  apresChangement();
}

// ------------------------------------------------------------ bijouterie

function bijVierge(plan) {
  const p = planDe(plan);
  return {
    plan, nombre: 10, qmin: 0, variete: 2, duree: 30, ecartes: false, tot: false, hall: false,
    conditions: Array.from({ length: 14 }, () => ({ stat: 0, priorite: 1, op: 0, valeur: 0 })),
    filtres: p.pieces.map(() => ({ grade: 0, ecosystem: 0, name: 0, type: 0, color: 0, origin: 0 })),
    maitre: { fores: [], lootes: [], ecos: [] },
    races: Array(10).fill(0),
  };
}
function sauverBij() { garder("kc-bijouterie", S.bij); }

function choixDePiece(piece) {
  const liste = S.meta.materiaux[piece];
  return [[...new Set(liste.map((m) => m.n))].sort(),
          [...new Set(liste.map((m) => m.t))].sort()];
}

function vueBij() {
  const b = S.bij;
  const plan = planDe(b.plan);
  const ops = [[0, ">"], [1, "="], [2, "<"]];
  const stats = [[0, "— aucune —"], ...S.meta.bijou.map((s) => [s, S.meta.stats[s][0]])];
  const conditions = b.conditions.map((c, i) => "<tr><td>"
    + '<input type="number" data-b="priorite" data-i="' + i + '" min="1" max="8" value="' + c.priorite + '" title="1 : la priorité la plus faible"></td><td>'
    + selecteur('data-b="stat" data-i="' + i + '"', stats, c.stat) + "</td><td>"
    + selecteur('data-b="op" data-i="' + i + '"', ops, c.op) + "</td><td>"
    + '<input type="number" data-b="valeur" data-i="' + i + '" min="0" max="10000" step="1" value="' + c.valeur + '"></td></tr>').join("");
  const grades = [1, 2, 3, 4, 5];
  const cases = (cle, valeurs, libelle) => valeurs.map((v) => '<label><input type="checkbox" data-b="maitre" data-m="'
    + cle + '" data-v="' + v + '"' + (b.maitre[cle].includes(v) ? " checked" : "") + "> " + esc(libelle(v)) + "</label>").join("");
  const filtres = plan.pieces.map(([piece, n], i) => {
    const [noms_, types] = choixDePiece(piece);
    const f = b.filtres[i] || {};
    const liste = (cle, entrees) => selecteur('data-b="filtre" data-i="' + i + '" data-f="' + cle + '" title="' + cle + '"', entrees, f[cle] || 0);
    return '<section class="panneau"><h2>' + esc(S.meta.pieces[piece].nom) + " — " + n + " unités par bijou</h2><div class=\"kc-filtres\">"
      + liste("grade", [[0, "Tous grades"], ...grades.map((g) => [g, S.meta.grades[g][0]])])
      + liste("ecosystem", [[0, "Toutes régions"], ...Object.entries(S.meta.ecos).map(([e, x]) => [e, x[0]])])
      + liste("name", [[0, "Tous noms"], ...noms_.map((x, k) => [k + 1, x])])
      + liste("type", [[0, "Tous types"], ...types.map((x, k) => [k + 1, (S.meta.materiaux[piece].find((m) => m.t === x) || {}).tl || x])])
      + liste("color", [[0, "Toutes couleurs"], ...Object.entries(S.meta.couleurs).map(([c, x]) => [c, x[0]])])
      + liste("origin", [[0, "Foragé et looté"], [1, "Foragé"], [2, "Looté"]])
      + "</div></section>";
  }).join("");
  const nombreChamp = (cle, texte, min, max, pas, aide) => '<label title="' + esc(aide) + '">' + texte
    + ' <input type="number" data-b="' + cle + '" min="' + min + '" max="' + max + '" step="' + pas + '" value="' + b[cle] + '"></label>';
  const coche = (cle, texte, aide) => '<label title="' + esc(aide || "") + '"><input type="checkbox" data-b="' + cle + '"'
    + (b[cle] ? " checked" : "") + "> " + texte + "</label>";
  return '<div class="kc-barre">'
    + selecteur('data-b="plan"', plansBijoux().map((p) => [p.id, p.complet]), b.plan)
    + '<button type="button" class="principal" data-kc="chercher">' + (S.bijEnCours ? "Arrêter" : "Chercher") + "</button>"
    + '<button type="button" data-kc="kcj-ouvrir">Ouvrir un .kcj</button>'
    + '<button type="button" data-kc="kcj-enregistrer">Télécharger le .kcj</button>'
    + '<button type="button" data-kc="bij-zero">Tout remettre à zéro</button>'
    + '<span class="faible" id="kc-avance">' + esc(S.bijAvance) + "</span></div>"
    + '<div class="kc-bij"><div>'
    + '<section class="panneau"><h2>Panneau de commande</h2><div class="kc-barre">'
    + nombreChamp("nombre", "Bijoux", 1, 10, 1, "Ryzom compte dix emplacements")
    + nombreChamp("qmin", "Q min", 0, 500, 5, "Qualité minimale des matériaux. 0 : sans limite.")
    + nombreChamp("variete", "Variété", 0, 12, 1, "Matériaux différents par pièce. 0 : sans limite.")
    + nombreChamp("duree", "Durée (s)", 0, 600, 5, "0 : jusqu'à l'arrêt")
    + "</div><div class=\"kc-barre\">"
    + coche("hall", "Seulement le stock du hall", "Seulement les MP que le hall a, en qualité ≥ Q min")
    + coche("ecartes", "Employer les matériaux écartés")
    + coche("tot", "S'arrêter dès que les conditions sont tenues", "Sinon la recherche emploie tout son temps à les dépasser")
    + "</div><details><summary>Race de chaque bijou</summary><div class=\"kc-races\">"
    + b.races.map((r, i) => "<label>" + (i + 1) + " " + selecteur('data-b="race" data-i="' + i + '"', RACES.map((x, k) => [k, x]), r) + "</label>").join("")
    + '</div><p class="faible">Décoratives : elles ne changent aucune valeur, elles sont reportées sur la liste à fabriquer.</p></details></section>'
    + '<section class="panneau"><h2>Filtre pour toutes les pièces</h2><div class="kc-maitre">'
    + "<div><b>Foragé</b>" + cases("fores", grades, (g) => S.meta.grades[g][0]) + "</div>"
    + "<div><b>Looté</b>" + cases("lootes", grades, (g) => S.meta.grades[g][0]) + "</div>"
    + "<div><b>Écosystème</b>" + cases("ecos", [0, 1, 2, 3, 4, 5, 6], (e) => S.meta.ecos[e + 1][0]) + "</div>"
    + '</div><p class="faible">Une colonne sans case cochée ne restreint rien.</p></section>'
    + vueBijResultat()
    + "</div><div>"
    + '<section class="panneau"><h2>Priorités (1 = la plus faible) et conditions</h2>'
    + '<p class="faible">Sur ce que la parure totalise, une fois les dix bijoux portés : un bijou apporte au plus 8 '
    + "sur une caractéristique, donc 80 pour la parure entière.</p>"
    + '<table class="kc-conditions"><thead><tr><th>Priorité</th><th>Caractéristique</th><th></th><th>Total visé</th></tr></thead><tbody>'
    + conditions + "</tbody></table></section>" + filtres + "</div></div>";
}

function vueBijResultat() {
  const r = S.bijRes;
  if (!r) return "";
  if (r.erreur) return '<section class="panneau"><p class="inconnue">' + esc(r.erreur) + "</p></section>";
  const n = r.bijoux.length;
  const totaux = S.meta.bijou.map((s) => "<tr><td class=\"n\">" + (r.totaux[s] != null ? nfr(r.totaux[s], 2) : "")
    + '</td><td class="n">' + (r.totaux[s] != null ? nfr(r.totaux[s] / n, 2) : "") + "</td><td>"
    + esc(S.meta.stats[s][0]) + "</td></tr>").join("");
  // Les bijoux identiques reunis : c'est une liste a fabriquer.
  const groupes = new Map();
  r.bijoux.forEach((b, i) => {
    const cle = JSON.stringify(b.cases.map((c) => [...c].sort()));
    if (!groupes.has(cle)) groupes.set(cle, []);
    groupes.get(cle).push(i);
  });
  const plan = planDe(r.bijoux[0].plan);
  let rang = 0;
  const bijoux = [...groupes.values()].map((positions) => {
    rang++;
    const b = r.bijoux[positions[0]];
    const races = [...new Set(positions.map((p) => r.races[p]).filter((x) => x))];
    return '<div class="kc-bijou"><b>Bijou ' + rang + " — ×" + positions.length + "</b>"
      + (races.length ? ' <span class="faible">(' + races.map((x) => RACES[x]).join(", ") + ")</span>" : "")
      + ' <button type="button" data-kc="bij-simuler" data-i="' + positions[0] + '">Simuler</button>'
      + ' <button type="button" data-kc="bij-kc" data-i="' + positions[0] + '" data-r="' + rang + '">.kc</button>'
      + b.cases.map((c, i) => '<div class="faible">' + esc(S.meta.pieces[plan.pieces[i][0]].nom) + "</div>"
        + c.map(([k, q]) => { const m = materiau(plan.pieces[i][0], k);
          return '<div class="kc-ingr">' + q + '× <span class="' + ecoClasse(m) + '">' + esc(nomComplet(m)) + "</span></div>"; }).join("")).join("")
      + "</div>";
  }).join("");
  // Tout ce qu'il faut pour la parure, face a ce que le hall a.
  const courses = new Map();
  r.bijoux.forEach((b) => b.cases.forEach((c, i) => c.forEach(([k, q]) => {
    const cle = plan.pieces[i][0] + "|" + k;
    courses.set(cle, (courses.get(cle) || 0) + q);
  })));
  const lignes = [...courses].map(([cle, q]) => {
    const [piece, k] = cle.split("|");
    const m = materiau(piece, k);
    const hall = auHall(k, S.bij.qmin);
    return "<tr><td class=\"n\">" + q + '</td><td><span class="' + ecoClasse(m) + '">' + esc(nomComplet(m)) + "</span></td>"
      + '<td class="n">' + hallHtml(k, S.bij.qmin) + "</td><td>" + (hall !== null && hall < q ? '<span class="kc-bas">manque ' + (q - hall) + "</span>" : "") + "</td></tr>";
  }).join("");
  return '<section class="panneau"><h2>Résultat</h2><p class="kc-ligne">' + esc(r.verdict) + "</p>"
    + '<p class="faible">' + (r.manque.length ? "Non tenu : " + r.manque.map(([s, e]) => esc(s) + " (écart " + nfr(e, 2) + ")").join(" · ")
      : r.distincts + " bijoux différents sur " + n + " · " + r.generations + " générations") + "</p>"
    + '<div class="kc-res"><table class="kc-stats"><thead><tr><th class="n">Total</th><th class="n">Par bijou</th><th></th></tr></thead><tbody>'
    + totaux + "</tbody></table><div>" + bijoux + "</div></div>"
    + '<h2>À récolter</h2><table class="kc-stats"><thead><tr><th class="n">Il faut</th><th>MP</th><th class="n">Hall</th><th></th></tr></thead><tbody>'
    + lignes + "</tbody></table></section>";
}

async function chercher() {
  if (S.bijEnCours) { travail.postMessage({ op: "arreter" }); S.bijAvance = "Arrêt demandé…"; majAvance(); return; }
  const b = S.bij;
  const demande = Object.assign({}, b, { liste_ecartes: [...S.ecartes] });
  if (b.hall) {
    const plan = planDe(b.plan);
    demande.permis = [...new Set(plan.pieces.flatMap(([p]) => S.meta.materiaux[p]
      .filter((m) => auHall(m.k, b.qmin) > 0).map((m) => m.k)))];
  }
  S.bijEnCours = true;
  S.bijRes = null;
  S.bijAvance = "Recherche…";
  dessiner();
  surAvance = (a) => { S.bijAvance = "génération " + a.generation + " — " + a.etat; majAvance(); };
  try {
    S.bijRes = await appelerJson("bijouter", demande);
    S.bijAvance = S.bijRes.erreur ? "" : "Terminé";
  } catch (souci) {
    S.bijRes = { erreur: "La recherche a échoué : " + souci.message };
    S.bijAvance = "";
  }
  S.bijEnCours = false;
  surAvance = null;
  if (S.sous === "bij") dessiner();
}
function majAvance() { const z = document.getElementById("kc-avance"); if (z) z.textContent = S.bijAvance; }

// ------------------------------------------------------------ base de materiaux

function vueBase() {
  const f = S.base;
  const pieces = Object.entries(S.meta.pieces).map(([k, p]) => [k, p.nom]).sort((a, b) => a[1].localeCompare(b[1]));
  const stats = S.meta.pieces[f.piece].stats;
  const texte = f.texte.trim().toLowerCase();
  const liste = S.meta.materiaux[f.piece].filter((m) => (!f.grade || m.g === f.grade) && (!f.eco || m.e === f.eco)
    && (!f.origine || m.o === f.origine - 1) && (f.ecartes || !ecarte(m))
    && (!texte || nomComplet(m).toLowerCase().includes(texte) || m.t.toLowerCase().includes(texte))
    && (!f.hall || auHall(m.k, 0) > 0))
    .sort((a, b) => b.g - a.g || ORDRE_E.indexOf(a.e) - ORDRE_E.indexOf(b.e) || a.n.localeCompare(b.n));
  const lignes = liste.map((m) => '<tr class="' + (ecarte(m) ? "kc-ecarte" : "") + '">'
    + '<td><input type="checkbox" data-kc="ecarter" data-k="' + esc(m.k) + '"' + (ecarte(m) ? " checked" : "")
    + (m.i ? " disabled title=\"Écarté par la base elle-même\"" : "") + "></td>"
    + '<td><img src="' + icone(m.t) + '" alt="" class="kc-mini"> <span class="' + ecoClasse(m) + '">' + esc(nomComplet(m)) + "</span>"
    + (m.o ? ' <span class="faible">looté</span>' : "") + "</td>"
    + '<td class="n faible">' + qualites(m) + '</td><td class="n">' + hallHtml(m.k, 0) + "</td>"
    + m.v.map((v) => '<td class="n">' + v + "</td>").join("") + "</tr>").join("");
  return '<div class="kc-barre">'
    + selecteur('data-kb="piece"', pieces, f.piece)
    + selecteur('data-kb="grade"', [[0, "Tous grades"], ...[5, 4, 3, 2, 1].map((g) => [g, S.meta.grades[g][0]])], f.grade)
    + selecteur('data-kb="eco"', [[0, "Toutes régions"], ...ORDRE_E.map((e) => [e, S.meta.ecos[e][0]])], f.eco)
    + selecteur('data-kb="origine"', [[0, "Foragé et looté"], [1, "Foragé"], [2, "Looté"]], f.origine)
    + '<input type="search" data-kb="texte" placeholder="Chercher" value="' + esc(f.texte) + '">'
    + '<label><input type="checkbox" data-kb="hall"' + (f.hall ? " checked" : "") + "> Au hall</label>"
    + '<label><input type="checkbox" data-kb="ecartes"' + (f.ecartes ? " checked" : "") + "> Écartés</label>"
    + '<span class="faible">' + liste.length + " matériau(x)</span></div>"
    + '<p class="faible">Cocher une ligne écarte le matériau du sélecteur et de la Bijouterie, dans ce navigateur seulement.</p>'
    + '<div class="cadre collant"><table class="kc-base"><thead><tr><th title="Écarté"></th><th>Matériau</th><th class="n">Q</th><th class="n">Hall</th>'
    + stats.map((s) => '<th class="n" title="' + esc(S.meta.stats[s][0]) + '">' + esc(S.meta.stats[s][1]) + "</th>").join("")
    + "</tr></thead><tbody>" + lignes + "</tbody></table></div>";
}

// ------------------------------------------------------------ formules

async function chargerFormules(plan, option) {
  plan = plan == null ? S.recette.plan : plan;
  option = option == null ? (plan === S.recette.plan ? S.recette.option : planDe(plan).options[0]) : option;
  const f = await appelerJson("formules", plan, option);
  S.form = Object.assign(f, { plan, option, message: "" });
  if (S.sous === "form") dessiner();
}

function vueForm() {
  const f = S.form;
  if (!f) return '<p class="faible">Lecture des formules…</p>';
  const plan = planDe(f.plan);
  const groupes = S.meta.paliers.map(([t, nom]) => '<optgroup label="' + esc(nom) + '">'
    + S.meta.plans.filter((p) => p.palier === t).map((p) => '<option value="' + p.id + '"'
      + (p.id === f.plan ? " selected" : "") + ">" + esc(p.intitule) + "</option>").join("") + "</optgroup>").join("");
  const retouchee = Object.prototype.hasOwnProperty.call(lire("kc-retouches", {}), f.fichier);
  return '<div class="kc-barre"><select data-kf="plan">' + groupes + "</select>"
    + (plan.options.length > 1 ? '<select data-kf="option">' + options(plan, f.option) + "</select>" : "")
    + '<span class="faible">' + esc(f.fichier) + (retouchee ? " — retouché dans ce navigateur" : "") + "</span></div>"
    + "<p class=\"faible\">Une ligne par caractéristique : <code>Caractéristique = formule</code>. Constantes "
    + "<code>&lt;precraft&gt;</code>, <code>&lt;quality&gt;</code>, <code>&lt;rite&gt;</code>. Une retouche ne vaut "
    + "que pour ce navigateur.</p>"
    + '<textarea class="kc-formules" data-kf="texte" spellcheck="false">' + esc(f.texte) + "</textarea>"
    + '<div class="kc-barre"><button type="button" class="principal" data-kc="form-appliquer">Appliquer</button>'
    + (retouchee ? '<button type="button" data-kc="form-retablir">Rétablir l\'original</button>' : "")
    + '<span class="faible">' + esc(f.message || "") + "</span></div>"
    + (f.problemes.length ? '<ul class="inconnue">' + f.problemes.map((p) => "<li>" + esc(p) + "</li>").join("") + "</ul>" : "");
}

async function appliquerFormules() {
  const f = S.form;
  const texte = document.querySelector('[data-kf="texte"]').value;
  const r = await appelerJson("retoucher", f.fichier, texte);
  if (r.erreur) { f.message = r.erreur; dessiner(); return; }
  const retouches = lire("kc-retouches", {});
  retouches[f.fichier] = texte;
  garder("kc-retouches", retouches);
  await chargerFormules(f.plan, f.option);
  S.form.message = r.problemes.length ? r.problemes.length + " ligne(s) ignorée(s)" : "Appliqué.";
  dessiner();
  recalculer();
}

async function retablirFormules() {
  const f = S.form;
  await appeler("retablir", f.fichier);
  const retouches = lire("kc-retouches", {});
  delete retouches[f.fichier];
  garder("kc-retouches", retouches);
  await chargerFormules(f.plan, f.option);
  S.form.message = "Original rétabli.";
  dessiner();
  recalculer();
}

// ------------------------------------------------------------ audit

function vueAudit() {
  const a = S.audit;
  let h = '<p>Les bases de matériaux et les formules se corrigent à la main : l\'audit cherche les valeurs '
    + "aberrantes et les formules manquantes qui fausseraient les calculs.</p>"
    + '<p><button type="button" class="principal" data-kc="auditer">' + (S.auditEnCours ? "Audit en cours…" : "Lancer l'audit") + "</button></p>";
  if (!a) return h;
  h += '<p class="kc-ligne">' + esc(a.resume) + '</p><p class="faible">Examiné : '
    + Object.entries(a.examine).map(([k, v]) => v + " " + esc(k)).join(", ") + "</p>";
  for (const niveau of [2, 1, 0]) {
    const liste = a.constats.filter((c) => c[0] === niveau);
    if (!liste.length) continue;
    h += '<section class="panneau"><h2>' + esc(liste[0][1]) + "s</h2><ul>"
      + liste.map((c) => "<li><b>" + esc(c[3]) + "</b> — " + esc(c[4]) + ' <span class="faible">(' + esc(c[2]) + ")</span></li>").join("")
      + "</ul></section>";
  }
  return h;
}

// ------------------------------------------------------------ evenements

async function surClic(ev) {
  const b = ev.target.closest("[data-kc]");
  if (!b || b.tagName === "SELECT" || b.tagName === "INPUT" || b.tagName === "TEXTAREA") return;
  const quoi = b.dataset.kc;
  if (quoi === "sous") { S.sous = b.dataset.v; garder("kc-sous", S.sous); dessiner(); }
  else if (quoi === "ajouter") ouvrirChoix(Number(b.dataset.i), null);
  else if (quoi === "case") ouvrirChoix(Number(b.dataset.i), Number(b.dataset.j));
  else if (quoi === "vider") { nouvelle(planDe(S.recette.plan)); dessiner(); recalculer(); }
  else if (quoi === "detail") { S.detail = !S.detail; document.getElementById("kc-apercu").innerHTML = vueApercu(); }
  else if (quoi === "ouvrir") {
    const f = await choisirFichier(".kc");
    const r = await appelerJson("lire_kc", f.texte);
    if (r.erreur) { bandeau(f.nom + " : " + r.erreur, true); return; }
    S.recette = r.recette;
    S.palier = planDe(r.recette.plan).palier;
    sauverRecette();
    dessiner();
    recalculer();
    bandeau(f.nom + " ouvert");
  } else if (quoi === "enregistrer") {
    const plan = planDe(S.recette.plan);
    telecharger(plan.intitule + ".kc", await appeler("ecrire_kc", S.recette));
  } else if (quoi === "chercher") chercher();
  else if (quoi === "bij-zero") { S.bij = bijVierge(S.bij.plan); S.bijRes = null; sauverBij(); dessiner(); }
  else if (quoi === "kcj-enregistrer") telecharger("parure.kcj", await appeler("projet_kcj", S.bij));
  else if (quoi === "kcj-ouvrir") {
    const f = await choisirFichier(".kcj");
    const r = await appelerJson("projet_vers_page", f.texte);
    if (r.erreur) { bandeau(f.nom + " : " + r.erreur, true); return; }
    const p = r.projet;
    const vierge = bijVierge(planDe(p.plan) ? p.plan : S.bij.plan);
    S.bij = Object.assign(vierge, {
      plan: vierge.plan, qmin: p.qmin, ecartes: p.ecartes, maitre: p.maitre,
      conditions: vierge.conditions.map((c, i) => p.conditions[i] ? Object.assign({}, p.conditions[i],
        { priorite: Math.max(1, p.conditions[i].priorite) }) : c),
      filtres: vierge.filtres.map((x, i) => p.filtres[i] || x),
      races: vierge.races.map((x, i) => p.races[i] || 0),
    });
    S.bijRes = null;
    sauverBij();
    dessiner();
    bandeau(f.nom + " ouvert");
  } else if (quoi === "bij-simuler") {
    S.recette = Object.assign({}, S.bijRes.bijoux[Number(b.dataset.i)], { commentaire: "Créée par la Bijouterie" });
    S.palier = planDe(S.recette.plan).palier;
    S.sous = "simu";
    garder("kc-sous", S.sous);
    sauverRecette();
    dessiner();
    recalculer();
  } else if (quoi === "bij-kc") telecharger("bijou " + b.dataset.r + ".kc", S.bijRes.kc[Number(b.dataset.i)]);
  else if (quoi === "form-appliquer") appliquerFormules();
  else if (quoi === "form-retablir") retablirFormules();
  else if (quoi === "auditer" && !S.auditEnCours) {
    S.auditEnCours = true;
    dessiner();
    try { S.audit = await appelerJson("auditer"); } catch (souci) { bandeau(souci.message, true); }
    S.auditEnCours = false;
    if (S.sous === "audit") dessiner();
  }
}

function surChangement(ev) {
  const t = ev.target;
  const d = t.dataset || {};
  const v = t.type === "checkbox" ? t.checked : t.value;
  if (d.kc === "palier") {
    S.palier = v;
    nouvelle(S.meta.plans.find((p) => p.palier === v));
    dessiner();
    recalculer();
  } else if (d.kc === "plan") { nouvelle(planDe(v)); dessiner(); recalculer(); }
  else if (d.kc === "option") { S.recette.option = Number(v); sauverRecette(); recalculer(); }
  else if (d.kc === "pref") {
    S.prefs[d.v] = t.type === "checkbox" ? v : Math.max(Number(t.min), Math.min(Number(t.max), Number(v) || 0));
    garder("kc-prefs", S.prefs);
    recalculer();
  } else if (d.kc === "colonne") {
    S.prefs[d.v] = v;
    garder("kc-prefs", S.prefs);
    document.getElementById("kc-apercu").innerHTML = vueApercu();
  } else if (d.kc === "commentaire") { S.recette.commentaire = v; sauverRecette(); }
  else if (d.kc === "ecarter") {
    const cle = S.base.piece + "|" + d.k;
    if (v) S.ecartes.add(cle); else S.ecartes.delete(cle);
    garder("kc-ecartes", [...S.ecartes]);
    t.closest("tr").classList.toggle("kc-ecarte", v);
  } else if (d.kb) {
    S.base[d.kb] = t.type === "checkbox" ? v : d.kb === "piece" || d.kb === "texte" ? v : Number(v);
    if (ev.type === "input" && d.kb !== "texte") return;
    const garde = document.activeElement === t && d.kb === "texte";
    dessiner();
    if (garde) { const c = racine.querySelector('[data-kb="texte"]'); c.focus(); c.setSelectionRange(c.value.length, c.value.length); }
  } else if (d.kf === "plan") chargerFormules(Number(v), null);
  else if (d.kf === "option") chargerFormules(S.form.plan, Number(v));
  else if (d.b) surBij(ev, t, d, v);
}

function surBij(ev, t, d, v) {
  const b = S.bij;
  const n = Number(v);
  if (d.b === "plan") {
    // Les memes deux pieces d'un palier a l'autre : on garde le formulaire.
    b.plan = n;
    S.bijRes = null;
    sauverBij();
    dessiner();
    return;
  }
  if (["priorite", "stat", "op", "valeur"].includes(d.b)) b.conditions[Number(d.i)][d.b] = n;
  else if (d.b === "filtre") b.filtres[Number(d.i)][d.f] = n;
  else if (d.b === "race") b.races[Number(d.i)] = n;
  else if (d.b === "maitre") {
    const liste = b.maitre[d.m].filter((x) => x !== Number(d.v));
    if (v) liste.push(Number(d.v));
    b.maitre[d.m] = liste.sort((x, y) => x - y);
  } else if (t.type === "checkbox") b[d.b] = v;
  else b[d.b] = n;
  sauverBij();
}

function surMenu(ev) {
  const b = ev.target.closest('[data-kc="case"]');
  if (!b) return;
  ev.preventDefault();
  retirer(Number(b.dataset.i), Number(b.dataset.j));
}

// ------------------------------------------------------------ entree

window.KC = {
  // Appele par index.html quand on ouvre l'onglet ; `vue` est vide.
  afficher(vue) {
    racine = document.createElement("div");
    racine.className = "kc";
    racine.addEventListener("click", surClic);
    racine.addEventListener("change", surChangement);
    racine.addEventListener("input", (ev) => { if (ev.target.dataset.kb === "texte" || ev.target.dataset.kc === "commentaire") surChangement(ev); });
    racine.addEventListener("contextmenu", surMenu);
    vue.appendChild(racine);
    lancer();
    dessiner();
  },
};

const style = document.createElement("style");
style.textContent = `
.kc h2 { font-size: 1.05rem; color: var(--or); margin: 4px 0 8px; }
.kc-sous { align-items: baseline; }
.kc-resume { margin-left: auto; font-size: .8rem; }
@media (min-width: 901px) { .kc-sous { padding-right: 52px; } }
.kc-attente { color: var(--clair); }
.kc-barre { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin: 0 0 10px; }
.kc-barre label { display: flex; gap: 6px; align-items: center; color: var(--faible); }
.kc select { background: var(--surface); color: var(--texte); border: 1px solid var(--trait);
             border-radius: 7px; padding: 6px 8px; font: inherit; max-width: 100%; }
.kc-simu { display: grid; grid-template-columns: minmax(0, 5fr) minmax(0, 6fr); gap: 24px; }
@media (max-width: 1100px) { .kc-simu { grid-template-columns: 1fr; } }
.kc-ligne { color: var(--texte); }
.kc-stats { width: auto; min-width: 100%; }
.kc-stats td, .kc-stats th { padding: 2px 10px; border-bottom: none; }
.kc-stats th select { padding: 3px 6px; font-size: .85rem; }
.kc-stats td:first-child, .kc-detail td:first-child, .kc-base td:first-child, .kc-liste td:first-child { min-width: 0; }
.kc-bas td, span.kc-bas { color: #e2756a; }
.kc-haut td { color: #6fcf8a; }
.kc-com { display: flex; flex-direction: column; gap: 4px; color: var(--faible); margin-top: 10px; }
.kc textarea { background: var(--surface); color: var(--texte); border: 1px solid var(--trait);
               border-radius: 7px; padding: 6px 8px; font: inherit; width: 100%; }
.kc-detail td, .kc-detail th { padding: 2px 6px; font-size: .85rem; }
.kc-piece { margin-bottom: 12px; }
.kc-titre { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }
.kc-titre span { flex: 1; border-top: 1px solid var(--trait); }
.kc-cases { display: flex; gap: 6px; flex-wrap: wrap; }
.kc-case { position: relative; width: 52px; height: 52px; padding: 0; border: 2px solid #909090;
           background: #353535; border-radius: 4px; overflow: hidden; }
.kc-case img { position: absolute; left: 4px; top: 4px; width: 40px; height: 40px; }
.kc-case span { position: absolute; font-size: 8px; font-weight: 700; line-height: 1; color: #d4e092;
                text-shadow: 0 0 2px #000, 0 0 2px #000; }
.kc-c-nom { left: 2px; top: 2px; max-width: 46px; overflow: hidden; white-space: nowrap; }
.kc-c-q { left: 0; right: 0; top: 20px; text-align: center; font-size: 9px; }
.kc-c-x { left: 2px; bottom: 2px; }
.kc-c-g { right: 0; bottom: 0; padding: 6px 2px 1px 8px; color: #fff !important; }
.kc-coul-red { background: linear-gradient(to bottom right, transparent 50%, #c60000 50%); }
.kc-coul-blue { background: linear-gradient(to bottom right, transparent 50%, #2a2c90 50%); }
.kc-coul-green { background: linear-gradient(to bottom right, transparent 50%, #1f7a1f 50%); }
.kc-coul-turquoise { background: linear-gradient(to bottom right, transparent 50%, #1f9a9a 50%); }
.kc-coul-purple { background: linear-gradient(to bottom right, transparent 50%, #7a2a9a 50%); }
.kc-coul-beige { background: linear-gradient(to bottom right, transparent 50%, #c8a870 50%); }
.kc-coul-white { background: linear-gradient(to bottom right, transparent 50%, #e8e8e8 50%); }
.kc-coul-black { background: linear-gradient(to bottom right, transparent 50%, #101010 50%); }
.kc-vide { font-size: 1.6rem; color: var(--faible); border-style: dashed; border-color: var(--trait); }
.kc-aide { font-size: .8rem; }
.kc-mini { width: 22px; height: 22px; vertical-align: middle; border-radius: 3px; }
.kc-hall { color: var(--oui); }
tr.kc-ecarte td { opacity: .5; }
#kc-choix { max-width: min(1100px, calc(100vw - 16px)); width: 100%; }
.kc-choix-tete { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 10px; }
.kc-choix-tete label { display: flex; gap: 6px; align-items: center; color: var(--faible); }
.kc-espace { flex: 1; }
.kc-choix-corps { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: 16px; }
@media (max-width: 800px) { .kc-choix-corps { grid-template-columns: 1fr; } }
.kc-choix-liste { max-height: 55vh; overflow-y: auto; }
.kc-liste tr[data-k] { cursor: pointer; }
.kc-liste tr.kc-sel td { background: #1d3a33; }
.kc-liste td, .kc-liste th { padding: 3px 6px; }
.kc-choix-stats h3 { font-size: 1rem; margin: 0 0 6px; }
.kc-choix-stats td { padding: 2px 8px; border-bottom: none; }
.kc-bij { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; }
@media (max-width: 1100px) { .kc-bij { grid-template-columns: 1fr; } }
.kc-maitre { display: flex; gap: 24px; flex-wrap: wrap; }
.kc-maitre > div { display: flex; flex-direction: column; gap: 2px; }
.kc-maitre label, .kc-races label { color: var(--faible); }
.kc-races { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 6px; margin: 8px 0; }
.kc-conditions td { padding: 2px 4px; border-bottom: none; }
.kc-conditions select { width: 100%; }
.kc-conditions input[type="number"] { width: 5.5em; }
.kc-filtres { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; }
@media (max-width: 600px) { .kc-filtres { grid-template-columns: 1fr; } }
.kc-res { display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: 16px; margin-bottom: 10px;
          align-items: start; }
@media (max-width: 700px) { .kc-res { grid-template-columns: 1fr; } }
.kc-bijou { margin-bottom: 10px; }
.kc-bijou button { padding: 2px 8px; font-size: .85rem; }
.kc-ingr { margin-left: 12px; }
.kc-base td, .kc-base th { padding: 3px 6px; }
.kc-formules { min-height: 360px; font-family: ui-monospace, monospace !important; font-size: .9rem !important; }
`;
document.head.appendChild(style);
})();
