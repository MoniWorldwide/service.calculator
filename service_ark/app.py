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
            
            # --- AKKUMULERET LOGIK ---
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

            # Find sektions-indekser
            v_idx = df[df[beskrivelse_kol].astype(str).str.contains('Væsker', case=False, na=False)].index
            d_idx = df[df[beskrivelse_kol].astype(str).str.contains('Diverse', case=False, na=False)].index
            v_start = v_idx[0] if len(v_idx) > 0 else 9999
            d_start = d_idx[0] if len(d_idx) > 0 else 9999

            # --- BEREGN AKKUMULERET TOTAL (0 til valgt interval) ---
            total_akkumuleret_res = 0.0
            total_akkumuleret_vd = 0.0
            total_akkumuleret_arbejd = 0.0

            for interval in forudgaaende_intervaller:
                m_mask = df[interval].astype(str).replace(['nan', 'None', ''], None).notna()
                
                # Reservedele
                res_part = df[(df.index < v_start) & m_mask].copy()
                total_akkumuleret_res += (res_part[ordretype].apply(rens_til_tal) * res_part['Antal'].apply(rens_til_tal) * (1 + avance/100)).sum()
                
                # Væsker & Diverse
                vd_part = df[(df.index > v_start) & m_mask].copy()
                vd_part = vd_part[~vd_part[beskrivelse_kol].astype(str).str.strip().str.lower().isin(["none", "nan", "", "diverse"])]
                total_akkumuleret_vd += (vd_part[pris_kol_h].apply(rens_til_tal) * vd_part['Antal'].apply(rens_til_tal)).sum()
                
                # Arbejdsløn
                mask_arbejd = df[beskrivelse_kol].astype(str).str.contains('Arbejd', case=False, na=False)
                if mask_arbejd.any():
                    t_timer = rens_til_tal(df[mask_arbejd][interval].values[0])
                    total_akkumuleret_arbejd += (t_timer * timepris)

            total_akkumuleret_alt = total_akkumuleret_res + total_akkumuleret_vd + total_akkumuleret_arbejd
            pris_pr_time_akkumuleret = total_akkumuleret_alt / valgt_timer_tal if valgt_timer_tal > 0 else 0

            # --- DATA TIL TABEL-VISNING (KUN DET VALGTE INTERVAL) ---
            df['markeret'] = df[valgt_interval].astype(str).replace(['nan', 'None', ''], None).notna()
            
            hoved = df[(df.index < v_start) & (df['markeret'])].copy()
            vaesker = df[(df.index > v_start) & (df.index < d_start) & (df['markeret'])].copy()
            diverse = df[(df.index >= d_start) & (df['markeret'])].copy()
            
            # Rensning af tabellerne før visning
            hoved = hoved[~hoved[beskrivelse_kol].astype(str).str.strip().str.lower().isin(["none", "nan", ""])]
            vaesker = vaesker[~vaesker[beskrivelse_kol].astype(str).str.strip().str.lower().isin(["none", "nan", ""])]
            diverse = diverse[diverse[pris_kol_h].apply(rens_til_tal) > 0]
            diverse = diverse[~diverse[beskrivelse_kol].astype(str).str.strip().str.lower().isin(["diverse"])]

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

            # --- VISNING AF TABELLER ---
            st.subheader(f"{valgt_visningsnavn} - Detaljer for {valgt_interval}")
            
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

            # --- TOTALER (AKKUMULERET) ---
            st.divider()
            st.markdown(f"### Samlede akkumulerede omkostninger (0 - {valgt_timer_tal} timer)")
            st.caption(f"Beregningen summerer alle serviceintervaller op til nu: {', '.join(forudgaaende_intervaller)}")
            
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("Total Reservedele", f"{total_akkumuleret_res:,.2f} DKK")
            with c2: st.metric("Total Væsker/Diverse", f"{total_akkumuleret_vd:,.2f} DKK")
            with c3: st.metric("Total Arbejdsløn", f"{total_akkumuleret_arbejd:,.2f} DKK")
            with c4: 
                st.markdown(f"<div style='background-color: #367c2b; padding: 10px; border-radius: 5px; color: white; text-align: center;'>"
                            f"<small>AKKUMULERET TOTAL (Ekskl. moms)</small><br><strong><big>{total_akkumuleret_alt:,.2f} DKK</big></strong></div>", unsafe_allow_html=True)

            # --- DRIFTSØKONOMI BOKS ---
            st.markdown("<br>", unsafe_allow_html=True)
            col_info, col_box = st.columns([2, 1])
            with col_info:
                st.markdown(f"### Reel serviceomkostning pr. driftstime")
                st.write(f"Dette tal er beregnet ved at tage samtlige serviceomkostninger fra traktoren var ny til den har kørt **{valgt_timer_tal} timer**, og dividere dem med det totale timetal.")
                st.write(f"Dette giver det mest præcise billede af maskinens faktiske vedligeholdelsesomkostning pr. kørt time.")
            
            with col_box:
                st.markdown(f"<div style='border: 2px solid #367c2b; padding: 15px; border-radius: 10px; text-align: center; background-color: #f9f9f9;'>"
                            f"<span style='color: #555; font-size: 0.9em; font-weight: bold;'>REEL PRIS PR. DRIFTSTIME</span><br>"
                            f"<span style='font-size: 1.6em; font-weight: bold; color: #367c2b;'>{pris_pr_time_akkumuleret:,.2f} DKK/t</span>"
                            f"</div>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Fejl ved behandling af data: {e}")
