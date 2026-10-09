// Le Web Worker de ZyRoom web : Pyodide et le code Python de ZyRoom-GTK.
//
// Meme principe que celui de KipeeCraft (mp/kc/travail.js) : la page envoie
// {id, op, args}, on repond {id, ok, valeur} ou {id, ok: false, erreur}.
// Le meme Pyodide, a la meme adresse : un joueur qui a ouvert KipeeCraft
// l'a deja dans son cache.

const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/";
importScripts(PYODIDE + "pyodide.js");

let pret = null;
let zr = null;

async function demarrer() {
  const py = await loadPyodide({ indexURL: PYODIDE });
  // "no-cache" : 304 tant que le zip n'a pas change, jamais l'ancien code.
  const r = await fetch("zyroom.zip", { cache: "no-cache" });
  if (!r.ok) throw new Error("zyroom.zip " + r.status);
  py.FS.mkdirTree("/zr");
  py.unpackArchive(await r.arrayBuffer(), "zip", { extractDir: "/zr" });
  py.runPython("import sys; sys.path.insert(0, '/zr')");
  zr = py.pyimport("zr_web");
  return zr.demarrer();
}

const OPERATIONS = {
  entite: (xml, sorte) => zr.entite(xml, sorte),
  saison: (xml) => zr.saison(xml),
  releve: (xml, sorte, avant) => zr.releve(xml, sorte, avant),
  charger_journal: (cle, texte, depuis) => zr.charger_journal(cle, texte, depuis),
  vue_journal: (cle, cherche, mode) => zr.vue_journal(cle, cherche, mode),
  registre: (gid, texte) => zr.registre(gid, texte),
  copier_journal: (cle, cherche, mode) => zr.copier_journal(cle, cherche, mode),
};

onmessage = async (ev) => {
  const { id, op, args } = ev.data;
  try {
    let valeur;
    if (op === "demarrer") {
      pret = pret || demarrer();
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
