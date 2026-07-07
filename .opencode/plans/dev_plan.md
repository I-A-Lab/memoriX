# Dev Plan - Todo List

## Architecture fichiers
```
packages/todo-app/
  index.html     # Structure HTML + Tailwind + Font Awesome + Inter
  style.css      # Surcouche CSS (animations, glassmorphism, custom)
  app.js         # Logique JS (CRUD, filtres, localStorage)
```

## Contrats d'interface

### HTML (`index.html`)
- `<div id="app">` : conteneur principal
  - `<div id="todo-card">` : carte glassmorphique centree
    - `<h1>` : titre "memoriX"
    - `<div id="todo-form">` : input + bouton ajouter
    - `<div id="todo-filters">` : 3 boutons filtres (Toutes/Actives/Terminees)
    - `<ul id="todo-list">` : liste des taches
    - `<div id="todo-footer">` : compteur + bouton "Effacer terminees"

### CSS (`style.css`)
- Classes personnalisees :
  - `.glass-card` : effet glassmorphism
  - `.todo-item` : style d'une tache
  - `.todo-item.completed` : tache terminee (barre + opacite reduite)
  - `.todo-enter`, `.todo-leave` : animations
  - `.filter-btn.active` : filtre actif

### JS (`app.js`)
```js
// Structure de donnees
interface Todo {
  id: string;        // crypto.randomUUID()
  text: string;
  completed: boolean;
  createdAt: number; // Date.now()
}

// API publique exposee
class TodoApp {
  constructor()                              // charge depuis localStorage, init DOM
  get todos(): Todo[]                        // getter prive
  get filter(): 'all' | 'active' | 'completed'
  set filter(value)

  addTodo(text: string): void                // cree et ajoute
  toggleTodo(id: string): void               // bascule completed
  removeTodo(id: string): void               // supprime
  clearCompleted(): void                     // supprime toutes les completed
  get filteredTodos(): Todo[]                // selon le filtre courant
  get activeCount(): number                  // count !completed

  save(): void                               // persiste dans localStorage
  render(): void                             // re-affiche la liste
}
```

### Persistance
- Cle localStorage : `memoriX_todos`
- Charge au constructeur, sauvegarde a chaque mutation

## Instructions pour @dev_branch
1. Creer le dossier `packages/todo-app/` s'il n'existe pas
2. Creer `index.html` avec structure Tailwind, Inter, Font Awesome
3. Creer `style.css` avec animations et glassmorphism
4. Creer `app.js` avec la classe TodoApp complete
5. Le design DOIT etre premium : dark mode, glassmorphism, animations
