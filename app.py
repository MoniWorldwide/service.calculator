import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. KONFIGURATION ---
st.set_page_config(page_title="Deutz-Fahr Intern Beregner", layout="wide")

DATA_MAPPE = "service_ark"
# Din faste instruks: Tilføj altid 500 DKK pr. service interval
FAST_DIVERSE_GEBYR = 500.0 

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

# --- 2. HEADER ---
col_logo, col_title = st.columns([1, 3])
logo_sti = find_logo()
with col_logo:
    if logo_sti: st.image(logo_sti, width=150)
    else: st.subheader("DEUTZ-FAHR")
with col_title:
    st.title("Serviceberegner & Kundekontrakt")
    st.caption("Fuld oversigt over reservedele, væsker og diverse")

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
        ordretype = st.sidebar.radio("Prisliste (Reservedele)", ["Brutto", "Haste", "Uge", "Måned"])
        avance = st.sidebar.slider("Avance på dele (%)", 0, 50, 0)
        
        st.sidebar.divider()
        st.sidebar.header("👤 Kundeinformation")
        forhandler = st.sidebar.text_input("Forhandler", "Indtast navn")
        kunde_navn = st.sidebar.text_input("Kunde")
        stelnummer = st.sidebar.text_input("Stelnummer")

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
            pris_kol_h = df.columns[7] # Kolonne H (Pris for væsker/diverse)
            int_kols = [c for c in df.columns if "timer" in c.lower()]

            if int_kols:
                valgt_int = st.sidebar.selectbox("Aftale stop-punkt (Timer)", int_kols)
                valgt_t = int("".join(filter(str.isdigit, valgt_int)))
                hist_int = [c for c in int_kols if int("".join(filter(str.isdigit, c))) < valgt_t]

                # --- TABS ---
                tab_admin, tab_kunde = st.tabs(["👨‍🔧 INTERN BEREGNING", "📜 KUNDE KONTRAKT"])

                with tab_admin:
                    st.subheader(f"Kalkulation: {model_valg}")
                    
                    # 1. ARBEJDSTIMER
                    st.write("### 1. Arbejdstimer pr. service")
                    m_arb_row = df[df[besk_kol].astype(str).str.contains('Arbejd', case=False, na=False)]
                    bruger_timer = {}
                    
                    t_cols = st.columns(len(hist_int))
                    for idx, interval in enumerate(hist_int):
                        std_t = rens_tal(m_arb_row[interval].values[0]) if not m_arb_row.empty else 0.0
                        with t_cols[idx]:
                            bruger_timer[interval] = st.number_input(f"Timer {interval}", value=std_t, step=0.5, key=f"t_{interval}")

                    # 2. DETALJEREDE TABELLER
                    st.write("---")
                    st.write("### 2. Specifikation af indhold")
                    
                    v_idx = df[df[besk_kol].astype(str).str.contains('Væsker', case=False, na=False)].index
                    v_s = v_idx[0] if len(v_idx) > 0 else 9999
                    
                    t_res, t_vd, t_arb = 0.0, 0.0, 0.0
                    
                    for i in hist_int:
                        mask = df[i].astype(str).replace(['nan', 'None', ''], None).notna()
                        
                        with st.expander(f"🔍 Se fuldt indhold for {i}"):
                            # --- TABEL 1: RESERVEDELE ---
                            st.write("**Reservedele (Filtre o.lign.)**")
                            ønskede_res = [besk_kol, 'Antal', 'Enhed', ordretype]
                            eksist_res = [c for c in ønskede_res if c in df.columns]
                            res_subset = df[mask & (df.index < v_s)][eksist_res]
                            st.table(res_subset)
                            
                            # --- TABEL 2: VÆSKER & DIVERSE ---
                            st.write("**Væsker, Olier & Diverse**")
                            ønskede_vd = [besk_kol, 'Antal', 'Enhed', pris_kol_h]
                            eksist_vd = [c for c in ønskede_vd if c in df.columns]
                            vd_subset = df[mask & (df.index > v_s)][eksist_vd]
                            
                            # Vi fjerner tomme rækker i diverse-tabellen
                            vd_subset = vd_subset[~vd_subset[besk_kol].astype(str).str.strip().str.lower().isin(["none", "nan", ""])]
                            st.table(vd_subset)
                            
                            # --- INFO OM FAST GEBYR ---
                            st.info(f"Hertil lagt: Diverse/Miljøgebyr: {FAST_DIVERSE_GEBYR:,.2f} kr.")

                            # Beregninger til totalen
                            antal_res = res_subset['Antal'].apply(rens_tal) if 'Antal' in res_subset.columns else 0.0
                            pris_res = res_subset[ordretype].apply(rens_tal) if ordretype in res_subset.columns else 0.0
                            curr_res = (pris_res * antal_res * (1 + avance/100)).sum()
                            
                            antal_vd = vd_subset['Antal'].apply(rens_tal) if 'Antal' in vd_subset.columns else 0.0
                            pris_vd = vd_subset[pris_kol_h].apply(rens_tal) if pris_kol_h in vd_subset.columns else 0.0
                            curr_vd = (pris_vd * antal_vd).sum() + FAST_DIVERSE_GEBYR
                            
                            curr_arb = (bruger_timer[i] * timepris)
                            
                            t_res += curr_res
                            t_vd += curr_vd
                            t_arb += curr_arb

                    total_omk = t_res + t_vd + t_arb
                    cph = total_omk / valgt_t if valgt_t > 0 else 0

                    st.write("---")
                    st.write("### 3. Økonomisk Opsummering")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Reservedele", f"{t_res:,.2f} kr.")
                    c2.metric("Væsker & Miljø", f"{t_vd:,.2f} kr.")
                    c3.metric("Arbejdsløn", f"{t_arb:,.2f} kr.")
                    c4.metric("TOTAL OMK.", f"{total_omk:,.2f} kr.")
                    
                    st.success(f"**Resultat: {cph:,.2f} DKK pr. driftstime**")

                with tab_kunde:
                    st.markdown(f"""
                    <div style="padding: 30px; border: 1px solid #ddd; background-color: white; color: black; font-family: Arial;">
                        <h2 style="text-align: center; color: #367c2b;">SERVICEAFTALE</h2>
                        <hr style="border: 1px solid #367c2b;">
                        <p><b>Model:</b> Deutz-Fahr {model_valg} <span style="float:right"><b>Dato:</b> {datetime.now().strftime('%d-%m-%Y')}</span></p>
                        <p><b>Kunde:</b> {kunde_navn} | <b>Stelnummer:</b> {stelnummer}</p>
                        <br>
                        <h4>Aftalens omfang</h4>
                        <p>Denne aftale dækker alle planlagte serviceeftersyn i henhold til fabrikantens forskrifter frem til traktoren har opnået <b>{valgt_t} driftstimer</b>.</p>
                        <p>Serviceintervaller inkluderet: {', '.join(hist_int)}.</p>
                        <br>
                        <div style="background-color: #f1f8e9; padding: 25px; border: 1px solid #367c2b; text-align: center;">
                            <span style="font-size: 1.5em; color: #2e7d32;"><b>FAST PRIS PR. DRIFTSTIME: {cph:,.2f} DKK</b></span><br>
                            <small>(Prisen er ekskl. moms og brændstof)</small>
                        </div>
                        <br><br><br>
                        <div style="display: flex; justify-content: space-between;">
                            <div style="border-top: 1px solid black; width: 40%; text-align: center;"><br>Forhandler: {forhandler}</div>
                            <div style="border-top: 1px solid black; width: 40%; text-align: center;"><br>Kunde: {kunde_navn}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.write("---")
                    st.info("Tip: Brug Ctrl+P for at gemme som PDF eller printe.")

        except Exception as e:
            st.error(f"Der opstod en fejl ved beregningen: {e}")
