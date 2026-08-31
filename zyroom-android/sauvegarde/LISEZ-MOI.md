# Sauvegarde chiffrée

`cles-signature.tar.gz.gpg` est une archive personnelle, chiffrée en AES-256
par phrase de passe. Elle ne s'ouvre qu'avec elle : rien ici ne permet de la
retrouver, et personne d'autre ne la détient.

Pour l'ouvrir :

    gpg --decrypt cles-signature.tar.gz.gpg | tar -xz

Elle contient un `LISEZ-MOI.md` qui explique où remettre chacun des fichiers.

Le dépôt sert ici de second exemplaire, rien de plus — l'original vit hors
dépôt, sur la machine de développement. Ne jamais y déposer l'équivalent en
clair : le contenu d'un commit ne s'efface pas, il se déplace seulement dans
l'historique.
