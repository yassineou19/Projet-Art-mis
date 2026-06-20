"""Comparaison et activation des plans en mode démonstration."""

from html import escape

import streamlit as st

from src.profiles import (
    get_profile_plan,
    load_subscription_plans,
    update_subscription_plan,
)
from src.ui import (
    get_user_id,
    page_header,
    render_sidebar,
    require_auth,
    section_title,
)


user = require_auth()
render_sidebar(user)
profile = st.session_state.get("profile") or {}
current_plan = get_profile_plan(profile)
user_id = get_user_id(user)

page_header(
    title="Abonnements Artemis",
    subtitle="Choisissez le niveau d'analyse adapté à votre usage.",
    eyebrow="ARTEMIS · PLANS",
    badge="Mode démonstration",
)

st.info(
    "Projet école : aucun paiement n'est effectué. Le changement de plan sert à "
    "démontrer les droits Free, Pro et Premium."
)

try:
    plans = load_subscription_plans()
except Exception as exc:
    st.error(f"Impossible de charger les offres : {exc}")
    st.stop()

columns = st.columns(len(plans))
for column, plan in zip(columns, plans):
    plan_id = str(plan["id"])
    is_current = plan_id == current_plan
    included = [item for item in plan["features"] if item["is_included"]]
    with column:
        status = "PLAN ACTUEL" if is_current else "OFFRE"
        price = int(plan["price_monthly_eur"])
        features_html = "".join(
            f"<li>{escape(str(item['feature']))}</li>" for item in included
        )
        st.markdown(
            f"""
            <div class="artemis-card" style="min-height:390px;">
                <div class="artemis-eyebrow">{status}</div>
                <h2 style="margin:.35rem 0;">{escape(str(plan['name']))}</h2>
                <div style="font-size:2rem;font-weight:800;">{price} EUR<span
                    class="artemis-muted" style="font-size:.9rem;font-weight:500;"> / mois</span>
                </div>
                <p class="artemis-muted">{escape(str(plan['description']))}</p>
                <ul style="padding-left:1.2rem;line-height:1.8;">{features_html}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if is_current:
            st.button("Plan actif", key=f"active_{plan_id}", disabled=True, width="stretch")
        elif st.button(
            f"Activer {plan['name']}",
            key=f"activate_{plan_id}",
            type="primary" if plan_id != "free" else "secondary",
            width="stretch",
        ):
            if not user_id:
                st.error("Identifiant utilisateur indisponible.")
            else:
                update_subscription_plan(user_id, plan_id)
                st.session_state["profile"] = {**profile, "subscription_plan": plan_id}
                st.cache_data.clear()
                st.rerun()

section_title("Positionnement des offres")
st.markdown(
    """
    **Free** permet de vérifier la valeur du produit. **Pro** transforme le score en
    analyse explicable et comparable. **Premium** ajoute la surveillance continue,
    les simulations et les livrables professionnels.
    """
)
