"""Briefing personnalise selon le profil utilisateur Artemis."""

import streamlit as st

from src.profiles import (
    can_access_advanced_briefing,
    can_access_premium_features,
    can_export,
    get_subscription_plan_label,
    get_user_type_label,
    is_free,
)
from src.queries import load_dashboard_data
from src.ui import (
    ARTEMIS_COLORS,
    insight,
    kpi_card,
    page_header,
    render_sidebar,
    require_auth,
    section_title,
    style_plotly,
)

import plotly.express as px


user = require_auth()
render_sidebar(user)

profile = st.session_state.get("profile") or {}
user_type = profile.get("user_type")
subscription_plan = profile.get("subscription_plan")
user_type_label = get_user_type_label(user_type)
plan_label = get_subscription_plan_label(subscription_plan)
has_advanced_briefing = can_access_advanced_briefing(profile)
has_premium_features = can_access_premium_features(profile)
has_export = can_export(profile)

page_header(
    title="Briefing personnalise",
    subtitle="Une lecture adaptee a votre profil et a votre usage d'Artemis.",
    eyebrow="ANALYTICS · BRIEFING",
    badge=f"{user_type_label} · {plan_label}",
)

try:
    data = load_dashboard_data()
except Exception as e:
    st.error(f"Impossible de charger les donnees: {e}")
    st.stop()

launches_by_year = data["launches_by_year"]
top_agencies = data["top_agencies"]
launches_by_country = data["launches_by_country"]
growth = data["growth"]

latest_year = None
latest_launches = 0
peak_year = None
peak_launches = 0

if not launches_by_year.empty:
    ordered_years = launches_by_year.sort_values("year")
    latest = ordered_years.iloc[-1]
    peak = launches_by_year.loc[launches_by_year["launches"].idxmax()]
    latest_year = int(latest["year"])
    latest_launches = int(latest["launches"])
    peak_year = int(peak["year"])
    peak_launches = int(peak["launches"])

top_agency = top_agencies.iloc[0] if not top_agencies.empty else None
top_country = (
    launches_by_country.sort_values("launches", ascending=False).iloc[0]
    if not launches_by_country.empty else None
)

best_growth = None
if not growth.empty:
    best_growth = growth.loc[growth["growth_pct"].idxmax()]


def _value(row, key: str, fallback: str = "-"):
    return row[key] if row is not None and key in row else fallback


def render_common_snapshot() -> None:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Derniere annee", latest_year or "-")
    with c2:
        kpi_card("Lancements recents", latest_launches)
    with c3:
        kpi_card("Agence leader", _value(top_agency, "agency"))
    with c4:
        kpi_card("Pays leader", _value(top_country, "country"))


def render_plan_banner() -> None:
    if is_free(profile):
        title = "Apercu Free"
        text = "Vous voyez les chiffres essentiels. Les analyses avancees, exports et signaux editoriaux sont verrouilles."
    elif has_premium_features:
        title = "Experience Premium"
        text = "Vous avez acces au briefing complet, aux exports et aux signaux de veille."
    else:
        title = "Experience Pro"
        text = "Vous avez acces aux analyses avancees et aux exports du briefing."

    st.markdown(
        f"""
        <div class="artemis-card" style="border-left: 3px solid var(--primary);">
            <div class="artemis-eyebrow">{plan_label}</div>
            <h3 style="margin:.25rem 0;">{title}</h3>
            <p class="artemis-muted" style="margin:0;">{text}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_locked_card(title: str, text: str, plan: str = "Pro") -> None:
    st.markdown(
        f"""
        <div class="artemis-card" style="opacity:.72;border-style:dashed;">
            <div class="artemis-eyebrow">Verrouille · {plan}</div>
            <h3>{title}</h3>
            <p class="artemis-muted">{text}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


render_common_snapshot()
st.markdown("")
render_plan_banner()
st.markdown("")

if user_type == "journalist":
    section_title("Angles editoriaux")

    leader_agency = _value(top_agency, "agency")
    leader_country = _value(top_country, "country")
    leader_agency_launches = int(top_agency["launches"]) if top_agency is not None else 0
    leader_country_launches = int(top_country["launches"]) if top_country is not None else 0

    st.markdown(
        f"""
        <div class="artemis-card">
            <div class="artemis-eyebrow">Angle 1</div>
            <h3>La concentration du marche des lancements spatiaux</h3>
            <p class="artemis-muted">
                L'agence <strong>{leader_agency}</strong> domine le volume observe avec
                <strong>{leader_agency_launches}</strong> lancements. Cet angle permet de raconter
                la competition entre acteurs historiques et nouveaux entrants.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("")
    if has_advanced_briefing:
        st.markdown(
            f"""
            <div class="artemis-card">
                <div class="artemis-eyebrow">Angle 2 · Pro</div>
                <h3>La geographie de la puissance spatiale</h3>
                <p class="artemis-muted">
                    <strong>{leader_country}</strong> ressort comme zone dominante avec
                    <strong>{leader_country_launches}</strong> lancements. Un sujet utile pour expliquer
                    les rapports de force entre pays et bases de lancement.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        render_locked_card(
            "Angle geographique",
            "Debloquez la lecture pays/sites pour construire un article plus contextualise.",
            "Pro",
        )
    st.markdown("")
    if best_growth is not None:
        insight(
            f"Chiffre a citer: la plus forte croissance annuelle observee est "
            f"<strong>{best_growth['growth_pct']:.1f}%</strong> en "
            f"<strong>{int(best_growth['year'])}</strong>."
        )

    if has_advanced_briefing:
        section_title("Briefing Pro")
        st.markdown(
            f"""
            <div class="artemis-card">
                <div class="artemis-eyebrow">Synthese exploitable</div>
                <h3>Un angle pret a developper</h3>
                <p class="artemis-muted">
                    Comparez <strong>{leader_agency}</strong> aux autres acteurs du top 8 pour
                    illustrer la concentration du secteur. La formulation editoriale la plus directe:
                    "quelques agences structurent encore l'essentiel de l'activite mondiale,
                    malgre l'arrivee de nouveaux entrants prives".
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if has_premium_features:
        st.markdown("")
        st.markdown(
            f"""
            <div class="artemis-card">
                <div class="artemis-eyebrow">Premium</div>
                <h3>Signal a surveiller</h3>
                <p class="artemis-muted">
                    Surveillez les ruptures de croissance annuelle et les changements de leader:
                    ce sont les meilleurs signaux pour produire une analyse avant les pics
                    mediatiques lies aux grandes missions.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif has_advanced_briefing:
        st.markdown("")
        render_locked_card(
            "Signal de veille Premium",
            "Ajoutez une couche de signaux a surveiller pour anticiper les sujets forts.",
            "Premium",
        )

    if has_advanced_briefing:
        section_title("Graphique recommande")
        fig = px.bar(
            top_agencies.head(8),
            x="launches",
            y="agency",
            orientation="h",
            color="agency",
            color_discrete_sequence=ARTEMIS_COLORS,
        )
        fig.update_layout(showlegend=False, yaxis={"categoryorder": "total ascending"})
        fig.update_traces(
            marker_line_width=0,
            hovertemplate="<b>%{y}</b><br>%{x} lancements<extra></extra>",
        )
        style_plotly(fig, height=380)
        st.plotly_chart(fig, use_container_width=True)

        if has_export:
            csv = top_agencies.head(8).to_csv(index=False).encode("utf-8")
            st.download_button(
                "Exporter les agences du briefing",
                data=csv,
                file_name="artemis_briefing_agencies.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary",
            )
    else:
        section_title("Graphique recommande")
        render_locked_card(
            "Graphique editorial exportable",
            "Le plan Pro debloque le graphique recommande et l'export CSV associe.",
            "Pro",
        )

else:
    section_title("Ce qu'il faut retenir")

    st.markdown(
        f"""
        <div class="artemis-card">
            <h3>L'activite spatiale se lit comme une course dans le temps</h3>
            <p class="artemis-muted">
                Le pic observe se situe en <strong>{peak_year or '-'}</strong> avec
                <strong>{peak_launches}</strong> lancements. C'est un bon point de depart
                pour comprendre les periodes ou l'industrie accelere.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("")
    if has_advanced_briefing:
        st.markdown(
            f"""
            <div class="artemis-card">
                <div class="artemis-eyebrow">Pro</div>
                <h3>Les lancements sont concentres autour de quelques acteurs</h3>
                <p class="artemis-muted">
                    L'agence la plus active dans les donnees est <strong>{_value(top_agency, "agency")}</strong>,
                    et le pays le plus represente est <strong>{_value(top_country, "country")}</strong>.
                    La carte mondiale permet ensuite de voir ou cette activite se concentre.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        render_locked_card(
            "Lecture des acteurs dominants",
            "Le plan Pro debloque l'analyse des agences et pays qui structurent l'activite spatiale.",
            "Pro",
        )
    st.markdown("")
    insight(
        "Astuce: commencez par comparer les periodes avant et apres 2010 pour voir "
        "l'arrivee des nouveaux acteurs prives et la montee en puissance de nouveaux pays."
    )

    if has_advanced_briefing:
        section_title("Exploration Pro")
        st.markdown(
            f"""
            <div class="artemis-card">
                <h3>Question d'exploration</h3>
                <p class="artemis-muted">
                    Essayez d'expliquer pourquoi <strong>{_value(top_agency, "agency")}</strong>
                    domine les donnees: cadence de lancement, type de missions, periode recente
                    ou poids historique. Cette lecture transforme le graphique en vraie histoire.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if has_premium_features:
        st.markdown("")
        st.markdown(
            """
            <div class="artemis-card">
                <div class="artemis-eyebrow">Premium</div>
                <h3>Parcours recommande</h3>
                <p class="artemis-muted">
                    Passez du Dashboard a la Carte mondiale, puis a Space Race: ce parcours
                    permet de relier volume, geographie et competition entre agences.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif has_advanced_briefing:
        st.markdown("")
        render_locked_card(
            "Parcours Premium recommande",
            "Le plan Premium ajoute un parcours de lecture entre Dashboard, Carte mondiale et Space Race.",
            "Premium",
        )

    if has_advanced_briefing:
        section_title("Evolution simplifiee")
        fig = px.area(
            launches_by_year,
            x="year",
            y="launches",
            color_discrete_sequence=[ARTEMIS_COLORS[0]],
        )
        fig.update_traces(
            line=dict(width=2.5),
            fillcolor="rgba(124,58,237,0.16)",
            hovertemplate="Annee %{x}<br>%{y} lancements<extra></extra>",
        )
        style_plotly(fig, height=360)
        st.plotly_chart(fig, use_container_width=True)

        if has_export:
            csv = launches_by_year.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Exporter l'evolution annuelle",
                data=csv,
                file_name="artemis_briefing_launches_by_year.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary",
            )
    else:
        section_title("Evolution simplifiee")
        render_locked_card(
            "Graphique d'evolution",
            "Le plan Pro debloque la visualisation detaillee et l'export de l'evolution annuelle.",
            "Pro",
        )

if is_free(profile):
    st.info(
        "Votre plan Free affiche un briefing d'aperçu. Les blocs Pro, Premium et les "
        "exports sont disponibles avec les offres superieures."
    )
