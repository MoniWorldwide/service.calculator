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
    """
    Ekstremt robust tal-rensning. 
    Håndterer både '500.00', '500,00' og '1.250,00'.
    """
    if pd.isna(val) or str(val).strip() == "": return 0.0
    s = str(val).strip()
    
    # Hvis formatet er dansk (1.250,50), fjern punktum og skift komma til punktum
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    # Hvis der kun er komma (500,00), skift til punktum
    elif "," in s:
        s = s.replace(",", ".")
    # Hvis der kun er punktum, og der er 3 cifre efter det (500.000), 
    # så er det en tusindtals-fejl fra CSV-læsningen. Fjern det.
    elif "." in s:
        dele = s.split('.')
        if len(dele[-1]) == 3:
            s = s.replace(".", "")
            
    # Rens alt andet end tal og punktum
    s = "".join(c for c in s if c.isdigit() or c == '.')
    try:
        return float(s)
    except:
        return 0.0

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
        # SIDEBAR
        st.sidebar.header("🔧 Indstillinger")
        model_valg = st.sidebar.selectbox("Vælg Model", modeller)
        timepris = st.sidebar.number_input("Værkstedstimepris (DKK)", value=750, step=25)
        ordretype = st.sidebar.radio("Reservedelspris", ["Brutto", "Haste", "Uge", "Måned"])
        avance = st.sidebar.slider("Avance på dele (%)", 0, 50, 0)

        valgt_fil = os.path.join(DATA_MAPPE, f"{model_valg}.csv")
        try:
            # Læs CSV - vi finder overskriftsrækken dynamisk
            df_raw = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=None)
            h_idx = 0
            for i, row in df_raw.iterrows():
                if row.astype(str).str.contains('timer', case=False).any():
                    h_idx = i
                    break
            
            df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=h_idx)
            df.columns = [str(c).strip() for c in df.columns]
            
            besk_kol = df.columns[0]
            vare_kol = df.columns[1] 
            pris_kol_h = df.columns[7] # Kolonne H (Univar priser)
            int_kols = [c for c in df.columns if "timer" in c.lower()]

            if int_kols:
                valgt_int = st.sidebar.selectbox("Aftale stop-punkt (Timer)", int_kols)
                valgt_t = int("".join(filter(str.isdigit, valgt_int)))
                hist_int = [c for c in int_kols if int("".join(filter(str.isdigit, c))) <= valgt_t]

                tab_admin, tab_kunde = st.tabs(["👨‍🔧 INTERN BEREGNING", "📜 KUNDE KONTRAKT"])

                with tab_admin:
                    st.subheader(f"Kalkulation: {model_valg}")
                    
                    # 1. Arbejdstimer
                    m_arb_row = df[df[besk_kol].astype(str).str.contains('Arbejd', case=False, na=False)]
                    bruger_timer = {}
                    t_cols = st.columns(len(hist_int))
                    for idx, interval in enumerate(hist_int):
                        std_t = rens_tal(m_arb_row[interval].values[0]) if not m_arb_row.empty else 0.0
                        with t_cols[idx]:
                            bruger_timer[interval] = st.number_input(f"Timer {interval}", value=std_t, step=0.5, key=f"t_{interval}")

                    # 2. Specifikation
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
                            # --- RESERVEDELE ---
                            st.write("**Reservedele**")
                            res_df = main_items[main_items.index < v_s]
                            res_cols = [c for c in [besk_kol, vare_kol, 'Antal', 'Enhed', ordretype] if c in df.columns]
                            st.table(res_df[res_cols])
                            
                            # --- VÆSKER (MED ENHEDSPRIS & TOTAL) ---
                            st.write("**Væsker**")
                            fluid_df = main_items[main_items.index > v_s].copy()
                            # Beregn priser specifikt for visning
                            fluid_df['Enhedspris'] = fluid_df[pris_kol_h].apply(rens_tal)
                            fluid_df['Totalpris'] = fluid_df['Enhedspris'] * fluid_df['Antal'].apply(rens_tal)
                            
                            fluid_view_cols = [c for c in [besk_kol, 'Antal', 'Enhed', 'Enhedspris', 'Totalpris'] if c in fluid_df.columns or c in ['Enhedspris', 'Totalpris']]
                            st.table(fluid_df[fluid_view_cols].style.format({'Enhedspris': '{:,.2f}', 'Totalpris': '{:,.2f}'}))
                            
                            # --- DIVERSE ---
                            st.write("**Diverse**")
                            div_rows = []
                            for _, row in special_div_items.iterrows():
                                p = rens_tal(row[pris_kol_h])
                                div_rows.append({besk_kol: row[besk_kol], "Antal": row.get('Antal', 1), "Pris": p})
                            # Tilføj dit faste tillæg på 500 kr.
                            div_rows.append({besk_kol: "Diverse tillæg (fast)", "Antal": 1, "Pris": FAST_DIVERSE_TILLAEG})
                            
                            df_div_vis = pd.DataFrame(div_rows)
                            st.table(df_div_vis.style.format({'Pris': '{:,.2f}'}))

                            # Beregn summer
                            c_res = (res_df[ordretype].apply(rens_tal) * res_df['Antal'].apply(rens_tal) * (1 + avance/100)).sum()
                            c_fluid = fluid_df['Totalpris'].sum()
                            c_div = sum(d['Pris'] for d in div_rows)
                            
                            total_sum["res"] += c_res
                            total_sum["fluid"] += c_fluid
                            total_sum["div"] += c_div
                            total_sum["arb"] += (bruger_timer[i] * timepris)

                    total_samlet = sum(total_sum.values())
                    cph = total_samlet / valgt_t if valgt_t > 0 else 0

                    st.write("---")
                    st.write("### 3. Samlet Oversigt")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Reservedele", f"{total_sum['res']:,.2f} kr.")
                    c2.metric("Væsker", f"{total_sum['fluid']:,.2f} kr.")
                    c3.metric("Diverse & Arbejde", f"{(total_sum['div'] + total_sum['arb']):,.2f} kr.")
                    c4.metric("TOTAL OMK.", f"{total_samlet:,.2f} kr.")
                    
                    st.success(f"**Resultat: {cph:,.2f} DKK pr. driftstime**")

                with tab_kunde:
                    # (Kundekontrakt layout...)
                    st.subheader("Kundekontrakt")
                    st.info("Her genereres kundens kopi baseret på ovenstående beregning.")

        except Exception as e:
            st.error(f"Fejl ved beregning: {e}")
