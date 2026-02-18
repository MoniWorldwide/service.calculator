import streamlit as st
import pandas as pd
import os

# Konfiguration af siden
st.set_page_config(page_title="Deutz-Fahr Serviceberegner", layout="wide")

# --- STYRING AF MAPPER OG KONSTANTER ---
DATA_MAPPE = "service_ark"
FAST_DIVERSE_GEBYR = 500.0  # Din faste omkostning pr. serviceinterval

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
    st.markdown("<p style='font-style: italic; color: gray;'>Total driftsøkonomi og serviceoverblik</p>", unsafe_allow_html=True)

st.divider()

# Find filer
if not os.path.exists(DATA_MAPPE):
    st.error(f"Mappen '{DATA_MAPPE}' blev ikke fundet.")
    modeller_raw = []
else:
    filer_i_mappe = [f for f in os.listdir(DATA_MAPPE) if f.endswith('.csv')]
    modeller_raw = sorted([f.replace('.csv', '') for f in filer_i_mappe])

if not modeller_raw:
    st.warning("Ingen CSV-filer fundet.")
else:
    # --- SIDEBAR INDSTILLINGER ---
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
            valgt_interval = st.selectbox("Vælg serviceinterval", interval_kolonner)
            
            # --- ARBEJDSTIMER INPUT (SIDEBAR) ---
            mask_arbejd = df[beskrivelse_kol].astype(str).str.contains('Arbejd', case=False, na=False)
            vejledende_timer = 0.0
            if mask_arbejd.any():
                vejledende_timer = rens_til_tal(df[mask_arbejd][valgt_interval].values[0])
            
            st.sidebar.divider()
            valgte_arbejdstimer = st.sidebar.number_input(f"Arbejdstimer for {valgt_interval}", value=float(vejledende_timer), step=0.5)

            # --- AKKUMULERET BEREGNING ---
            try:
                valgt_timer_tal = int("".join(filter(str.isdigit, valgt_interval)))
                forudgaaende_intervaller = []
                for col in interval_kolonner:
                    col_timer = int("".join(filter(str.isdigit, col)))
                    if col_timer <= valgt_timer_tal:
                        forudgaaende_intervaller.append(col)
            except:
                valgt_timer_tal = 1
                forudgaaende_intervaller = [valgt_interval]

            v_idx = df[df[beskrivelse_kol].astype(str).str.contains('Væsker', case=False, na=False)].index
            v_start = v_idx[0] if len(v_idx) > 0 else 9999

            total_akkumuleret_res = 0.0
            total_akkumuleret_vd = 0.0
            total_akkumuleret_arbejd = 0.0

            for interval in forudgaaende_intervaller:
                m_mask = df[interval].astype(str).replace(['nan', 'None', ''], None).notna()
                
                # Reservedele
                res_part = df[(df.index < v_start) & m_mask].copy()
                total_akkumuleret_res += (res_part[ordretype].apply(rens_til_tal) * res_part['Antal'].apply(rens_til_tal) * (1 + avance/100)).sum()
                
                # Væsker & Excel-diverse
                vd_part = df[(df.index > v_start) & m_mask].copy()
                vd_part = vd_part[~vd_part[beskrivelse_kol].astype(str).str.strip().str.lower().isin(["none", "nan", "", "diverse"])]
                total_akkumuleret_vd += (vd_part[pris_kol_h].apply(rens_til_tal) * vd_part['Antal'].apply(rens_til_tal)).sum()
                
                # Arbejdsløn (Brug brugerinput for det valgte interval, ellers Excel-tal for de forudgående)
                if interval == valgt_interval:
                    total_akkumuleret_arbejd += (valgte_arbejdstimer * timepris)
                else:
                    if mask_arbejd.any():
                        t_timer = rens_til_tal(df[mask_arbejd][interval].values[0])
                        total_akkumuleret_arbejd += (t_timer * timepris)

            # Læg de faste 500 kr. pr. interval til
            total_akkumuleret_vd += (len(forudgaaende_intervaller) * FAST_DIVERSE_GEBYR)
            
            total_akkumuleret_alt = total_akkumuleret_res + total_akkumuleret_vd + total_akkumuleret_arbejd
            pris_pr_time_akkumuleret = total_akkumuleret_alt / valgt_timer_tal if valgt_timer_tal > 0 else 0

            # --- VISNING ---
            st.subheader(f"{valgt_visningsnavn} - Detaljer for {valgt_interval}")
            
            # Tabeller (Kun for det valgte interval)
            df['markeret'] = df[valgt_interval].astype(str).replace(['nan', 'None', ''], None).notna()
            hoved = df[(df.index < v_start) & (df['markeret'])].copy()
            vaesker = df[(df.index > v_start) & (df['markeret'])].copy()
            vaesker = vaesker[~vaesker[beskrivelse_kol].astype(str).str.strip().str.lower().isin(["none", "nan", "", "diverse"])]

            if not hoved[~hoved[beskrivelse_kol].astype(str).str.strip().str.lower().isin(["none", "nan", ""])].empty:
                st.markdown("<h4 style='color: #367c2b;'>🛠️ Filtre og reservedele</h4>", unsafe_allow_html=True)
                h_disp = hoved.copy()
                h_disp['Enhed_Tal'] = h_disp[ordretype].apply(rens_til_tal) * (1 + avance/100)
                h_disp['Total_Tal'] = h_disp['Enhed_Tal'] * h_disp['Antal'].apply(rens_til_tal)
                st.dataframe(h_disp[[beskrivelse_kol, 'Reservedelsnr.', 'Enhed_Tal', 'Antal', 'Total_Tal']].rename(columns={'Enhed_Tal': 'Enhedspris', 'Total_Tal': 'Total'}), use_container_width=True, hide_index=True)

            if not vaesker.empty:
                st.markdown("<h4 style='color: #367c2b;'>🛢️ Væsker</h4>", unsafe_allow_html=True)
                st.info("Prisen på væsker er en foreslået salgspris fra Univar. Det anbefales at kontakte Univar for den dagsaktuelle pris.")
                v_disp = vaesker.copy()
                v_disp['Enhed_Tal'] = v_disp[pris_kol_h].apply(rens_til_tal)
                v_disp['Total_Tal'] = v_disp['Enhed_Tal'] * v_disp['Antal'].apply(rens_til_tal)
                st.dataframe(v_disp[[beskrivelse_kol, 'Enhed_Tal', 'Antal', 'Total_Tal']].rename(columns={'Enhed_Tal': 'Vejl. Univar pris', 'Total_Tal': 'Total'}), use_container_width=True, hide_index=True)

            st.markdown("<h4 style='color: #367c2b;'>📦 Diverse</h4>", unsafe_allow_html=True)
            st.dataframe(pd.DataFrame({beskrivelse_kol: ["Fast diverse omkostning"], 'Pris': [FAST_DIVERSE_GEBYR], 'Antal': [1.0], 'Total': [FAST_DIVERSE_GEBYR]}), use_container_width=True, hide_index=True)

            # --- AKKUMULERET TOTALER ---
            st.divider()
            st.markdown(f"### Samlede akkumulerede omkostninger (0 - {valgt_timer_tal} timer)")
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("Total Reservedele", f"{total_akkumuleret_res:,.2f} DKK")
            with c2: st.metric("Total Væsker/Diverse", f"{total_akkumuleret_vd:,.2f} DKK")
            with c3: st.metric("Total Arbejdsløn", f"{total_akkumuleret_arbejd:,.2f} DKK")
            with c4: 
                st.markdown(f"<div style='background-color: #367c2b; padding: 10px; border-radius: 5px; color: white; text-align: center;'>"
                            f"<small>AKKUMULERET TOTAL</small><br><strong><big>{total_akkumuleret_alt:,.2f} DKK</big></strong></div>", unsafe_allow_html=True)

            # --- DRIFTSØKONOMI ---
            st.markdown("<br>", unsafe_allow_html=True)
            col_info, col_box = st.columns([2, 1])
            with col_info:
                st.markdown(f"### Reel serviceomkostning pr. driftstime")
                st.write(f"Baseret på alle serviceomkostninger op til **{valgt_timer_tal} timer**.")
            with col_box:
                st.markdown(f"<div style='border: 2px solid #367c2b; padding: 15px; border-radius: 10px; text-align: center; background-color: #f9f9f9;'>"
                            f"<span style='color: #555; font-size: 0.9em; font-weight: bold;'>REEL PRIS PR. DRIFTSTIME</span><br>"
                            f"<span style='font-size: 1.6em; font-weight: bold; color: #367c2b;'>{pris_pr_time_akkumuleret:,.2f} DKK/t</span>"
                            f"</div>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Fejl: {e}")
