<?php
// La porte de xiom.be/Lune-eternelle/ : recopiee telle quelle par
// outils/site-domaine.py en Lune-eternelle/index.php.
//
// Plus de mot de passe propre : la page passe par la porte de tout xiom.be
// (index/porte.php). Sans le laissez-passer de l'entree, retour a l'accueil,
// qui ramene ici une fois entre.
//
// La page elle-meme s'appelle page.html et le .htaccess du dossier en refuse
// la lecture directe : elle ne sort que par ici. readfile() lit le fichier sur
// le disque, sans repasser par Apache, donc sans buter sur ce refus.
declare(strict_types=1);
require __DIR__ . '/../index/porte.php';
porte_page(__DIR__ . '/page.html');
