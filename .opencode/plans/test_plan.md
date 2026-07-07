# Test Plan - Todo List

## Tests fonctionnels (manuels)

### Test : Ajout d'une tache
1. Saisir "Acheter du pain" dans l'input
2. Cliquer "Ajouter" ou Enter
3. Verifier que la tache apparait dans la liste
4. Verifier que le compteur indique "1 tache restante"

### Test : Completion d'une tache
1. Cocher la checkbox d'une tache
2. Verifier le style barre / opacite reduite
3. Verifier que le compteur decremente

### Test : Suppression d'une tache
1. Cliquer l'icone poubelle sur une tache
2. Verifier qu'elle disparait (animation)

### Test : Filtres
1. Ajouter 3 taches, en completer 1
2. Cliquer "Actives" -> voir 2 taches
3. Cliquer "Terminees" -> voir 1 tache
4. Cliquer "Toutes" -> voir 3 taches

### Test : Effacer terminees
1. Avoir au moins 1 tache terminee
2. Cliquer "Effacer terminees"
3. Verifier que les terminees disparaissent

### Test : Persistance localStorage
1. Ajouter une tache, actualiser la page
2. Verifier que la tache est toujours presente
3. Verifier l'etat completed persiste

## Tests d'integrite
- Input vide : desactiver le bouton ou empecher l'ajout
- Input " " (espaces) : trim avant ajout
- localStorage corrompu : fallback a un tableau vide
