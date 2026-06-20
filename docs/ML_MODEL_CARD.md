# Artemis Risk v2 - Model Card

## Objectif

Classer les prochains lancements en `Réussite probable` ou `Risque d'échec élevé`
et produire un risque calibré. Le modèle est une aide à l'analyse, pas une
certification de sûreté.

## Données

- 7 540 lancements labellisés entre 1957 et 2025.
- Cible positive : échec total ou partiel.
- Taux historique d'échec : environ 7,3 %.
- Variables : agence, fusée, orbite, mission, site, géographie, date et compteurs
  d'expérience disponibles avant le lancement.

## Méthode

- Régression logistique pondérée avec encodage des catégories.
- Séparation chronologique : 70 % entraînement, 10 % calibration, 20 % test.
- Calibration sigmoid sur une période distincte.
- Seuil opérationnel choisi sur la période de calibration selon la balanced accuracy.
- Fiabilité bayésienne par agence et famille de fusée avec retour vers la moyenne
  globale lorsque l'historique est faible.

## Résultats actuels

- ROC-AUC : 0,868.
- PR-AUC : 0,274 pour une prévalence proche de 0,046 sur le test récent.
- Balanced accuracy : 0,776.
- Rappel des échecs : 0,771.
- Brier score : 0,039.

Ces métriques sont recalculées à chaque entraînement et affichées dans le monitoring
Premium.

## Limites

- Les échecs sont rares : une alerte ne signifie pas qu'un échec va se produire.
- Les données publiques ne contiennent pas la télémétrie, les contrôles qualité ou
  toutes les conditions météorologiques internes aux opérateurs.
- Les nouvelles fusées ont peu d'historique; l'estimation bayésienne réduit cette
  instabilité sans la supprimer.
- Un changement de source ou de définition des statuts peut créer une dérive.

## Surveillance

Suivre la calibration, la PR-AUC, le rappel des échecs, le Brier score, la couverture
des variables et l'évolution des scores enregistrés. Réentraîner après chaque lot
significatif de nouveaux résultats.
