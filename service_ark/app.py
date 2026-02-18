import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Deutz-Fahr Serviceberegner", layout="wide")

# Logo og Titel
col1, col2 = st.columns([1, 4])
with col1:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=150)
with col2:
    st.title("Deutz-Fahr Serviceberegner")

# Find filer
nuværende_mappe = os.path.dirname(__file__)
filer_i_mappe = [f for f in os.listdir(nuværende_mappe) if f.endswith('.csv')]
modeller = [f.replace('.csv', '') for f in filer_i_mappe]

if not modeller:
    st.error("Ingen data fundet.")
else:
    # --- SIDEBAR ---
    st.sidebar.header("Indstillinger")
    model_valg = st.sidebar.selectbox("Vælg Traktormodel", sorted(modeller))
    ordretype = st.sidebar.radio("Vælg Ordretype (Pris)", ["Brutto", "Haste", "Uge", "Måned"])
    avance = st.sidebar.slider("Avance på dele (%)", 0, 50, 0)

    valgt_fil = os.path.join(nuværende_mappe, f"{model_valg}.csv")

    try:
        # 1. Find header
        raw_df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=None)
        header_row_index = 0
        for i, row in raw_df.iterrows():
            if row.astype(str).str.contains('timer', case=False).any():
                header_row_index = i
                break
        
        # 2. Indlæs data
        df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=header_row_index)
        df.columns = [str(c).strip() for c in df.columns]
        beskrivelse_kol = df.columns[0]

        interval_kolonner = [c for c in df.columns if "timer" in c.lower()]
        
        if interval_kolonner:
            valgt_interval = st.selectbox("Vælg Service Interval", interval_kolonner)
            
            # --- LOGIK FOR FILTRERING OG BEREGNING ---
            # Vi tager rækker der ikke er tomme i interval-kolonnen
            df[valgt_interval] = df[valgt_interval].astype(str).replace(['nan', 'None', 'nan '], '').str.strip()
            dele_fundet = df[df[valgt_interval] != ""].copy()

            if not dele_fundet.empty:
                # Rens pris-kolonnen
                def rens_til_tal(serie):
                    return pd.to_numeric(serie.astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False), errors='coerce').fillna(0)

                # Beregn antal (Hvis det er et 'x', tæller vi det som 1. Hvis det er et tal, bruger vi tallet)
                dele_fundet['Antal_Tal'] = pd.to_numeric(dele_fundet[valgt_interval].str.replace(',', '.'), errors='coerce').fillna(1)
                # En 'x' bliver til NaN i to_numeric, så vi tvinger alle 'x'er til at være 1
                dele_fundet.loc[dele_fundet[valgt_interval].str.lower() == 'x', 'Antal_Tal'] = 1
                
                # Beregn Linjetotal
                dele_fundet['Enhedspris'] = rens_til_tal(dele_fundet[ordretype])
                dele_fundet['Total_Pris'] = dele_fundet['Antal_Tal'] * dele_fundet['Enhedspris'] * (1 + avance/100)

                # --- SEKTIONSOPDELING ---
                vaesker_idx = df[df[beskrivelse_kol].astype(str).str.contains('Væsker', case=False, na=False)].index
                diverse_idx = df[df[beskrivelse_kol].astype(str).str.contains('Diverse', case=False, na=False)].index
                v_start = vaesker_idx[0] if len(vaesker_idx) > 0 else 9999
                d_start = diverse_idx[0] if len(diverse_idx) > 0 else 9999

                def vis_tabel(titel, data):
                    if not data.empty:
                        st.markdown(f"#### {titel}")
                        # Vi viser: Beskrivelse, Antal (fra intervallet), Enhedspris og Total
                        vis_df = data.copy()
                        vis_df = vis_df.rename(columns={valgt_interval: 'Antal/Info', ordretype: 'Pris pr. stk/liter'})
                        kol_at_vise = [beskrivelse_kol, 'Reservedelsnr.', 'Antal/Info', 'Pris pr. stk/liter']
                        st.dataframe(vis_df[kol_at_vise], use_container_width=True, hide_index=True)

                hoved = dele_fundet[dele_fundet.index < v_start]
                vaesker = dele_fundet[(dele_fundet.index > v_start) & (dele_fundet.index < d_start)]
                diverse = dele_fundet[dele_fundet.index > d_start]

                st.subheader(f"Beregning for {model_valg} - {valgt_interval}")
                vis_tabel("Filtre og Reservedele", hoved)
                vis_tabel("Væsker (Olie, kølervæske osv.)", vaesker)
                vis_tabel("Diverse", diverse)
                
                # TOTAL
                total_sum = dele_fundet['Total_Pris'].sum()
                st.divider()
                st.metric(f"Samlet pris (Ekskl. moms)", f"{total_sum:,.2f} DKK")
                st.caption(f"Beregnet ud fra {ordretype}-priser med {avance}% avance.")
            else:
                st.info("Ingen dele eller væsker markeret i dette interval.")
        else:
            st.warning("Ingen service-intervaller fundet.")

    except Exception as e:
        st.error(f"Fejl: {e}")
