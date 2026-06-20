# Artemis Space Analytics

Application Streamlit d'analyse mondiale des lancements spatiaux avec ingestion
Supabase, carte 3D, Data Control Center et moteur ML de risque de lancement.

## Installation

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Expérience ML

- **Free** : 3 analyses mensuelles et niveau de risque simplifié.
- **Pro** : score calibré, intervalle, explications, fiabilité, comparaison et CSV.
- **Premium** : scénarios, watchlist, alertes, historique, monitoring et PDF.

Le changement d'abonnement est simulé sans paiement depuis la page `Abonnements`.
La méthodologie est détaillée dans `docs/ML_MODEL_CARD.md`.

## Tests

```bash
python -m unittest discover -s tests -v
```
