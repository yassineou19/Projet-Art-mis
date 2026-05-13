"""Profils métier Artemis liés aux comptes Supabase Auth."""

from __future__ import annotations

from src.database import connection


VALID_USER_TYPES = {"space_enthusiast", "journalist"}
VALID_SUBSCRIPTION_PLANS = {"free", "pro", "premium"}

USER_TYPE_LABELS = {
    "space_enthusiast": "Passionne d'espace",
    "journalist": "Journaliste scientifique",
}

SUBSCRIPTION_PLAN_LABELS = {
    "free": "Free",
    "pro": "Pro",
    "premium": "Premium",
}

FALLBACK_SUBSCRIPTION_PLANS = [
    {
        "id": "free",
        "name": "Free",
        "price_monthly_eur": 0,
        "description": "Decouverte des donnees essentielles Artemis.",
        "features": [],
    },
    {
        "id": "pro",
        "name": "Pro",
        "price_monthly_eur": 30,
        "description": "Analyses avancees et exports pour utilisateurs reguliers.",
        "features": [],
    },
    {
        "id": "premium",
        "name": "Premium",
        "price_monthly_eur": 100,
        "description": "Briefings enrichis, signaux de veille et analyses professionnelles.",
        "features": [],
    },
]


def create_user_profile(
    user_id: str,
    email: str,
    user_type: str,
    subscription_plan: str,
) -> None:
    """Crée ou met à jour le profil métier d'un utilisateur Artemis."""
    if user_type not in VALID_USER_TYPES:
        raise ValueError(f"Type d'utilisateur invalide: {user_type}")
    if subscription_plan not in VALID_SUBSCRIPTION_PLANS:
        raise ValueError(f"Plan d'abonnement invalide: {subscription_plan}")

    query = """
    insert into public.user_profiles (
        id,
        email,
        user_type,
        subscription_plan,
        subscription_status
    )
    values (%s, %s, %s, %s, 'active')
    on conflict (id)
    do update set
        email = excluded.email,
        user_type = excluded.user_type,
        subscription_plan = excluded.subscription_plan,
        subscription_status = excluded.subscription_status;
    """

    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    user_id,
                    email,
                    user_type,
                    subscription_plan,
                ),
            )
        conn.commit()


def load_user_profile(user_id: str) -> dict | None:
    """Charge le profil métier Artemis d'un utilisateur."""
    query = """
    select
        id,
        email,
        user_type,
        subscription_plan,
        subscription_status,
        created_at,
        updated_at
    from public.user_profiles
    where id = %s;
    """

    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (user_id,))
            row = cur.fetchone()

    if row is None:
        return None

    return {
        "id": str(row[0]),
        "email": row[1],
        "user_type": row[2],
        "subscription_plan": row[3],
        "subscription_status": row[4],
        "created_at": row[5],
        "updated_at": row[6],
    }


def load_subscription_plans() -> list[dict]:
    """Charge les offres d'abonnement et leurs fonctionnalités depuis Supabase."""
    plans_query = """
    select
        id,
        name,
        price_monthly_eur,
        description
    from public.subscription_plans
    where is_active = true
    order by display_order;
    """

    features_query = """
    select
        plan_id,
        feature,
        is_included
    from public.subscription_plan_features
    order by plan_id, display_order;
    """

    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(plans_query)
            plan_rows = cur.fetchall()

            cur.execute(features_query)
            feature_rows = cur.fetchall()

    features_by_plan: dict[str, list[dict]] = {}
    for plan_id, feature, is_included in feature_rows:
        features_by_plan.setdefault(plan_id, []).append(
            {
                "feature": feature,
                "is_included": is_included,
            }
        )

    plans = []
    for plan_id, name, price_monthly_eur, description in plan_rows:
        plans.append(
            {
                "id": plan_id,
                "name": name,
                "price_monthly_eur": price_monthly_eur,
                "description": description,
                "features": features_by_plan.get(plan_id, []),
            }
        )

    return plans or FALLBACK_SUBSCRIPTION_PLANS


def get_user_type_label(user_type: str | None) -> str:
    """Retourne le libellé affichable d'un type utilisateur."""
    return USER_TYPE_LABELS.get(user_type or "", "Profil non configure")


def get_subscription_plan_label(subscription_plan: str | None) -> str:
    """Retourne le libellé affichable d'un plan."""
    return SUBSCRIPTION_PLAN_LABELS.get(subscription_plan or "", "Plan non configure")


def get_profile_plan(profile: dict | None) -> str:
    """Retourne le plan d'un profil, ou free par défaut."""
    if not profile:
        return "free"
    return profile.get("subscription_plan") or "free"


def is_free(profile: dict | None) -> bool:
    """Indique si le profil est sur le plan Free."""
    return get_profile_plan(profile) == "free"


def is_pro(profile: dict | None) -> bool:
    """Indique si le profil est sur le plan Pro."""
    return get_profile_plan(profile) == "pro"


def is_premium(profile: dict | None) -> bool:
    """Indique si le profil est sur le plan Premium."""
    return get_profile_plan(profile) == "premium"


def can_access_pro_features(profile: dict | None) -> bool:
    """Fonctionnalités disponibles à partir du plan Pro."""
    return get_profile_plan(profile) in {"pro", "premium"}


def can_access_premium_features(profile: dict | None) -> bool:
    """Fonctionnalités réservées au plan Premium."""
    return is_premium(profile)


def can_export(profile: dict | None) -> bool:
    """Exports disponibles à partir du plan Pro."""
    return can_access_pro_features(profile)


def can_access_advanced_briefing(profile: dict | None) -> bool:
    """Briefing enrichi disponible à partir du plan Pro."""
    return can_access_pro_features(profile)
