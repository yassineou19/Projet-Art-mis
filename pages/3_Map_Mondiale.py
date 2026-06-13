"""Carte mondiale — projection, période, KPIs, insight."""

import json

import streamlit as st
from streamlit.components.v1 import html

from src.queries import load_view
from src.ui import (
    require_auth, render_sidebar, page_header, kpi_card,
    insight, section_title, format_number, get_theme_mode,
)

user = require_auth()
render_sidebar(user)

page_header(
    title="Carte mondiale des lancements",
    subtitle="Géographie des sites actifs : identifier les hubs et l'émergence de nouveaux acteurs.",
    eyebrow="ANALYTICS · GEOGRAPHY",
    badge="Géospatial",
)

try:
    df = load_view("launches_map")
except Exception as e:
    st.error(f"Impossible de charger les données : {e}")
    st.stop()

years = sorted(df["launch_year"].dropna().unique().astype(int).tolist())
if not years:
    st.warning("Aucune donnée géographique disponible.")
    st.stop()

# === Filtres ===
ctrl1, ctrl2 = st.columns([3, 1])
with ctrl1:
    y_min, y_max = min(years), max(years)
    y_from, y_to = st.slider(
        "Période", min_value=y_min, max_value=y_max,
        value=(y_min, y_max),
        help="Filtre les lancements affichés sur la carte.",
    )
with ctrl2:
    map_focus = st.selectbox(
        "Vue",
        ["Globe", "Top hubs", "Europe / Asie"],
        index=0,
    )

mask = (df["launch_year"] >= y_from) & (df["launch_year"] <= y_to)
filtered = df[mask]

if filtered.empty:
    st.warning("Aucun lancement sur la période sélectionnée.")
    st.stop()

country_counts = (
    filtered.groupby(["country", "latitude", "longitude"])
    .size().reset_index(name="launches")
    .sort_values("launches", ascending=False)
)

# === KPIs ===
k1, k2, k3 = st.columns(3)
with k1:
    kpi_card("Lancements affichés", format_number(int(country_counts["launches"].sum())))
with k2:
    kpi_card("Sites actifs", str(len(country_counts)))
with k3:
    top_site = country_counts.iloc[0]
    kpi_card(
        "Site #1",
        str(top_site["country"]),
        delta=f"{format_number(top_site['launches'])} lancements",
    )

st.markdown("")

# === Carte ===
section_title("Carte des sites actifs")

mode = get_theme_mode()
max_launches = max(int(country_counts["launches"].max()), 1)
map_data = country_counts.copy()
map_data["label"] = map_data.apply(
    lambda row: f"{row['country']} · {int(row['launches'])}", axis=1
)

globe_points = [
    {
        "country": str(row["country"]),
        "lat": float(row["latitude"]),
        "lon": float(row["longitude"]),
        "launches": int(row["launches"]),
        "scale": round((int(row["launches"]) / max_launches) ** 0.55, 4),
    }
    for _, row in map_data.iterrows()
]

focus_presets = {
    "Globe": {"lat": 18, "lon": 8, "distance": 4.9},
    "Top hubs": {
        "lat": float(top_site["latitude"]),
        "lon": float(top_site["longitude"]),
        "distance": 4.2,
    },
    "Europe / Asie": {"lat": 35, "lon": 58, "distance": 4.5},
}

theme_config = {
    "dark": {
        "background": "linear-gradient(135deg, #070b1c 0%, #0d1730 48%, #050816 100%)",
        "globe": "#182746",
        "land": "#8fa6cf",
        "countryBorder": "#17233d",
        "coastBorder": "#f8fbff",
        "rim": "#7ea6ff",
        "wire": "#61708f",
        "point": "#9b5cff",
        "pointHot": "#55d6ff",
        "arc": "#8b5cf6",
        "text": "#f8fafc",
        "muted": "#b8c1d9",
        "panel": "rgba(5, 8, 22, 0.72)",
        "border": "rgba(202, 210, 255, 0.16)",
    },
    "light": {
        "background": "linear-gradient(135deg, #f3f7ff 0%, #e6efff 52%, #f8fbff 100%)",
        "globe": "#c7dcf7",
        "land": "#f0f5fb",
        "countryBorder": "#5f7296",
        "coastBorder": "#3f5578",
        "rim": "#6f82dc",
        "wire": "#8fa4ca",
        "point": "#5b46d9",
        "pointHot": "#1287a8",
        "arc": "#6d5dfc",
        "text": "#0f172a",
        "muted": "#475569",
        "panel": "rgba(255, 255, 255, 0.72)",
        "border": "rgba(15, 23, 42, 0.14)",
    },
}[mode]

payload = {
    "points": globe_points,
    "top": globe_points[:12],
    "focus": focus_presets[map_focus],
    "theme": theme_config,
    "maxLaunches": max_launches,
    "period": f"{y_from}-{y_to}",
}

html(
    f"""
    <div id="artemis-globe">
      <canvas id="globe-canvas" aria-label="Globe 3D des sites de lancement"></canvas>
      <div class="globe-overlay">
        <div class="eyebrow">Vue 3D · {map_focus}</div>
        <div class="title">Sites de lancement mondiaux</div>
        <div class="subtitle">{len(globe_points)} sites · {format_number(int(country_counts["launches"].sum()))} lancements · {y_from}-{y_to}</div>
      </div>
      <div id="globe-tooltip"></div>
    </div>
    <script type="importmap">
      {{
        "imports": {{
          "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
          "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/",
          "d3-geo": "https://cdn.jsdelivr.net/npm/d3-geo@3/+esm",
          "topojson-client": "https://cdn.jsdelivr.net/npm/topojson-client@3/+esm"
        }}
      }}
    </script>
    <script type="module">
      import * as THREE from "three";
      import {{ OrbitControls }} from "three/addons/controls/OrbitControls.js";
      import {{ geoEquirectangular, geoPath }} from "d3-geo";
      import {{ feature, mesh }} from "topojson-client";

      const payload = {json.dumps(payload)};
      const root = document.getElementById("artemis-globe");
      const canvas = document.getElementById("globe-canvas");
      const tooltip = document.getElementById("globe-tooltip");
      const theme = payload.theme;

      root.style.setProperty("--globe-bg", theme.background);
      root.style.setProperty("--globe-text", theme.text);
      root.style.setProperty("--globe-muted", theme.muted);
      root.style.setProperty("--globe-panel", theme.panel);
      root.style.setProperty("--globe-border", theme.border);

      const renderer = new THREE.WebGLRenderer({{ canvas, antialias: true, alpha: true }});
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
      camera.position.set(0, 0, payload.focus.distance);

      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.enablePan = false;
      controls.minDistance = 3.4;
      controls.maxDistance = 7.2;
      controls.autoRotate = true;
      controls.autoRotateSpeed = 0.45;

      const globeGroup = new THREE.Group();
      scene.add(globeGroup);

      scene.add(new THREE.AmbientLight(0xffffff, 1.35));
      const keyLight = new THREE.DirectionalLight(0xffffff, 2.2);
      keyLight.position.set(4, 3, 5);
      scene.add(keyLight);
      const frontLight = new THREE.DirectionalLight(0xffffff, "{mode}" === "dark" ? 1.85 : 0.9);
      frontLight.position.set(0, 0, 5);
      camera.add(frontLight);
      scene.add(camera);

      const globeMaterial = new THREE.MeshPhongMaterial({{
          color: new THREE.Color("#ffffff"),
          emissive: new THREE.Color(theme.globe),
          emissiveIntensity: "{mode}" === "dark" ? 0.10 : 0.08,
          shininess: 34,
          transparent: true,
          opacity: "{mode}" === "dark" ? 1 : 0.96,
        }});

      const globe = new THREE.Mesh(
        new THREE.SphereGeometry(2, 128, 128),
        globeMaterial
      );
      globeGroup.add(globe);

      const wire = new THREE.Mesh(
        new THREE.SphereGeometry(2.012, 48, 48),
        new THREE.MeshBasicMaterial({{
          color: new THREE.Color(theme.wire),
          wireframe: true,
          transparent: true,
          opacity: "{mode}" === "dark" ? 0.035 : 0.075,
        }})
      );
      globeGroup.add(wire);

      const rim = new THREE.Mesh(
        new THREE.SphereGeometry(2.035, 96, 96),
        new THREE.MeshBasicMaterial({{
          color: new THREE.Color(theme.rim),
          side: THREE.BackSide,
          transparent: true,
          opacity: "{mode}" === "dark" ? 0.28 : 0.18,
        }})
      );
      rim.scale.setScalar(1.018);
      globeGroup.add(rim);

      async function buildEarthTexture() {{
        const width = 4096;
        const height = 2048;
        const textureCanvas = document.createElement("canvas");
        textureCanvas.width = width;
        textureCanvas.height = height;
        const ctx = textureCanvas.getContext("2d");

        ctx.fillStyle = theme.globe;
        ctx.fillRect(0, 0, width, height);

        const graticuleAlpha = "{mode}" === "dark" ? 0.07 : 0.08;
        ctx.strokeStyle = theme.wire;
        ctx.globalAlpha = graticuleAlpha;
        ctx.lineWidth = 1;
        for (let lon = -180; lon <= 180; lon += 20) {{
          const x = ((lon + 180) / 360) * width;
          ctx.beginPath();
          ctx.moveTo(x, 0);
          ctx.lineTo(x, height);
          ctx.stroke();
        }}
        for (let lat = -80; lat <= 80; lat += 20) {{
          const y = ((90 - lat) / 180) * height;
          ctx.beginPath();
          ctx.moveTo(0, y);
          ctx.lineTo(width, y);
          ctx.stroke();
        }}
        ctx.globalAlpha = 1;

        try {{
          const response = await fetch("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-50m.json");
          const world = await response.json();
          const countries = feature(world, world.objects.countries);
          const borders = mesh(world, world.objects.countries, (a, b) => a !== b);
          const projection = geoEquirectangular()
            .translate([width / 2, height / 2])
            .scale(width / (2 * Math.PI));
          const path = geoPath(projection, ctx);

          ctx.fillStyle = theme.land;
          ctx.strokeStyle = theme.coastBorder;
          ctx.lineWidth = "{mode}" === "dark" ? 0.95 : 1.05;
          ctx.globalAlpha = "{mode}" === "dark" ? 1 : 0.98;
          ctx.beginPath();
          path(countries);
          ctx.fill();
          ctx.stroke();

          ctx.strokeStyle = theme.countryBorder;
          ctx.lineWidth = "{mode}" === "dark" ? 1.05 : 0.95;
          ctx.globalAlpha = "{mode}" === "dark" ? 0.88 : 0.92;
          ctx.beginPath();
          path(borders);
          ctx.stroke();
          ctx.globalAlpha = 1;
        }} catch (error) {{
          console.warn("World atlas texture failed to load", error);
        }}

        const texture = new THREE.CanvasTexture(textureCanvas);
        texture.colorSpace = THREE.SRGBColorSpace;
        texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
        return texture;
      }}

      buildEarthTexture().then((texture) => {{
        globeMaterial.map = texture;
        globeMaterial.needsUpdate = true;
      }});

      function latLonToVector3(lat, lon, radius = 2.045) {{
        const phi = (90 - lat) * Math.PI / 180;
        const theta = (lon + 180) * Math.PI / 180;
        return new THREE.Vector3(
          -radius * Math.sin(phi) * Math.cos(theta),
          radius * Math.cos(phi),
          radius * Math.sin(phi) * Math.sin(theta)
        );
      }}

      function color(hex) {{
        return new THREE.Color(hex);
      }}

      const pointMeshes = [];
      const pointMaterial = new THREE.MeshBasicMaterial({{ color: color(theme.point), transparent: true, opacity: 0.92 }});
      const hotMaterial = new THREE.MeshBasicMaterial({{ color: color(theme.pointHot), transparent: true, opacity: 0.98 }});

      payload.points.forEach((point, index) => {{
        const size = 0.025 + point.scale * 0.07;
        const mesh = new THREE.Mesh(
          new THREE.SphereGeometry(size, 18, 18),
          index < 8 ? hotMaterial.clone() : pointMaterial.clone()
        );
        mesh.position.copy(latLonToVector3(point.lat, point.lon));
        mesh.userData = point;
        globeGroup.add(mesh);
        pointMeshes.push(mesh);
      }});

      function orientTo(lat, lon) {{
        globeGroup.rotation.x = THREE.MathUtils.degToRad(lat * 0.18);
        globeGroup.rotation.y = THREE.MathUtils.degToRad(-lon - 18);
      }}
      orientTo(payload.focus.lat, payload.focus.lon);

      const raycaster = new THREE.Raycaster();
      const pointer = new THREE.Vector2(-2, -2);
      let hovered = null;

      function resize() {{
        const rect = root.getBoundingClientRect();
        renderer.setSize(rect.width, rect.height, false);
        camera.aspect = rect.width / rect.height;
        camera.updateProjectionMatrix();
      }}

      function updateTooltip(event) {{
        const rect = canvas.getBoundingClientRect();
        pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        tooltip.style.left = `${{event.clientX - rect.left + 14}}px`;
        tooltip.style.top = `${{event.clientY - rect.top + 14}}px`;
      }}

      canvas.addEventListener("pointermove", updateTooltip);
      canvas.addEventListener("pointerleave", () => {{
        pointer.set(-2, -2);
        tooltip.style.opacity = "0";
      }});

      function animate() {{
        requestAnimationFrame(animate);
        resize();
        controls.update();

        raycaster.setFromCamera(pointer, camera);
        const hits = raycaster.intersectObjects(pointMeshes, false);
        hovered = hits.length ? hits[0].object : null;
        if (hovered) {{
          const point = hovered.userData;
          tooltip.innerHTML = `<strong>${{point.country}}</strong><br>${{point.launches}} lancements<br><span>Lat ${{point.lat.toFixed(2)}} · Lon ${{point.lon.toFixed(2)}}</span>`;
          tooltip.style.opacity = "1";
        }} else {{
          tooltip.style.opacity = "0";
        }}

        renderer.render(scene, camera);
      }}
      animate();
    </script>
    <style>
      #artemis-globe {{
        position: relative;
        width: 100%;
        height: 640px;
        overflow: hidden;
        border: 1px solid var(--globe-border);
        border-radius: 18px;
        background: var(--globe-bg);
      }}

      #globe-canvas {{
        width: 100%;
        height: 100%;
        display: block;
        cursor: grab;
      }}

      #globe-canvas:active {{
        cursor: grabbing;
      }}

      .globe-overlay {{
        position: absolute;
        left: 24px;
        top: 22px;
        max-width: min(390px, calc(100% - 48px));
        padding: 14px 16px;
        border: 1px solid var(--globe-border);
        border-radius: 14px;
        background: var(--globe-panel);
        color: var(--globe-text);
        backdrop-filter: blur(16px);
        pointer-events: none;
      }}

      .globe-overlay .eyebrow {{
        color: var(--globe-muted);
        font-size: 11px;
        font-weight: 800;
        letter-spacing: .12em;
        text-transform: uppercase;
      }}

      .globe-overlay .title {{
        margin-top: 4px;
        font-size: 22px;
        font-weight: 850;
        line-height: 1.15;
      }}

      .globe-overlay .subtitle {{
        margin-top: 6px;
        color: var(--globe-muted);
        font-size: 13px;
        line-height: 1.35;
      }}

      #globe-tooltip {{
        position: absolute;
        z-index: 5;
        opacity: 0;
        min-width: 150px;
        padding: 10px 12px;
        border: 1px solid var(--globe-border);
        border-radius: 12px;
        background: var(--globe-panel);
        color: var(--globe-text);
        font: 13px Inter, sans-serif;
        pointer-events: none;
        transition: opacity .12s ease;
        backdrop-filter: blur(16px);
      }}

      #globe-tooltip span {{
        color: var(--globe-muted);
      }}

      @media (max-width: 760px) {{
        #artemis-globe {{
          height: 520px;
          border-radius: 14px;
        }}

        .globe-overlay {{
          left: 14px;
          top: 14px;
          padding: 12px 13px;
        }}

        .globe-overlay .title {{
          font-size: 18px;
        }}
      }}
    </style>
    """,
    height=660,
)

# === Insight ===
top3 = country_counts.head(3)
parts = ", ".join(
    f"<strong>{r['country']}</strong> ({int(r['launches'])})"
    for _, r in top3.iterrows()
)
insight(
    f"Sur la période <strong>{y_from}–{y_to}</strong>, le top 3 cumule "
    f"<strong>{int(top3['launches'].sum())}</strong> lancements ({parts})."
)

with st.expander("ℹ️ Lecture business"):
    st.markdown(
        """
        Cette carte met en évidence la **concentration géographique** de l'activité spatiale.
        Quelques sites historiques dominent encore le volume, mais l'émergence de nouveaux sites,
        notamment privés, redessine la carte sur les périodes récentes.

        💡 *Astuce* : comparer **avant / après 2010** met en évidence l'essor de SpaceX et de la Chine.
        """
    )
