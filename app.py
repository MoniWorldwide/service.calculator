import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. KONFIGURATION ---
st.set_page_config(page_title="Deutz-Fahr Intern Beregner", layout="wide")

DATA_MAPPE = "service_ark"
FAST_DIVERSE_TILLAEG = 500.0 
DIVERSE_SØGEORD = ["Testudstyr", "D-Tech", "Hjælpematerialer"]

def find_logo():
    stier = ["logo.png", os.path.join(DATA_MAPPE, "logo.png")]
    for sti in stier:
        if os.path.exists(sti): return sti
    return None

def rens_tal(val):
    """Håndterer danske talformater og retter fejllæsning af punktum (500.000 -> 500)"""
    if pd.isna(val) or str(val).strip() == "": return 0.0
    s = str(val).strip()
    
    # Hvis formatet er 1.250,50
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    # Hvis formatet er 500,00
    elif "," in s:
        s = s.replace(",", ".")
    # Hvis formatet er 500.000 (fejlagtigt læst som tusindtal)
    elif "." in s:
        dele = s.split('.')
        if len(dele[-1]) == 3: # Typisk tegn på tusindtals-separator
            s = s.replace(".", "")
            
    s = "".join(c for c in s if c.isdigit() or c == '.')
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

st.divider()

if not os.path.exists(DATA_MAPPE):
    st.error(f"Mappen '{DATA_MAPPE}' mangler.")
else:
    filer = [f for f in os.listdir(DATA_MAPPE) if f.endswith('.csv')]
    modeller = sorted([f.replace('.csv', '') for f in filer])

    if modeller:
        st.sidebar.header("🔧 Indstillinger")
        model_valg = st.sidebar.selectbox("Vælg Model", modeller)
        timepris = st.sidebar.number_input("Værkstedstimepris (DKK)", value=750, step=25)
        ordretype = st.sidebar.radio("Reservedelspris", ["Brutto", "Haste", "Uge", "Måned"])
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
            
            besk_kol, vare_kol, pris_kol_h = df.columns[0], df.columns[1], df.columns[7]
            int_kols = [c for c in df.columns if "timer" in c.lower()]

            if int_kols:
                valgt_int = st.sidebar.selectbox("Aftale stop-punkt (Timer)", int_kols)
                valgt_t = int("".join(filter(str.isdigit, valgt_int)))
                hist_int = [c for c in int_kols if int("".join(filter(str.isdigit, c))) <= valgt_t]

                tab_admin, tab_kunde = st.tabs(["👨‍🔧 INTERN BEREGNING", "📜 KUNDE KONTRAKT"])

                with tab_admin:
                    st.subheader(f"Kalkulation: {model_valg}")
                    
                    st.write("### 1. Arbejdstimer pr. service")
                    m_arb_row = df[df[besk_kol].astype(str).str.contains('Arbejd', case=False, na=False)]
                    bruger_timer = {}
                    t_cols = st.columns(len(hist_int))
                    for idx, interval in enumerate(hist_int):
                        std_t = rens_tal(m_arb_row[interval].values[0]) if not m_arb_row.empty else 0.0
                        with t_cols[idx]:
                            bruger_timer[interval] = st.number_input(f"Timer {interval}", value=std_t, step=0.5, key=f"t_{interval}")

                    st.write("---")
                    st.write("### 2. Specifikation af indhold")
                    
                    v_idx = df[df[besk_kol].astype(str).str.contains('Væsker', case=False, na=False)].index
                    v_s = v_idx[0] if len(v_idx) > 0 else 9999
                    
                    total_sum = {"res": 0.0, "fluid": 0.0, "div": 0.0, "arb": 0.0}
                    
                    for i in hist_int:
                        mask = df[i].astype(str).str.strip().replace(['nan', 'None', ''], None).notna()
                        current_df = df[mask].copy()
                        
                        is_special_div = current_df[besk_kol].astype(str).str.contains('|'.join(DIVERSE_SØGEORD), case=False, na=False)
                        is_csv_div_row = current_df[besk_kol].astype(str).str.strip().str.lower() == "diverse"
                        
                        special_div_items = current_df[is_special_div].copy()
                        main_items = current_df[~(is_special_div | is_csv_div_row)].copy()

                        with st.expander(f"🔍 Se indhold for {i}"):
                            # Tjek kolonner dynamisk
                            def safe_cols(wanted): return [c for c in wanted if c in df.columns]

                            # --- 1. RESERVEDELE ---
                            st.write("**Reservedele**")
                            res_df = main_items[main_items.index < v_s]
                            st.table(res_df[safe_cols([besk_kol, vare_kol, 'Antal', 'Enhed', ordretype])])
                            
                            # --- 2. VÆSKER ---
                            st.write("**Væsker (Foreslået salgspris fra Univar)**")
                            fluid_df = main_items[main_items.index > v_s].copy()
                            fluid_df['Enhedspris'] = fluid_df[pris_kol_h].apply(rens_tal)
                            fluid_df['Total'] = fluid_df['Enhedspris'] * fluid_df['Antal'].apply(rens_tal)
                            
                            fluid_view = fluid_df[safe_cols([besk_kol, 'Antal', 'Enhed', 'Enhedspris', 'Total'])]
                            st.table(fluid_view.style.format({'Enhedspris': '{:,.2f}', 'Total': '{:,.2f}'}))
                            
                            # --- 3. DIVERSE ---
                            st.write("**Diverse (Priser fra CSV + Fast tillæg)**")
                            div_rows = []
                            for _, row in special_div_items.iterrows():
                                p = rens_tal(row[pris_kol_h])
                                div_rows.append({besk_kol: row[besk_kol], "Antal": row.get('Antal', 1), "Pris": p})
                            # Indsæt det faste diverse tillæg
                            div_rows.append({besk_kol: "Diverse tillæg (fast)", "Antal": 1, "Pris": FAST_DIVERSE_TILLAEG})
                            
                            df_div_vis = pd.DataFrame(div_rows)
                            st.table(df_div_vis.style.format({'Pris': '{:,.2f}'}))

                            # Beregn summer
                            total_sum["res"] += (res_df[ordretype].apply(rens_tal) * res_df['Antal'].apply(rens_tal) * (1 + avance/100)).sum()
                            total_sum["fluid"] += fluid_df['Total'].sum()
                            total_sum["div"] += sum(d["Pris"] for d in div_rows)
                            total_sum["arb"] += (bruger_timer[i] * timepris)

                    total_samlet = sum(total_sum.values())
                    cph = total_samlet / valgt_t if valgt_t > 0 else 0

                    st.write("---")
                    st.write("### 3. Samlet Oversigt")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Reservedele", f"{total_sum['res']:,.2f} kr.")
                    c2.metric("Væsker (Univar)", f"{total_sum['fluid']:,.2f} kr.")
                    c3.metric("Diverse & Arbejde", f"{(total_sum['div'] + total_sum['arb']):,.2f} kr.")
                    c4.metric("TOTAL OMK.", f"{total_samlet:,.2f} kr.")
                    
                    st.success(f"**Resultat: {cph:,.2f} DKK pr. driftstime**")

                with tab_kunde:
                    st.markdown(f"""
                    <div style="padding: 30px; border: 1px solid #ddd; background-color: white; color: black; font-family: Arial;">
                        <h2 style="text-align: center; color: #367c2b;">SERVICEAFTALE</h2>
                        <hr style="border: 1px solid #367c2b;">
                        <p><b>Model:</b> Deutz-Fahr {model_valg} <span style="float:right"><b>Dato:</b> {datetime.now().strftime('%d-%m-%Y')}</span></p>
                        <p><b>Kunde:</b> {kunde_navn} | <b>Stelnummer:</b> {stelnummer}</p>
                        <br>
                        <p>Denne aftale dækker alle planlagte serviceeftersyn frem til <b>{valgt_t} driftstimer</b>.</p>
                        <br>
                        <div style="background-color: #f1f8e9; padding: 25px; border: 1px solid #367c2b; text-align: center;">
                            <span style="font-size: 1.5em; color: #2e7d32;"><b>FAST PRIS PR. DRIFTSTIME: {cph:,.2f} DKK</b></span><br>
                            <small>(Ekskl. moms og brændstof)</small>
                        </div>
                        <br><br><br>
                        <div style="display: flex; justify-content: space-between;">
                            <div style="border-top: 1px solid black; width: 40%; text-align: center;"><br>Forhandler: {forhandler}</div>
                            <div style="border-top: 1px solid black; width: 40%; text-align: center;"><br>Kunde: {kunde_navn}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Fejl ved beregning: {e}")
