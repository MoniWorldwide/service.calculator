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
        
        # 2. Indlæs data korrekt
        df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=header_row_index)
        df.columns = [str(c).strip() for c in df.columns]
        beskrivelse_kol = df.columns[0]
        
        interval_kolonner = [c for c in df.columns if "timer" in c.lower()]
        
        if interval_kolonner:
            valgt_interval = st.selectbox("Vælg Service Interval", interval_kolonner)
            
            # Find rækker markeret i intervallet
            df[valgt_interval] = df[valgt_interval].astype(str).replace(['nan', 'None', 'nan '], '').str.strip()
            dele_fundet = df[df[valgt_interval] != ""].copy()

            if not dele_fundet.empty:
                # Rens tal-funktion
                def rens_til_tal(serie):
                    return pd.to_numeric(serie.astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False), errors='coerce').fillna(0)

                # Beregninger
                dele_fundet['Antal_Tal'] = pd.to_numeric(dele_fundet['Antal'].astype(str).str.replace(',', '.'), errors='coerce').fillna(1)
                dele_fundet['Pris_Valgt_Tal'] = rens_til_tal(dele_fundet[ordretype])
                dele_fundet['Linje_Total'] = dele_fundet['Antal_Tal'] * dele_fundet['Pris_Valgt_Tal'] * (1 + avance/100)

                # Sektions-opdeling
                vaesker_idx = df[df[beskrivelse_kol].astype(str).str.contains('Væsker', case=False, na=False)].index
                diverse_idx = df[df[beskrivelse_kol].astype(str).str.contains('Diverse', case=False, na=False)].index
                v_start = vaesker_idx[0] if len(vaesker_idx) > 0 else 9999
                d_start = diverse_idx[0] if len(diverse_idx) > 0 else 9999

                st.subheader(f"Serviceoversigt: {model_valg} - {valgt_interval}")

                # 1. Filtre (Standard layout)
                hoved = dele_fundet[dele_fundet.index < v_start]
                if not hoved.empty:
                    st.markdown("#### Filtre og Reservedele")
                    st.dataframe(pd.DataFrame({
                        beskrivelse_kol: hoved[beskrivelse_kol],
                        'Reservedelsnr.': hoved['Reservedelsnr.'],
                        'Antal': hoved['Antal'],
                        f'Pris ({ordretype})': hoved[ordretype]
                    }), use_container_width=True, hide_index=True)

                # 2. Væsker (Uden reservedelsnr. + Ny overskrift)
                vaesker = dele_fundet[(dele_fundet.index > v_start) & (dele_fundet.index < d_start)]
                if not vaesker.empty:
                    st.markdown("#### Væsker (Olie, kølervæske osv.)")
                    st.dataframe(pd.DataFrame({
                        beskrivelse_kol: vaesker[beskrivelse_kol],
                        'Antal': vaesker['Antal'],
                        'Foreslået salgspris fra Univar': vaesker[ordretype]
                    }), use_container_width=True, hide_index=True)

                # 3. Diverse (Uden reservedelsnr. + Ny overskrift)
                diverse = dele_fundet[dele_fundet.index > d_start]
                if not diverse.empty:
                    st.markdown("#### Diverse")
                    st.dataframe(pd.DataFrame({
                        beskrivelse_kol: diverse[beskrivelse_kol],
                        'Antal': diverse['Antal'],
                        'Foreslået salgspris fra Univar': diverse[ordretype]
                    }), use_container_width=True, hide_index=True)

                # TOTAL
                st.divider()
                total_sum = dele_fundet['Linje_Total'].sum()
                st.metric("Samlet pris (Ekskl. moms)", f"{total_sum:,.2f} DKK")
                st.caption(f"Beregnet ud fra {ordretype}-priser med {avance}% avance.")
            else:
                st.info(f"Ingen markeringer fundet for {valgt_interval}")
        else:
            st.warning("Kunne ikke finde service-intervaller.")

    except Exception as e:
        st.error(f"Der opstod en fejl: {e}")
