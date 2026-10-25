<?php
// La page, derriere la porte de xiom.be (index/porte.php) : sans le
// laissez-passer de l'entree, retour a l'accueil, qui ramene ici une fois entre.
declare(strict_types=1);
require __DIR__ . '/../index/porte.php';
porte_page(__DIR__ . '/index.html');
