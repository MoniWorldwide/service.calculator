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
        # 1. Find header række
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
            
            # Rens interval kolonne
            df[valgt_interval] = df[valgt_interval].astype(str).replace(['nan', 'None', 'nan '], '').str.strip()
            dele_fundet = df[df[valgt_interval] != ""].copy()

            if not dele_fundet.empty:
                # Hjælpefunktion til tal-rens
                def rens_til_tal(serie):
                    return pd.to_numeric(serie.astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False), errors='coerce').fillna(0)

                # Forbered priser og mængder
                dele_fundet['Mængde_Excel'] = dele_fundet[valgt_interval]
                dele_fundet['Pris_Pr_Enhed'] = rens_til_tal(dele_fundet[ordretype])
                
                # Beregn linjetotal (håndterer 'x' som 1)
                antal_numerisk = pd.to_numeric(dele_fundet[valgt_interval].str.replace(',', '.'), errors='coerce').fillna(1)
                dele_fundet['Linje_Total'] = antal_numerisk * dele_fundet['Pris_Pr_Enhed'] * (1 + avance/100)

                # Find sektions-indekser
                vaesker_idx = df[df[beskrivelse_kol].astype(str).str.contains('Væsker', case=False, na=False)].index
                diverse_idx = df[df[beskrivelse_kol].astype(str).str.contains('Diverse', case=False, na=False)].index
                v_start = vaesker_idx[0] if len(vaesker_idx) > 0 else 9999
                d_start = diverse_idx[0] if len(diverse_idx) > 0 else 9999

                # --- SEKTION 1: RESERVEDELE ---
                hoved = dele_fundet[dele_fundet.index < v_start]
                if not hoved.empty:
                    st.markdown("#### Filtre og Reservedele")
                    # Vi fjerner en eventuel eksisterende 'Antal' kolonne for at undgå dubletter
                    kol_til_visning = [beskrivelse_kol, 'Reservedelsnr.', ordretype]
                    eksisterende_kol = [k for k in kol_til_visning if k in hoved.columns]
                    st.dataframe(hoved[eksisterende_kol], use_container_width=True, hide_index=True)

                # --- SEKTION 2 & 3: VÆSKER & DIVERSE ---
                def vis_special_sektion(titel, data, pris_label):
                    if not data.empty:
                        st.markdown(f"#### {titel}")
                        vis_df = data.copy()
                        
                        # Vi opretter de nye kolonner specifikt
                        vis_df['Antal_Visning'] = vis_df['Mængde_Excel']
                        vis_df['Info_Tekst'] = "Foreslået salgspris fra Univar"
                        
                        # Vi vælger kun de kolonner vi skal bruge og giver dem pæne navne
                        # På denne måde undgår vi 'Duplicate column names'
                        final_df = pd.DataFrame({
                            beskrivelse_kol: vis_df[beskrivelse_kol],
                            'Antal': vis_df['Antal_Visning'],
                            'Info': vis_df['Info_Tekst'],
                            pris_label: vis_df[ordretype]
                        })
                        st.dataframe(final_df, use_container_width=True, hide_index=True)

                vaesker = dele_fundet[(dele_fundet.index > v_start) & (dele_fundet.index < d_start)]
                vis_special_sektion("Væsker (Olie, kølervæske osv.)", vaesker, "Pris pr. liter")

                diverse = dele_fundet[dele_fundet.index > d_start]
                vis_special_sektion("Diverse", diverse, "Pris pr. enhed")

                # TOTAL
                st.divider()
                total_sum = dele_fundet['Linje_Total'].sum()
                st.metric(f"Samlet pris (Ekskl. moms)", f"{total_sum:,.2f} DKK")
                st.caption(f"Beregnet ud fra {ordretype}-priser med {avance}% avance.")
        
    except Exception as e:
        st.error(f"Der opstod en fejl: {e}")
