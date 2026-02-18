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
        
        # Kolonne H (index 7) indeholder priserne til Væsker og Diverse
        pris_kol_h = df.columns[7]
        
        interval_kolonner = [c for c in df.columns if "timer" in c.lower()]
        
        if interval_kolonner:
            valgt_interval = st.selectbox("Vælg Service Interval", interval_kolonner)
            
            # Find rækker markeret i det valgte interval
            df[valgt_interval] = df[valgt_interval].astype(str).replace(['nan', 'None', 'nan '], '').str.strip()
            dele_fundet = df[df[valgt_interval] != ""].copy()

            if not dele_fundet.empty:
                # Hjælpefunktion til at rense tal fra CSV
                def rens_til_tal(serie):
                    return pd.to_numeric(serie.astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False), errors='coerce').fillna(0)

                # Find skel mellem sektioner i Excel-arket
                vaesker_idx = df[df[beskrivelse_kol].astype(str).str.strip().str.lower() == 'væsker'].index
                diverse_idx = df[df[beskrivelse_kol].astype(str).str.strip().str.lower() == 'diverse'].index
                
                v_start = vaesker_idx[0] if len(vaesker_idx) > 0 else 9999
                d_start = diverse_idx[0] if len(diverse_idx) > 0 else 9999

                # Beregningslogik
                def beregn_linje_data(row):
                    # Antal hentes fra kolonne C
                    antal = pd.to_numeric(str(row['Antal']).replace(',', '.'), errors='coerce') or 0
                    
                    if row.name < v_start:
                        # RESERVEDELE: Pris fra valgt ordretype (Brutto/Haste osv.) + AVANCE
                        enhedspris = rens_til_tal(pd.Series([row[ordretype]]))[0]
                        linje_total = antal * enhedspris * (1 + avance/100)
                    else:
                        # VÆSKER/DIVERSE: Enhedspris hentes fra Kolonne H (uden avance)
                        enhedspris = rens_til_tal(pd.Series([row[pris_kol_h]]))[0]
                        linje_total = antal * enhedspris
                    
                    return pd.Series([enhedspris, linje_total])

                dele_fundet[['Enhedspris', 'Linje_Total']] = dele_fundet.apply(beregn_linje_data, axis=1)

                st.subheader(f"Serviceoversigt: {model_valg} - {valgt_interval}")

                # --- VISNING ---
                
                # 1. Filtre og Reservedele
                hoved = dele_fundet[dele_fundet.index < v_start]
                if not hoved.empty:
                    st.markdown("#### Filtre og Reservedele")
                    st.dataframe(pd.DataFrame({
                        beskrivelse_kol: hoved[beskrivelse_kol],
                        'Reservedelsnr.': hoved['Reservedelsnr.'],
                        'Enhedspris': hoved['Enhedspris'].map("{:,.2f}".format),
                        'Antal': hoved['Antal'],
                        'Total (inkl. avance)': hoved['Linje_Total'].map("{:,.2f} DKK".format)
                    }), use_container_width=True, hide_index=True)

                # 2. Væsker
                vaesker = dele_fundet[(dele_fundet.index > v_start) & (dele_fundet.index < d_start)]
                if not vaesker.empty:
                    st.markdown("#### Væsker (Olie, kølervæske osv.)")
                    st.dataframe(pd.DataFrame({
                        beskrivelse_kol: vaesker[beskrivelse_kol],
                        'Foreslået salgspris fra Univar': vaesker['Enhedspris'].map("{:,.2f}".format),
                        'Antal': vaesker['Antal'],
                        'Total': vaesker['Linje_Total'].map("{:,.2f} DKK".format)
                    }), use_container_width=True, hide_index=True)

                # 3. Diverse (Inkluderer nu punktet "Diverse" under overskriften)
                diverse = dele_fundet[dele_fundet.index >= d_start]
                # Vi fjerner selve overskriftsrækken hvis den er kommet med i 'dele_fundet'
                diverse = diverse[diverse[beskrivelse_kol].astype(str).str.strip().str.lower() != 'diverse']
                
                if not diverse.empty:
                    st.markdown("#### Diverse")
                    st.dataframe(pd.DataFrame({
                        beskrivelse_kol: diverse[beskrivelse_kol],
                        'Foreslået salgspris': diverse['Enhedspris'].map("{:,.2f}".format),
                        'Antal': diverse['Antal'],
                        'Total': diverse['Linje_Total'].map("{:,.2f} DKK".format)
                    }), use_container_width=True, hide_index=True)

                # SAMLET TOTAL
                st.divider()
                total_sum = dele_fundet['Linje_Total'].sum()
                st.metric("Samlet pris for dele (Ekskl. moms)", f"{total_sum:,.2f} DKK")
                st.caption(f"Bemærk: Væsker og diverse priser hentes fra kolonne H uden avance. Reservedele bruger {ordretype}-priser + {avance}% avance.")
                
            else:
                st.info(f"Ingen dele markeret i {valgt_interval}")
        else:
            st.warning("Service-intervaller ikke fundet.")

    except Exception as e:
        st.error(f"Der opstod en fejl: {e}")
