"""Le fuseau que les essais de dates supposent.

**Pourquoi c'est necessaire.** Le journal affiche ses dates dans le fuseau du
joueur -- `time.localtime`, et c'est bien ce qu'on veut : quelqu'un qui releve
sa guilde a une heure du matin doit lire la date qu'il a sur sa montre. Mais
un essai qui ecrit « 2026-08-22 » en dur ne dit alors la verite que dans les
fuseaux a l'est de Greenwich.

Le relevé du 22 aout 2026 tombe a 00h09 a Paris, donc la veille a 22h09 en
temps universel. Sur la machine du mainteneur, l'essai passait ; sur celle de
GitHub, qui vit en UTC, il tombait -- et disait « 2026-08-21 » pour la meme
seconde. C'est la premiere chose qu'ait trouvee le passage des essais en
integration continue.

On pose donc le fuseau que ces essais-la supposent, plutot que de fixer celui
de la machine entiere : un essai doit dire la meme chose partout, et c'est a
lui de nommer ce qu'il suppose.
"""
import os
import time

#: Celui de la guilde, et des dates ecrites en dur dans ces essais.
FUSEAU = "Europe/Paris"


def poser_le_fuseau() -> None:
    """A appeler depuis `setUpModule`."""
    os.environ["TZ"] = FUSEAU
    if hasattr(time, "tzset"):    # absent sous Windows, ou rien de tout ceci
        time.tzset()              # ne tourne
