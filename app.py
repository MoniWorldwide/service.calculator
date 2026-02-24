import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- KONFIGURATION ---
st.set_page_config(page_title="Deutz-Fahr Intern Beregner", layout="wide")

DATA_MAPPE = "service_ark"
FAST_DIVERSE_GEBYR = 500.0  # Din faste instruks (Diverse/Miljø pr. service)

def find_logo():
    stier = ["logo.png", os.path.join(DATA_MAPPE, "logo.png")]
    for sti in stier:
        if os.path.exists(sti): return sti
    return None

def rens_tal(val):
    if pd.isna(val): return 0.0
    s = "".join(c for c in str(val) if c.isdigit() or c in ",.")
    s = s.replace(',', '.').strip()
    try: return float(s)
    except: return 0.0

# --- HEADER ---
col_logo, col_title = st.columns([1, 3])
logo_sti = find_logo()
with col_logo:
    if logo_sti: st.image(logo_sti, width=150)
    else: st.subheader("DEUTZ-FAHR")
with col_title:
    st.title("Intern Serviceberegner & Kundekontrakt")

st.divider()

if not os.path.exists(DATA_MAPPE):
    st.error(f"Mappen '{DATA_MAPPE}' mangler på GitHub.")
else:
    filer = [f for f in os.listdir(DATA_MAPPE) if f.endswith('.csv')]
    modeller = sorted([f.replace('.csv', '') for f in filer])

    if modeller:
        # --- SIDEBAR (FORHANDLERENS KONTROL) ---
        st.sidebar.header("🔧 Forhandler Indstillinger")
        model_valg = st.sidebar.selectbox("Vælg Model", modeller)
        timepris = st.sidebar.number_input("Værkstedstimepris (DKK)", value=750, step=25)
        ordretype = st.sidebar.radio("Reservedelspris", ["Brutto", "Haste", "Uge", "Måned"])
        avance = st.sidebar.slider("Avance på dele (%)", 0, 50, 0)
        
        st.sidebar.divider()
        st.sidebar.header("👤 Kundeinformation")
        forhandler = st.sidebar.text_input("Forhandler", "Indtast navn")
        kunde_navn = st.sidebar.text_input("Kunde")
        stelnummer = st.sidebar.text_input("Stelnummer")

        # Indlæs data
        valgt_fil = os.path.join(DATA_MAPPE, f"{model_valg}.csv")
        try:
            df_raw = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=None)
            h_idx = 0
            for i, row in df_raw.iterrows():
                if row.astype(str).str.contains('timer', case=False).any():
                    h_idx = i
                    break
            
            df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=h_idx)
            df.columns = [str(c).strip() for c in df.columns]
            
            besk_kol = df.columns[0]
            pris_kol_h = df.columns[7]
            int_kols = [c for c in df.columns if "timer" in c.lower()]

            if int_kols:
                valgt_int = st.sidebar.selectbox("Aftale stop-punkt (Timer)", int_kols)
                valgt_t = int("".join(filter(str.isdigit, valgt_int)))
                hist_int = [c for c in int_kols if int("".join(filter(str.isdigit, c))) < valgt_t]

                # --- TABS: INTERN VS KUNDE ---
                tab_admin, tab_kunde = st.tabs(["👨‍🔧 INTERN BEREGNING (Forhandler)", "📜 KUNDE KONTRAKT"])

                with tab_admin:
                    st.subheader(f"Intern Kalkulation for {model_valg}")
                    
                    # 1. ARBEJDSTIMER (INTERAKTIV)
                    st.write("### 1. Tilpas Arbejdstimer")
                    st.info("Her kan du rette timerne for hver service. Timeprisen opdateres automatisk.")
                    m_arb_row = df[df[besk_kol].astype(str).str.contains('Arbejd', case=False, na=False)]
                    bruger_timer = {}
                    
                    t_cols = st.columns(len(hist_int))
                    for idx, interval in enumerate(hist_int):
                        std_t = rens_tal(m_arb_row[interval].values[0]) if not m_arb_row.empty else 0.0
                        with t_cols[idx]:
                            bruger_timer[interval] = st.number_input(f"Timer {interval}", value=std_t, step=0.5, key=f"t_{interval}")

                    # 2. TABELLER OG BEREGNING
                    st.write("---")
                    st.write("### 2. Detaljeret oversigt over dele og væsker")
                    
                    v_idx = df[df[besk_kol].astype(str).str.contains('Væsker', case=False, na=False)].index
                    v_s = v_idx[0] if len(v_idx) > 0 else 9999
                    
                    t_res, t_vd, t_arb = 0.0, 0.0, 0.0
                    
                    for i in hist_int:
                        mask = df[i].astype(str).replace(['nan', 'None', ''], None).notna()
                        
                        with st.expander(f"📦 Se dele inkluderet i {i}"):
                            # Tabel over reservedele
                            res_subset = df[mask & (df.index < v_s)][[besk_kol, 'Antal', 'Enhed', ordretype]]
                            st.table(res_subset)
                            
                            # Beregning for dette interval
                            curr_res = (res_subset[ordretype].apply(rens_tal) * res_subset['Antal'].apply(rens_tal) * (1 + avance/100)).sum()
                            
                            vd_df = df[(df.index > v_s) & mask]
                            vd_df = vd_df[~vd_df[besk_kol].astype(str).str.strip().str.lower().isin(["none", "nan", "", "diverse"])]
                            curr_vd = (vd_df[pris_kol_h].apply(rens_tal) * vd_df['Antal'].apply(rens_tal)).sum()
                            curr_vd += FAST_DIVERSE_GEBYR # Miljø/Diverse post
                            
                            curr_arb = (bruger_timer[i] * timepris)
                            
                            st.write(f"**Omkostning v. {i}:** Dele: {curr_res:,.2f} | Væsker: {curr_vd:,.2f} | Arbejde: {curr_arb:,.2f}")
                            
                            t_res += curr_res
                            t_vd += curr_vd
                            t_arb += curr_arb

                    total_omk = t_res + t_vd + t_arb
                    cph = total_omk / valgt_t if valgt_t > 0 else 0

                    st.write("---")
                    st.write("### 3. Samlet Intern Kalkulation")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Reservedele", f"{t_res:,.2f} kr.")
                    c2.metric("Væsker & Miljø", f"{t_vd:,.2f} kr.")
                    c3.metric("Arbejdsløn", f"{t_arb:,.2f} kr.")
                    c4.metric("TOTAL", f"{total_omk:,.2f} kr.")
                    
                    st.success(f"**Anbefalet pris til kunde: {cph:,.2f} DKK / driftstime**")

                with tab_kunde:
                    st.markdown(f"""
                    <div style="padding: 35px; border: 1px solid #ccc; background-color: white; color: black; font-family: sans-serif;">
                        <h2 style="text-align: center; color: #367c2b;">SERVICEAFTALE</h2>
                        <hr style="border: 1px solid #367c2b;">
                        <p><b>Model:</b> Deutz-Fahr {model_valg} <span style="float:right"><b>Dato:</b> {datetime.now().strftime('%d-%m-%Y')}</span></p>
                        <p><b>Kunde:</b> {kunde_navn} | <b>Stelnummer:</b> {stelnummer}</p>
                        <br>
                        <h4>Aftalens omfang</h4>
                        <p>Aftalen omfatter alle planlagte serviceintervaller frem til traktoren har kørt <b>{valgt_t} timer</b>.</p>
                        <p>Inkluderede intervaller: {', '.join(hist_int)}.</p>
                        <br>
                        <div style="background-color: #f1f8e9; padding: 25px; border: 1px solid #367c2b; text-align: center;">
                            <span style="font-size: 1.6em; color: #2e7d32;"><b>FAST PRIS PR. DRIFTSTIME: {cph:,.2f} DKK</b></span><br>
                            <small>(Alle priser er ekskl. moms og brændstof)</small>
                        </div>
                        <br><br><br>
                        <div style="display: flex; justify-content: space-between; margin-top: 50px;">
                            <div style="border-top: 1px solid black; width: 40%; text-align: center;"><br>Forhandler: {forhandler}</div>
                            <div style="border-top: 1px solid black; width: 40%; text-align: center;"><br>Kunde: {kunde_navn}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.write("---")
                    st.info("Tip: Brug Ctrl+P for at printe eller gemme aftalen som PDF til kunden.")

        except Exception as e:
            st.error(f"Der opstod en fejl ved beregningen: {e}")
