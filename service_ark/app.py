import streamlit as st
import pandas as pd
import os

# Konfiguration af siden
st.set_page_config(page_title="Deutz-Fahr Serviceberegner", layout="wide")

# --- STYRING AF MAPPER ---
DATA_MAPPE = "service_ark"

# --- TOP SEKTION: LOGO OG TITEL ---
col1, col2 = st.columns([1, 3])
with col1:
    logo_path = os.path.join(DATA_MAPPE, "logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=200)
    else:
        st.markdown("<h1 style='color: #d32f2f; margin: 0;'>DEUTZ-FAHR</h1>", unsafe_allow_html=True)

with col2:
    st.markdown("<h1 style='margin-bottom: 0; color: #367c2b;'>Serviceberegner</h1>", unsafe_allow_html=True)
    st.markdown("<p style='font-style: italic; color: gray;'>Professionelt overblik over serviceomkostninger</p>", unsafe_allow_html=True)

st.divider()

# Find filer i service_ark mappen
if not os.path.exists(DATA_MAPPE):
    st.error(f"Mappen '{DATA_MAPPE}' blev ikke fundet.")
    modeller_raw = []
else:
    filer_i_mappe = [f for f in os.listdir(DATA_MAPPE) if f.endswith('.csv')]
    modeller_raw = sorted([f.replace('.csv', '') for f in filer_i_mappe])

if not modeller_raw:
    st.warning("Ingen CSV-filer fundet i 'service_ark' mappen.")
else:
    # --- SIDEBAR ---
    st.sidebar.header("Indstillinger")
    
    model_visning = {f"Deutz-Fahr {m}": m for m in modeller_raw}
    valgt_visningsnavn = st.sidebar.selectbox("Vælg Traktormodel", list(model_visning.keys()))
    model_valg = model_visning[valgt_visningsnavn]
    
    st.sidebar.divider()
    timepris = st.sidebar.number_input("Værkstedstimepris (DKK)", value=750, step=25)
    ordretype = st.sidebar.radio("Pristype for filtre", ["Brutto", "Haste", "Uge", "Måned"])
    avance = st.sidebar.slider("Avance på reservedele (%)", 0, 50, 0)

    valgt_fil = os.path.join(DATA_MAPPE, f"{model_valg}.csv")

    try:
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
        
        if interval_kolonner:
            valgt_interval = st.selectbox("Vælg serviceinterval", interval_kolonner)
            
            def rens_til_tal(val):
                if pd.isna(val): return 0.0
                s = "".join(c for c in str(val) if c.isdigit() or c in ",.")
                s = s.replace(',', '.').strip()
                try: return float(s)
                except: return 0.0

            # Find sektioner
            v_idx = df[df[beskrivelse_kol].astype(str).str.contains('Væsker', case=False, na=False)].index
            d_idx = df[df[beskrivelse_kol].astype(str).str.contains('Diverse', case=False, na=False)].index
            v_start = v_idx[0] if len(v_idx) > 0 else 9999
            d_start = d_idx[0] if len(d_idx) > 0 else 9999

            # Markering tjek: Er cellen i interval-kolonnen udfyldt?
            df['markeret'] = df[valgt_interval].astype(str).replace(['nan', 'None', ''], None).notna()
            
            # --- SEKTIONS-OPDELING (Nu alle afhængige af 'markeret') ---
            
            # 1. Filtre
            hoved = df[(df.index < v_start) & (df['markeret'])].copy()
            hoved = hoved[~hoved[beskrivelse_kol].astype(str).str.strip().str.lower().isin(["none", "nan", ""])]
            
            # 2. Væsker
            vaesker = df[(df.index > v_start) & (df.index < d_start) & (df['markeret'])].copy()
            vaesker = vaesker[~vaesker[beskrivelse_kol].astype(str).str.strip().str.lower().isin(["none", "nan", ""])]
            
            # 3. Diverse (Dynamisk tjek på intervallet)
            diverse = df[(df.index >= d_start) & (df['markeret'])].copy()
            diverse = diverse[~diverse[beskrivelse_kol].astype(str).str.strip().str.lower().isin(["none", "nan", "", "diverse"])]
            # Sikr at der er en pris før vi tager den med
            diverse['pris_tjek'] = diverse[pris_kol_h].apply(rens_til_tal)
            diverse = diverse[diverse['pris_tjek'] > 0].copy()

            # --- ARBEJDSTIMER ---
            mask_arbejd = df[beskrivelse_kol].astype(str).str.contains('Arbejd', case=False, na=False)
            vejledende_timer = 0.0
            if mask_arbejd.any():
                vejledende_timer = rens_til_tal(df[mask_arbejd][valgt_interval].values[0])

            st.sidebar.divider()
            valgte_timer = st.sidebar.number_input(f"Arbejdstimer ({valgt_interval})", value=float(vejledende_timer), step=0.5)
            arbejd_total = valgte_timer * timepris

            # --- BEREGNINGER ---
            def apply_calc(data, kilde_kol, mult=1.0):
                if data.empty: return data
                data = data.copy()
                data['Enhed_Tal'] = data[kilde_kol].apply(rens_til_tal)
                data['Antal_Tal'] = data['Antal'].apply(rens_til_tal)
                data['Total_Tal'] = data['Antal_Tal'] * data['Enhed_Tal'] * mult
                return data

            hoved = apply_calc(hoved, ordretype, (1 + avance/100))
            vaesker = apply_calc(vaesker, pris_kol_h)
            diverse = apply_calc(diverse, pris_kol_h)

            # --- VISNING ---
            st.subheader(f"{valgt_visningsnavn} - {valgt_interval}")

            if not hoved.empty:
                st.markdown("<h4 style='color: #367c2b;'>🛠️ Filtre og reservedele</h4>", unsafe_allow_html=True)
                st.dataframe(hoved[[beskrivelse_kol, 'Reservedelsnr.', 'Enhed_Tal', 'Antal', 'Total_Tal']].rename(columns={'Enhed_Tal': 'Enhedspris', 'Total_Tal': 'Total (inkl. avance)'}), use_container_width=True, hide_index=True)

            if not vaesker.empty:
                st.markdown("<h4 style='color: #367c2b;'>🛢️ Væsker</h4>", unsafe_allow_html=True)
                st.info("Prisen på væsker er en foreslået salgspris fra Univar. Det anbefales at kontakte Univar for den dagsaktuelle pris.")
                st.dataframe(vaesker[[beskrivelse_kol, 'Enhed_Tal', 'Antal', 'Total_Tal']].rename(columns={'Enhed_Tal': 'Vejl. Univar pris', 'Total_Tal': 'Total'}), use_container_width=True, hide_index=True)

            if not diverse.empty:
                st.markdown("<h4 style='color: #367c2b;'>📦 Diverse</h4>", unsafe_allow_html=True)
                st.dataframe(diverse[[beskrivelse_kol, 'Enhed_Tal', 'Antal', 'Total_Tal']].rename(columns={'Enhed_Tal': 'Vejl. pris', 'Total_Tal': 'Total'}), use_container_width=True, hide_index=True)

            # --- TOTALER ---
            st.divider()
            sum_reservedele = hoved['Total_Tal'].sum() if not hoved.empty else 0
            sum_v_d = (vaesker['Total_Tal'].sum() if not vaesker.empty else 0) + (diverse['Total_Tal'].sum() if not diverse.empty else 0)
            total_alt = sum_reservedele + sum_v_d + arbejd_total
            
            try:
                interval_tal = float("".join(filter(str.isdigit, valgt_interval)))
                pris_pr_time = total_alt / interval_tal if interval_tal > 0 else 0
            except:
                pris_pr_time = 0

            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("Sum reservedele", f"{sum_reservedele:,.2f} DKK")
            with c2: st.metric("Væsker & diverse", f"{sum_v_d:,.2f} DKK")
            with c3: st.metric("Arbejdsløn", f"{arbejd_total:,.2f} DKK")
            with c4: 
                st.markdown(f"<div style='background-color: #367c2b; padding: 10px; border-radius: 5px; color: white; text-align: center;'>"
                            f"<small>SAMLET TOTAL (Ekskl. moms)</small><br><strong><big>{total_alt:,.2f} DKK</big></strong></div>", unsafe_allow_html=True)

            # --- DRIFTSØKONOMI ---
            st.markdown("<br>", unsafe_allow_html=True)
            col_info, col_box = st.columns([2, 1])
            with col_info:
                st.markdown(f"### Driftsøkonomi")
                st.write(f"For at give et overblik over maskinens driftsomkostninger er den samlede pris herunder fordelt ud på serviceintervallets varighed (**{valgt_interval}**).")
                st.write(f"Dette tal repræsenterer den gennemsnitlige udgift til service pr. driftstime i denne periode.")
            
            with col_box:
                st.markdown(f"<div style='border: 2px solid #367c2b; padding: 15px; border-radius: 10px; text-align: center; background-color: #f9f9f9;'>"
                            f"<span style='color: #555; font-size: 0.9em; font-weight: bold;'>SERVICEOMKOSTNING PR. DRIFTSTIME</span><br>"
                            f"<span style='font-size: 1.6em; font-weight: bold; color: #367c2b;'>{pris_pr_time:,.2f} DKK/t</span>"
                            f"</div>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Fejl ved indlæsning af data: {e}")
