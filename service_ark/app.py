import sys
# Her "snyder" vi systemet så underskrifts-modulet tror alt er normalt
try:
    import imghdr
except ImportError:
    from unittest.mock import MagicMock
    mock_imghdr = MagicMock()
    # Vi fortæller Python at 'imghdr' bare er denne tomme boks
    sys.modules["imghdr"] = mock_imghdr

import streamlit as st
import pandas as pd
import os
from datetime import datetime
from streamlit_drawable_canvas import st_canvas

# ... resten af din kode fortsætter herfra

import streamlit as st
import pandas as pd
import os
from datetime import datetime
from streamlit_drawable_canvas import st_canvas

# --- KONFIGURATION AF SIDEN ---
st.set_page_config(page_title="Deutz-Fahr Serviceaftale", layout="wide")

# --- STYRING AF MAPPER OG LOGO ---
DATA_MAPPE = "service_ark"
FAST_DIVERSE_GEBYR = 500.0  # Din faste instruks

def find_logo():
    # Leder efter logoet de to mest sandsynlige steder
    mulige_stier = ["logo.png", os.path.join(DATA_MAPPE, "logo.png")]
    for sti in mulige_stier:
        if os.path.exists(sti):
            return sti
    return None

# --- TOP SEKTION: LOGO OG TITEL ---
col1, col2 = st.columns([1, 3])
logo_sti = find_logo()

with col1:
    if logo_sti:
        st.image(logo_sti, width=200)
    else:
        st.markdown("<h1 style='color: #d32f2f; margin: 0;'>DEUTZ-FAHR</h1>", unsafe_allow_html=True)

with col2:
    st.markdown("<h1 style='margin-bottom: 0; color: #367c2b;'>Serviceberegner & Digital Aftale</h1>", unsafe_allow_html=True)
    st.markdown("<p style='font-style: italic; color: gray;'>Professionel driftsøkonomi og kontraktstyring</p>", unsafe_allow_html=True)

st.divider()

# Find filer
if not os.path.exists(DATA_MAPPE):
    st.error(f"Mappen '{DATA_MAPPE}' blev ikke fundet. Tjek din GitHub-struktur.")
    modeller_raw = []
else:
    filer_i_mappe = [f for f in os.listdir(DATA_MAPPE) if f.endswith('.csv')]
    modeller_raw = sorted([f.replace('.csv', '') for f in filer_i_mappe])

if not modeller_raw:
    st.warning("Ingen CSV-filer fundet i mappen 'service_ark'.")
else:
    # --- SIDEBAR: KONFIGURATION ---
    st.sidebar.header("1. Maskine & Priser")
    model_visning = {f"Deutz-Fahr {m}": m for m in modeller_raw}
    valgt_visningsnavn = st.sidebar.selectbox("Vælg Traktormodel", list(model_visning.keys()))
    model_valg = model_visning[valgt_visningsnavn]
    
    timepris = st.sidebar.number_input("Værkstedstimepris (DKK)", value=750, step=25)
    ordretype = st.sidebar.radio("Pristype for filtre", ["Brutto", "Haste", "Uge", "Måned"])
    avance = st.sidebar.slider("Avance på reservedele (%)", 0, 50, 0)

    st.sidebar.divider()
    st.sidebar.header("2. Kundeinformation")
    forhandler_navn = st.sidebar.text_input("Forhandler", value="Indtast forhandler")
    kunde_navn = st.sidebar.text_input("Kundenavn")
    kunde_adr = st.sidebar.text_input("Adresse / By")
    stelnummer = st.sidebar.text_input("Stelnummer / Chassis nr.")

    valgt_fil = os.path.join(DATA_MAPPE, f"{model_valg}.csv")

    try:
        # Indlæs data
        raw_df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=None)
        header_row_index = 0
        for i, row in raw_df.iterrows():
            if row.astype(str).str.contains('timer', case=False).any():
                header_row_index = i
                break
        
        df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=header_row_index)
        df.columns = [str(c).strip() for c in df.columns]
        beskrivelse_kol = df.columns[0]
        pris_kol_h = df.columns[7]
        interval_kolonner = [c for c in df.columns if "timer" in c.lower()]
        
        def rens_til_tal(val):
            if pd.isna(val): return 0.0
            s = "".join(c for c in str(val) if c.isdigit() or c in ",.")
            s = s.replace(',', '.').strip()
            try: return float(s)
            except: return 0.0

        if interval_kolonner:
            st.sidebar.divider()
            st.sidebar.header("3. Aftale Stop-punkt")
            valgt_interval = st.sidebar.selectbox("Vælg timetal for beregning", interval_kolonner)
            valgt_timer_tal = int("".join(filter(str.isdigit, valgt_interval)))
            
            # Logik: Kun services før stop-punktet medregnes i prisen
            historiske_intervaller = [col for col in interval_kolonner if int("".join(filter(str.isdigit, col))) < valgt_timer_tal]
            
            # --- ARBEJDSTIMER INPUT ---
            bruger_timer = {}
            mask_arbejd = df[beskrivelse_kol].astype(str).str.contains('Arbejd', case=False, na=False)
            if historiske_intervaller:
                with st.sidebar.expander("Ret timer for tidligere services"):
                    for interval in historiske_intervaller:
                        std_hist = rens_til_tal(df[mask_arbejd][interval].values[0]) if mask_arbejd.any() else 0.0
                        t_hist = st.number_input(f"Timer v. {interval}", value=float(std_hist), step=0.5, key=f"hist_{interval}")
                        bruger_timer[interval] = t_hist

            # --- BEREGNING AF AKKUMULERET PRIS ---
            v_idx = df[df[beskrivelse_kol].astype(str).str.contains('Væsker', case=False, na=False)].index
            v_start = v_idx[0] if len(v_idx) > 0 else 9999
            
            tot_res, tot_vd, tot_arb = 0.0, 0.0, 0.0

            for interval in historiske_intervaller:
                m_mask = df[interval].astype(str).replace(['nan', 'None', ''], None).notna()
                # Reservedele
                res_p = df[(df.index < v_start) & m_mask].copy()
                tot_res += (res_p[ordretype].apply(rens_til_tal) * res_p['Antal'].apply(rens_til_tal) * (1 + avance/100)).sum()
                # Væsker & Diverse (inkl. dine faste 500 kr.)
                vd_p = df[(df.index > v_start) & m_mask].copy()
                vd_p = vd_p[~vd_p[beskrivelse_kol].astype(str).str.strip().str.lower().isin(["none", "nan", "", "diverse"])]
                for _, r in vd_p.iterrows():
                    tot_vd += rens_til_tal(r[pris_kol_h]) * rens_til_tal(r['Antal'])
                tot_vd += FAST_DIVERSE_GEBYR # Fast omkostning pr. interval
                # Arbejdsløn
                tot_arb += (bruger_timer[interval] * timepris)

            tot_alt = tot_res + tot_vd + tot_arb
            pris_pr_t = tot_alt / valgt_timer_tal if valgt_timer_tal > 0 else 0

            # --- VISNING (TABS) ---
            tab1, tab2 = st.tabs(["📊 Økonomisk Overblik", "✍️ Digital Serviceaftale"])

            with tab1:
                st.subheader(f"Beregning: 0 - {valgt_timer_tal} timer")
                st.markdown(f"Herunder ses de akkumulerede omkostninger. Bemærk at det valgte {valgt_interval} service **ikke** er medregnet i timeprisen.")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Reservedele total", f"{tot_res:,.2f} DKK")
                c2.metric("Væsker/Diverse total", f"{tot_vd:,.2f} DKK")
                c3.metric("Arbejdsløn total", f"{tot_arb:,.2f} DKK")

                st.markdown(f"<div style='margin-top:20px; border: 2px solid #367c2b; padding: 20px; border-radius: 10px; text-align: center; background-color: #f9f9f9;'>"
                            f"<span style='font-size: 1.2em; font-weight: bold;'>REEL PRIS PR. DRIFTSTIME: </span>"
                            f"<span style='font-size: 2.2em; font-weight: bold; color: #367c2b;'>{pris_pr_t:,.2f} DKK/t</span>"
                            f"</div>", unsafe_allow_html=True)

            with tab2:
                # KONTRAKT LAYOUT
                st.markdown(f"""
                <div style="padding: 30px; border: 1px solid #ccc; background-color: white; color: black; font-family: Arial;">
                    <h2 style="text-align: center; color: #367c2b;">SERVICEAFTALE</h2>
                    <table style="width: 100%;">
                        <tr><td><b>Forhandler:</b> {forhandler_navn}</td><td><b>Kunde:</b> {kunde_navn}</td></tr>
                        <tr><td><b>Model:</b> {valgt_visningsnavn}</td><td><b>Stelnummer:</b> {stelnummer}</td></tr>
                    </table>
                    <hr>
                    <p>Denne aftale omfatter alle foreskrevne serviceintervaller frem til traktoren runder <b>{valgt_timer_tal} timer</b>.</p>
                    <p><b>Aftalt pris pr. driftstime: {pris_pr_t:,.2f} DKK (Ekskl. moms)</b></p>
                </div>
                """, unsafe_allow_html=True)
                
                st.write("### Underskrifter")
                col_s1, col_s2 = st.columns(2)
                
                with col_s1:
                    st.caption(f"Forhandler: {forhandler_navn}")
                    st_canvas(fill_color="rgba(255, 255, 255, 0)", stroke_width=2, stroke_color="black", 
                              background_color="#eee", height=150, width=300, drawing_mode="freedraw", key="canvas1")
                
                with col_s2:
                    st.caption(f"Kunde: {kunde_navn}")
                    st_canvas(fill_color="rgba(255, 255, 255, 0)", stroke_width=2, stroke_color="blue", 
                              background_color="#eee", height=150, width=300, drawing_mode="freedraw", key="canvas2")
                
                if st.button("Udfør Aftale"):
                    st.balloons()
                    st.success("Aftalen er bekræftet digitalt.")

    except Exception as e:
        st.error(f"Der opstod en fejl i databehandlingen: {e}")

