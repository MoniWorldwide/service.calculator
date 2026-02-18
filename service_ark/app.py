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
        pris_kol_h = df.columns[7] # Kolonne H
        
        interval_kolonner = [c for c in df.columns if "timer" in c.lower()]
        
        if interval_kolonner:
            valgt_interval = st.selectbox("Vælg Service Interval", interval_kolonner)
            
            # Hjælpefunktion til tal-rensning
            def rens_til_tal(val):
                s = str(val).replace('.', '').replace(',', '.').strip()
                try:
                    return float(s)
                except:
                    return 0.0

            # Find sektioner
            indices_vaesker = df[df[beskrivelse_kol].astype(str).str.contains('Væsker', case=False, na=False)].index
            indices_diverse = df[df[beskrivelse_kol].astype(str).str.contains('Diverse', case=False, na=False)].index
            
            v_start = indices_vaesker[0] if len(indices_vaesker) > 0 else 9999
            d_start = indices_diverse[0] if len(indices_diverse) > 0 else 9999

            # --- RENSNING AF NAVNE (Skjul "None") ---
            # Vi markerer rækker der skal skules
            def skal_skjules(val):
                v = str(val).strip().lower()
                return v in ["none", "nan", ""]

            # --- DATA OPSAMLING ---
            df['markeret'] = df[valgt_interval].astype(str).replace(['nan', 'None', 'nan '], '').str.strip() != ""
            df['er_none'] = df[beskrivelse_kol].apply(skal_skjules)

            # 1. Filtre (Skal være markeret, før Væsker, og ikke være 'None')
            hoved = df[(df.index < v_start) & (df['markeret']) & (~df['er_none'])].copy()
            
            # 2. Væsker (Mellem Væsker og Diverse, markeret, og ikke 'None')
            vaesker = df[(df.index > v_start) & (df.index < d_start) & (df['markeret']) & (~df['er_none'])].copy()
            
            # 3. Diverse (Efter Diverse overskrift, har pris i H, og ikke 'None')
            diverse = df[df.index >= d_start].copy()
            diverse['pris_tjek'] = diverse[pris_kol_h].apply(rens_til_tal)
            diverse = diverse[(diverse['pris_tjek'] > 0) & (~diverse['er_none'])].copy()
            
            # Fjern selve sektionsoverskriften "Diverse" hvis den optræder som vare
            diverse = diverse[~diverse[beskrivelse_kol].astype(str).str.contains('^diverse$', case=False, na=False)]

            # --- BEREGNINGER ---
            def apply_calc(data, med_avance=False):
                if data.empty: return data
                data = data.copy()
                data['Enhed_Tal'] = (data[ordretype] if med_avance else data[pris_kol_h]).apply(rens_til_tal)
                data['Antal_Tal'] = data['Antal'].apply(rens_til_tal)
                multiplier = (1 + avance/100) if med_avance else 1.0
                data['Total_Tal'] = data['Antal_Tal'] * data['Enhed_Tal'] * multiplier
                return data

            hoved = apply_calc(hoved, med_avance=True)
            vaesker = apply_calc(vaesker, med_avance=False)
            diverse = apply_calc(diverse, med_avance=False)

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

            # SAMLET TOTAL
            st.divider()
            sum_h = hoved['Total_Tal'].sum() if not hoved.empty else 0
            sum_v = vaesker['Total_Tal'].sum() if not vaesker.empty else 0
            sum_d = diverse['Total_Tal'].sum() if not diverse.empty else 0
            total_sum = sum_h + sum_v + sum_d
            
            st.metric("Samlet pris for dele (Ekskl. moms)", f"{total_sum:,.2f} DKK")
            
        else:
            st.warning("Kan ikke finde interval-kolonner.")
    except Exception as e:
        st.error(f"Fejl: {e}")
