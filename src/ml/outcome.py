"""Classification, calibration et explication du risque de lancement."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import beta as beta_distribution
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.frozen import FrozenEstimator
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


MODEL_VERSION = "artemis-risk-v2"
SUCCESS_STATUS = "Launch Successful"
FAILURE_STATUSES = {"Launch Failure", "Launch was a Partial Failure"}
LABELED_STATUSES = {SUCCESS_STATUS, *FAILURE_STATUSES}

CATEGORICAL_FEATURES = [
    "agency",
    "country",
    "rocket",
    "orbit",
    "mission_type",
    "agency_type",
    "pad",
]
NUMERIC_FEATURES = [
    "latitude",
    "longitude",
    "agency_attempts",
    "pad_attempts",
    "location_attempts",
    "orbital_attempts",
    "launch_year",
    "month_sin",
    "month_cos",
]
MIN_LABELED_ROWS = 200
EVALUATION_TRAIN_SHARE = 0.70
EVALUATION_CALIBRATION_SHARE = 0.10
FINAL_CALIBRATION_SHARE = 0.10

FEATURE_LABELS = {
    "agency": "Agence",
    "country": "Zone de lancement",
    "rocket": "Famille de fusée",
    "orbit": "Orbite visée",
    "mission_type": "Type de mission",
    "agency_type": "Type d'agence",
    "pad": "Pas de tir",
    "latitude": "Latitude du site",
    "longitude": "Longitude du site",
    "agency_attempts": "Expérience de l'agence",
    "pad_attempts": "Expérience du pas de tir",
    "location_attempts": "Expérience du site",
    "orbital_attempts": "Maturité du marché orbital",
    "launch_year": "Période technologique",
    "month_sin": "Saisonnalité",
    "month_cos": "Saisonnalité",
}


@dataclass(frozen=True)
class OutcomeModelResult:
    model: CalibratedClassifierCV
    base_model: Pipeline
    validation: pd.DataFrame
    calibration: pd.DataFrame
    decision_threshold: float
    roc_auc: float
    average_precision: float
    balanced_accuracy: float
    failure_recall: float
    failure_precision: float
    brier_score: float
    confusion: np.ndarray
    test_start: pd.Timestamp
    training_rows: int
    failure_rate: float
    model_version: str = MODEL_VERSION


def _prepare_features(launches: pd.DataFrame) -> pd.DataFrame:
    prepared = launches.copy()
    dates = pd.to_datetime(prepared["launch_date"], errors="coerce", utc=True)
    prepared["launch_year"] = dates.dt.year
    month = dates.dt.month
    prepared["month_sin"] = np.sin(2 * np.pi * month / 12)
    prepared["month_cos"] = np.cos(2 * np.pi * month / 12)

    for column in CATEGORICAL_FEATURES:
        if column not in prepared:
            prepared[column] = pd.NA

    for column in NUMERIC_FEATURES:
        if column not in prepared:
            prepared[column] = np.nan
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce")

    count_columns = [
        "agency_attempts",
        "pad_attempts",
        "location_attempts",
        "orbital_attempts",
    ]
    prepared[count_columns] = np.log1p(prepared[count_columns].clip(lower=0))
    return prepared[CATEGORICAL_FEATURES + NUMERIC_FEATURES]


def _make_pipeline() -> Pipeline:
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", min_frequency=3)),
        ]
    )
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    preprocessor = ColumnTransformer(
        [
            ("categorical", categorical, CATEGORICAL_FEATURES),
            ("numeric", numeric, NUMERIC_FEATURES),
        ]
    )
    classifier = LogisticRegression(
        C=0.05,
        class_weight="balanced",
        max_iter=2000,
        solver="liblinear",
        random_state=42,
    )
    return Pipeline([("preprocessor", preprocessor), ("classifier", classifier)])


def _fit_calibrated_model(
    train: pd.DataFrame,
    y_train: pd.Series,
    calibration: pd.DataFrame,
    y_calibration: pd.Series,
) -> tuple[Pipeline, CalibratedClassifierCV]:
    base_model = _make_pipeline()
    base_model.fit(_prepare_features(train), y_train)
    calibrated = CalibratedClassifierCV(FrozenEstimator(base_model), method="sigmoid")
    calibrated.fit(_prepare_features(calibration), y_calibration)
    return base_model, calibrated


def _select_threshold(target: pd.Series, scores: np.ndarray) -> float:
    candidates = np.linspace(0.02, min(0.40, max(float(scores.max()), 0.02)), 160)
    ranked = []
    for threshold in candidates:
        predictions = scores >= threshold
        score = balanced_accuracy_score(target, predictions)
        precision = precision_score(target, predictions, zero_division=0)
        ranked.append((score, precision, threshold))
    return float(max(ranked)[2])


def train_outcome_classifier(launches: pd.DataFrame) -> OutcomeModelResult:
    """Évalue chronologiquement puis entraîne un classifieur calibré."""
    required = {"launch_date", "status"}
    missing = required.difference(launches.columns)
    if missing:
        raise ValueError(f"Colonnes requises absentes: {', '.join(sorted(missing))}")

    labeled = launches[launches["status"].isin(LABELED_STATUSES)].copy()
    labeled["launch_date"] = pd.to_datetime(
        labeled["launch_date"], errors="coerce", utc=True
    )
    labeled = labeled.dropna(subset=["launch_date"]).sort_values("launch_date")

    if len(labeled) < MIN_LABELED_ROWS:
        raise ValueError(f"Au moins {MIN_LABELED_ROWS} lancements labellisés sont nécessaires.")

    target = labeled["status"].isin(FAILURE_STATUSES).astype(int)
    if target.nunique() < 2:
        raise ValueError("Les classes réussite et échec doivent toutes les deux être présentes.")

    train_end = int(len(labeled) * EVALUATION_TRAIN_SHARE)
    calibration_end = int(
        len(labeled) * (EVALUATION_TRAIN_SHARE + EVALUATION_CALIBRATION_SHARE)
    )
    evaluation_train = labeled.iloc[:train_end]
    evaluation_calibration = labeled.iloc[train_end:calibration_end]
    validation = labeled.iloc[calibration_end:]
    y_evaluation_train = target.iloc[:train_end]
    y_evaluation_calibration = target.iloc[train_end:calibration_end]
    y_validation = target.iloc[calibration_end:]

    _, evaluation_model = _fit_calibrated_model(
        evaluation_train,
        y_evaluation_train,
        evaluation_calibration,
        y_evaluation_calibration,
    )
    calibration_scores = evaluation_model.predict_proba(
        _prepare_features(evaluation_calibration)
    )[:, 1]
    decision_threshold = _select_threshold(
        y_evaluation_calibration, calibration_scores
    )
    risk_scores = evaluation_model.predict_proba(_prepare_features(validation))[:, 1]
    predictions = (risk_scores >= decision_threshold).astype(int)

    validation_results = validation[
        ["launch_id", "launch_name", "launch_date", "status"]
    ].copy()
    validation_results["actual_failure"] = y_validation.to_numpy()
    validation_results["risk_score"] = risk_scores
    validation_results["predicted_failure"] = predictions

    observed, predicted = calibration_curve(
        y_validation, risk_scores, n_bins=8, strategy="quantile"
    )
    calibration_results = pd.DataFrame(
        {"predicted_risk": predicted, "observed_failure_rate": observed}
    )

    final_calibration_size = max(int(len(labeled) * FINAL_CALIBRATION_SHARE), 50)
    final_train = labeled.iloc[:-final_calibration_size]
    final_calibration = labeled.iloc[-final_calibration_size:]
    y_final_train = target.iloc[:-final_calibration_size]
    y_final_calibration = target.iloc[-final_calibration_size:]
    base_model, final_model = _fit_calibrated_model(
        final_train,
        y_final_train,
        final_calibration,
        y_final_calibration,
    )

    return OutcomeModelResult(
        model=final_model,
        base_model=base_model,
        validation=validation_results,
        calibration=calibration_results,
        decision_threshold=decision_threshold,
        roc_auc=float(roc_auc_score(y_validation, risk_scores)),
        average_precision=float(average_precision_score(y_validation, risk_scores)),
        balanced_accuracy=float(balanced_accuracy_score(y_validation, predictions)),
        failure_recall=float(recall_score(y_validation, predictions, zero_division=0)),
        failure_precision=float(precision_score(y_validation, predictions, zero_division=0)),
        brier_score=float(brier_score_loss(y_validation, risk_scores)),
        confusion=confusion_matrix(y_validation, predictions, labels=[0, 1]),
        test_start=validation["launch_date"].iloc[0],
        training_rows=len(labeled),
        failure_rate=float(target.mean()),
    )


def risk_interval(
    result: OutcomeModelResult,
    risk_score: float,
    neighbors: int = 150,
) -> tuple[float, float]:
    """Estime une fourchette empirique avec les scores de validation voisins."""
    validation = result.validation.copy()
    validation["distance"] = (validation["risk_score"] - risk_score).abs()
    nearest = validation.nsmallest(min(neighbors, len(validation)), "distance")
    failures = int(nearest["actual_failure"].sum())
    successes = len(nearest) - failures
    lower, upper = beta_distribution.ppf(
        [0.10, 0.90], failures + 0.5, successes + 0.5
    )
    return float(lower), float(upper)


def predict_outcomes(result: OutcomeModelResult, launches: pd.DataFrame) -> pd.DataFrame:
    """Ajoute un risque calibré, une fourchette et la classe prédite."""
    predictions = launches.copy()
    scores = result.model.predict_proba(_prepare_features(predictions))[:, 1]
    predictions["risk_score"] = scores
    predictions["predicted_failure"] = scores >= result.decision_threshold
    predictions["prediction"] = np.where(
        predictions["predicted_failure"],
        "Risque d'échec élevé",
        "Réussite probable",
    )
    intervals = [risk_interval(result, float(score)) for score in scores]
    predictions["risk_lower"] = [interval[0] for interval in intervals]
    predictions["risk_upper"] = [interval[1] for interval in intervals]
    return predictions


def reliability_summary(
    launches: pd.DataFrame,
    selected: pd.Series,
    group_column: str,
    prior_strength: float = 20.0,
) -> dict:
    """Calcule une fiabilité bayésienne, ramenée vers la moyenne globale."""
    labeled = launches[launches["status"].isin(LABELED_STATUSES)].copy()
    selected_date = pd.to_datetime(selected["launch_date"], errors="coerce", utc=True)
    dates = pd.to_datetime(labeled["launch_date"], errors="coerce", utc=True)
    labeled = labeled[dates < selected_date]
    value = selected.get(group_column)
    group_value = value if pd.notna(value) and value else "UNKNOWN"
    group = labeled[labeled[group_column].fillna("UNKNOWN") == group_value]

    global_failure_rate = float(labeled["status"].isin(FAILURE_STATUSES).mean())
    failures = int(group["status"].isin(FAILURE_STATUSES).sum())
    attempts = len(group)
    prior_failures = global_failure_rate * prior_strength
    alpha = failures + prior_failures
    beta = attempts - failures + (1 - global_failure_rate) * prior_strength
    failure_mean = alpha / (alpha + beta)
    failure_low, failure_high = beta_distribution.ppf([0.10, 0.90], alpha, beta)
    return {
        "label": value if pd.notna(value) and value else "Inconnu",
        "attempts": attempts,
        "failures": failures,
        "success_rate": 1 - failure_mean,
        "success_low": 1 - failure_high,
        "success_high": 1 - failure_low,
    }


def explain_prediction(
    result: OutcomeModelResult,
    launch: pd.DataFrame,
    limit: int = 6,
) -> pd.DataFrame:
    """Retourne les contributions locales les plus fortes du modèle linéaire."""
    prepared = _prepare_features(launch.iloc[[0]])
    preprocessor = result.base_model.named_steps["preprocessor"]
    classifier = result.base_model.named_steps["classifier"]
    transformed = preprocessor.transform(prepared)
    values = transformed.toarray()[0] if hasattr(transformed, "toarray") else transformed[0]
    names = preprocessor.get_feature_names_out()
    contributions = values * classifier.coef_[0]

    rows = []
    for feature_name, contribution in zip(names, contributions):
        if abs(float(contribution)) < 1e-9:
            continue
        label = _humanize_feature(feature_name)
        rows.append(
            {
                "factor": label,
                "direction": "Augmente le risque" if contribution > 0 else "Réduit le risque",
                "impact": float(abs(contribution)),
                "signed_impact": float(contribution),
            }
        )
    return pd.DataFrame(rows).nlargest(limit, "impact").reset_index(drop=True)


def _humanize_feature(feature_name: str) -> str:
    name = feature_name.split("__", 1)[-1]
    if name in FEATURE_LABELS:
        return FEATURE_LABELS[name]
    for feature in sorted(CATEGORICAL_FEATURES, key=len, reverse=True):
        prefix = f"{feature}_"
        if name.startswith(prefix):
            return f"{FEATURE_LABELS[feature]} : {name[len(prefix):]}"
    return FEATURE_LABELS.get(name, name.replace("_", " ").capitalize())
