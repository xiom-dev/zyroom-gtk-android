// Le Web Worker de KipeeCraft : Pyodide et le code Python de kipeecraft-py.
//
// Tout tourne ici, hors de la page : le chargement de Pyodide (une dizaine
// de Mo la premiere fois, ensuite en cache) et la recherche de la
// Bijouterie, qui peut durer des minutes, ne figent jamais l'ecran.
//
// Protocole : la page envoie {id, op, args}, on repond {id, ok, valeur}
// ou {id, ok: false, erreur}. La Bijouterie envoie en plus des messages
// {avance: ...} pendant qu'elle cherche.

const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/";
importScripts(PYODIDE + "pyodide.js");

let pret = null;
let kc = null;

async function demarrer(retouches) {
  const py = await loadPyodide({ indexURL: PYODIDE });
  // "no-cache" : le navigateur redemande, le serveur repond 304 tant que
  // le zip n'a pas change. Un nouveau depot ne sert donc jamais l'ancien.
  const r = await fetch("kipeecraft.zip", { cache: "no-cache" });
  if (!r.ok) throw new Error("kipeecraft.zip " + r.status);
  py.FS.mkdirTree("/kc");
  py.unpackArchive(await r.arrayBuffer(), "zip", { extractDir: "/kc" });
  py.runPython("import sys; sys.path.insert(0, '/kc')");
  kc = py.pyimport("kc_web");
  return kc.demarrer(JSON.stringify(retouches || {}));
}

const OPERATIONS = {
  calculer: (d) => kc.calculer(JSON.stringify(d)),
  lire_kc: (texte) => kc.lire_kc(texte),
  ecrire_kc: (d) => kc.ecrire_kc(JSON.stringify(d)),
  formules: (plan, option) => kc.formules(plan, option),
  retoucher: (nom, texte) => kc.retoucher(nom, texte),
  retablir: (nom) => kc.retablir(nom),
  auditer: () => kc.auditer(),
  projet_vers_page: (texte) => kc.projet_vers_page(texte),
  projet_kcj: (d) => kc.projet_kcj(JSON.stringify(d)),
  projet_kce: (d) => kc.projet_kce(JSON.stringify(d)),
  kce_vers_page: (texte) => kc.kce_vers_page(texte),
  assistant: (d) => kc.assistant(JSON.stringify(d)),
  evoluer: (d) => kc.evoluer(JSON.stringify(d),
    (avance) => postMessage({ avance: JSON.parse(avance) })),
  bijouter: (d) => kc.bijouter(JSON.stringify(d),
    (avance) => postMessage({ avance: JSON.parse(avance) })),
};

onmessage = async (ev) => {
  const { id, op, args } = ev.data;
  // L'arret passe pendant que la recherche tourne : il ne doit pas
  // attendre son tour derriere elle.
  if (op === "arreter") { if (kc) kc.arreter(); return; }
  try {
    let valeur;
    if (op === "demarrer") {
      pret = pret || demarrer(...args);
      valeur = await pret;
    } else {
      await pret;
      valeur = await OPERATIONS[op](...args);
    }
    postMessage({ id, ok: true, valeur });
  } catch (souci) {
    postMessage({ id, ok: false, erreur: String(souci.message || souci) });
  }
};
