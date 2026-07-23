# PRD: Todo List Application

## Objectif
Application web de todo list moderne, elegante et reactive, entierement cote client (HTML/CSS/JS natif).

## Fonctionnalites
1. Ajouter une tache (champ texte + bouton "Ajouter")
2. Marquer une tache comme terminee (checkbox)
3. Supprimer une tache (bouton poubelle)
4. Persistance locale (localStorage)
5. Filtres : Toutes / Actives / Terminees
6. Compteur de taches restantes
7. Effacer les taches terminees

## Design (UI/UX) - OBLIGATOIRE
- Dark mode par defaut avec fond sombre (#0a0a0f ou similaire)
- Glassmorphism (fond semi-transparent avec `backdrop-filter: blur()`)
- Typographie : Inter (Google Fonts)
- Icônes : Font Awesome 6
- Animations douces au hover, ajout/suppression de tache
- Ombres profondes (`shadow-2xl`, `shadow-lg`)
- Boutons avec effets de hover (scale, glow)
- Responsive (mobile-first)
- Utilisation de Tailwind CSS via CDN pour le style

## Stack
- HTML5
- Tailwind CSS (CDN)
- Google Fonts Inter (CDN)
- Font Awesome 6 (CDN)
- Vanilla JS (ES6+)
- localStorage pour la persistance
