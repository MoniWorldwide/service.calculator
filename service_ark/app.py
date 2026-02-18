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
    timepris = st.sidebar.number_input("Din værkstedstimepris (DKK)", value=750)
    ordretype = st.sidebar.radio("Vælg Ordretype (Pris for filtre)", ["Brutto", "Haste", "Uge", "Måned"])
    avance = st.sidebar.slider("Avance på RESERVEDELE (%)", 0, 50, 0)

    valgt_fil = os.path.join(nuværende_mappe, f"{model_valg}.csv")

    try:
        # 1. Indlæs rå data for at finde headers og sektioner
        raw_df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=None)
        header_row_index = 0
        for i, row in raw_df.iterrows():
            if row.astype(str).str.contains('timer', case=False).any():
                header_row_index = i
                break
        
        # 2. Indlæs med korrekt header
        df = pd.read_csv(valgt_fil, sep=';', encoding='latin-1', header=header_row_index)
        df.columns = [str(c).strip() for c in df.columns]
        beskrivelse_kol = df.columns[0]
        pris_kol_h = df.columns[7] # Kolonne H
        
        interval_kolonner = [c for c in df.columns if "timer" in c.lower()]
        
        if interval_kolonner:
            valgt_interval = st.selectbox("Vælg Service Interval", interval_kolonner)
            
            # Find sektions-start
            v_idx = df[df[beskrivelse_kol].astype(str).str.strip().str.lower() == 'væsker'].index
            d_idx = df[df[beskrivelse_kol].astype(str).str.strip().str.lower() == 'diverse'].index
            v_start = v_idx[0] if len(v_idx) > 0 else 9999
            d_start = d_idx[0] if len(d_idx) > 0 else 9999

            # Hjælpefunktion til tal
            def rens_til_tal(val):
                if pd.isna(val) or str(val).strip() in ["", "nan", "None"]: return 0.0
                return pd.to_numeric(str(val).replace('.', '').replace(',', '.'), errors='coerce') or 0.0

            # --- FILTRERING ---
            # Filtre og Væsker skal have markering i interval-kolonnen
            df[valgt_interval] = df[valgt_interval].astype(str).replace(['nan', 'None', 'nan '], '').str.strip()
            
            hoved = df[(df.index < v_start) & (df[valgt_interval] != "")].copy()
            vaesker = df[(df.index > v_start) & (df.index < d_start) & (df[valgt_interval] != "")].copy()
            
            # Diverse sektionen: Tag alt med der har en pris i kolonne H (fra d_start og ned)
            # Vi fjerner dog selve overskriftsrækken "Diverse"
            diverse = df[df.index >= d_start].copy()
            diverse = diverse[diverse[beskrivelse_kol].astype(str).str.strip().str.lower() != 'diverse']
            diverse = diverse[diverse[pris_kol_h].apply(rens_til_tal) > 0].copy()

            # --- BEREGNING ---
            def beregn_visning(data, type="dele"):
                if data.empty: return data
                data = data.copy()
                data['Antal_Tal'] = data['Antal'].apply(rens_til_tal)
                
                if type == "dele":
                    data['Enhed_Tal'] = data[ordretype].apply(rens_til_tal)
                    data['Total_Tal'] = data['Antal_Tal'] * data['Enhed_Tal'] * (1 + avance/100)
                else:
                    # Væsker og Diverse bruger altid kolonne H
                    data['Enhed_Tal'] = data[pris_kol_h].apply(rens_til_tal)
                    data['Total_Tal'] = data['Antal_Tal'] * data['Enhed_Tal']
                return data

            hoved = beregn_visning(hoved, "dele")
            vaesker = beregn_visning(vaesker, "univar")
            diverse = beregn_visning(diverse, "univar")

            # --- VISNING ---
            st.subheader(f"Serviceoversigt: {model_valg} - {valgt_interval}")

            if not hoved.empty:
                st.markdown("#### Filtre og Reservedele")
                st.dataframe(pd.DataFrame({
                    beskrivelse_kol: hoved[beskrivelse_kol],
                    'Reservedelsnr.': hoved['Reservedelsnr.'],
                    'Enhedspris': hoved['Enhed_Tal'].map("{:,.2f}".format),
                    'Antal': hoved['Antal'],
                    'Total (inkl. avance)': hoved['Total_Tal'].map("{:,.2f} DKK".format)
                }), use_container_width=True, hide_index=True)

            if not vaesker.empty:
                st.markdown("#### Væsker (Olie, kølervæske osv.)")
                st.dataframe(pd.DataFrame({
                    beskrivelse_kol: vaesker[beskrivelse_kol],
                    'Foreslået salgspris fra Univar': vaesker['Enhed_Tal'].map("{:,.2f}".format),
                    'Antal': vaesker['Antal'],
                    'Total': vaesker['Total_Tal'].map("{:,.2f} DKK".format)
                }), use_container_width=True, hide_index=True)

            if not diverse.empty:
                st.markdown("#### Diverse")
                st.dataframe(pd.DataFrame({
                    beskrivelse_kol: diverse[beskrivelse_kol],
                    'Foreslået salgspris': diverse['Enhed_Tal'].map("{:,.2f}".format),
                    'Antal': diverse['Antal'],
                    'Total': diverse['Total_Tal'].map("{:,.2f} DKK".format)
                }), use_container_width=True, hide_index=True)

            # TOTAL
            st.divider()
            total_sum = hoved['Total_Tal'].sum() if not hoved.empty else 0
            total_sum += vaesker['Total_Tal'].sum() if not vaesker.empty else 0
            total_sum += diverse['Total_Tal'].sum() if not diverse.empty else 0
            
            st.metric("Samlet pris for dele (Ekskl. moms)", f"{total_sum:,.2f} DKK")
            
        else:
            st.warning("Ingen service-intervaller fundet.")

    except Exception as e:
        st.error(f"Fejl: {e}")
