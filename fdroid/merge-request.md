# Le texte de la merge request

Ce qu'il faut coller sur GitLab pour proposer la recette, gardé ici pour la
même raison qu'elle : ne pas le réécrire de mémoire, et pouvoir le corriger
sans repartir de zéro. Le tout est en anglais — `fdroiddata` l'est.

Leur formulaire ajoutera son propre gabarit et ses cases à cocher : les
remplir, et mettre ce qui suit dans la description.

---

## Titre

    New app: V-RyLune (net.ryzom.zyroom)

## Description

```markdown
Adds a build recipe for **V-RyLune**, an offline reader for Ryzom character
inventories and guild chests, through the game's official web API.

Closes fdroid/rfp#4244

One thing to flag: the RFP description says GPL-3.0-or-later. That is a
mistake in the request, not in the app — it is **AGPL-3.0-or-later**,
inherited from Misugi's zyRoom, the Delphi original it is a port of. The
recipe carries the right one, and I will note the correction on the RFP.

### Notes for the reviewer

Four things in the recipe would look odd without a word of explanation.

- **`subdir: zyroom-android/app`** — the repository holds two applications
  built from one specification: a GTK desktop one and this Android one. Gradle
  finds the root project on its own, one level up, at
  `zyroom-android/settings.gradle.kts`.

- **`gradle: [fdroid]`** — three flavors share the code. This one is the
  players' build stripped of what F-Droid's inclusion policy rules out: it
  does not check for its own updates, and it does not bundle the game's
  `string_client.pack`. That file belongs to the game's publisher; the app
  imports it from the player's own Ryzom installation instead.

- **`UpdateCheckMode: HTTP`, not `Tags`** — version numbers are not written in
  `build.gradle.kts`. They live in a `version.properties` file that the
  release script increments, and the version scanner cannot read them there.
  The published `version.json` carries them verbatim, which is what
  `UpdateCheckData` reads. The pattern is anchored on the `net.ryzom.zyroom`
  key so it does not match the maintainer's build, which follows it in the
  same file.

- **No `scandelete`** — an earlier draft carried two entries, for the game's
  data and image directories, on the assumption that the scanner would object
  to them. It does not, and an entry the scan never needed counts as an error
  ("Unused scandelete path"). The `fdroid` flavor compiles neither directory,
  so the APK is clean without them.

### Checked locally

`fdroid readmeta` and `fdroid lint net.ryzom.zyroom` both pass without a
remark, on fdroidserver 2.4.5.

One caveat, in case it comes up in review: `fdroid rewritemeta` wants
`UpdateCheckData` on a single line, while CI asked for it wrapped onto the
next line, indented by two spaces. I have kept the wrapped form. Say the word
if the canonical form has moved again and I will match it.

Screenshots and per-version changelogs are in the app repository, under
`fastlane/metadata/android/`, in English and French.
```

---

## Le commentaire à poster sur la RFP #4244

Pour que les deux se rejoignent, et pour corriger la licence annoncée.

```markdown
I have opened a merge request on fdroiddata with a build recipe for this app:
<lien de la MR>

One correction to the description above: the licence is **AGPL-3.0-or-later**,
not GPL-3.0-or-later. The app is a port of Misugi's zyRoom, which is AGPL, and
it keeps that licence — Section 13 is the difference, and it is not one that
can be dropped in a derivative work.

Since the bot's pass on 10 August, the two things it would have asked for are
in place: screenshots under `fastlane/metadata/android/*/images/`, and a
release tag for every published version.
```
