import streamlit as st
import pandas as pd
from fpdf import FPDF
import io
import os

# --- KONFIGURATION ---
st.set_page_config(page_title=Deutz-Fahr Serviceberegner, layout=wide)

# Indlæs logo (Gem dit uploadede logo som 'logo.png')
def load_logo()
    if os.path.exists(logo.png)
        return logo.png
    return None

# --- SIDEBAR FORHANDLER INDSTILLINGER ---
st.sidebar.image(httpsupload.wikimedia.orgwikipediacommonsdd7Deutz-Fahr_logo.svg, width=200)
st.sidebar.header(Forhandler Kontrolpanel)

forhandler_navn = st.sidebar.text_input(Dit Forhandlernavn, Maskinforretning AS)
timepris_input = st.sidebar.number_input(Din Timepris (DKKt), value=850, step=25)
fortjeneste_pct = st.sidebar.slider(Fortjeneste på reservedele (%), 0, 100, 20)  100

st.sidebar.divider()
st.sidebar.markdown(### Guiden1. Vælg modeln2. Vælg intervaln3. Indtast kundeinfon4. Generer PDF)

# --- DATA LOGIK ---
modeller = {
    9340 9340.csv, 8280 8280.csv, 7250 7250.csv, 
    6230 6230.csv, 6210 6210.csv, 6190 6190.csv,
    6165 6165.csv, 6170.4 6170.4.csv, 6150.4 6150.4.csv,
    6135C 6135C.csv, 5125 5125.csv, 5115D TTV 5115D TTV.csv,
    5105 5105.csv, 5080 Keyline 5080 Keyline.csv
}

st.title(🚜 Deutz-Fahr Serviceaftale-beregner)

# 1. Vælg Model
valgt_model_navn = st.selectbox(Vælg Traktormodel, list(modeller.keys()))
filnavn = modeller[valgt_model_navn]

try
    # Indlæs data fra din fil
    df = pd.read_csv(filnavn, skiprows=2) # Vi springer de første rækker over som i dit ark
    
    # Find kolonner med timer i navnet (intervallerne)
    interval_kolonner = [col for col in df.columns if timer in col.lower()]
    
    # 2. Vælg Interval (Kun dem der findes i dit ark!)
    valgt_interval = st.selectbox(Vælg Serviceinterval (Timer), interval_kolonner)

    # 3. Beregning
    # Vi summerer priserne fra rækkerne i den valgte kolonne
    # Vi antager at 'Måned' eller 'Brutto' kolonnen holder indkøbsprisen
    indkob_pris_total = pd.to_numeric(df[valgt_interval], errors='coerce').sum()
    
    # Beregn slutpris baseret på forhandlerens indstillinger
    pris_dele_med_avance = indkob_pris_total  (1 + fortjeneste_pct)
    # Estimeret arbejdstid (f.eks. 1.5 time pr. 500 timer - du kan rette denne faktor)
    arbejdstimer = (int(valgt_interval.split()[0])  500)  2 
    pris_arbejde = arbejdstimer  timepris_input
    
    total_pris = pris_dele_med_avance + pris_arbejde

    # --- VISNING ---
    c1, c2, c3 = st.columns(3)
    c1.metric(Reservedele (inkl. avance), f{pris_dele_med_avance,.2f} DKK)
    c2.metric(Arbejdsløn (estimeret), f{pris_arbejde,.2f} DKK)
    c3.subheader(fTotal {total_pris,.2f} DKK)

    st.divider()

    # 4. Kundeinfo
    st.write(### Kunde- og Maskininformation)
    col_k1, col_k2 = st.columns(2)
    kunde_navn = col_k1.text_input(Kundens Navn)
    stelnummer = col_k2.text_input(Stelnummer (VIN))

    # 5. PDF GENERERING
    def generate_pdf()
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font(Arial, 'B', 16)
        pdf.cell(0, 10, TILBUD SERVICEAFTALE, ln=True, align='C')
        pdf.ln(10)
        pdf.set_font(Arial, '', 12)
        pdf.cell(0, 10, fForhandler {forhandler_navn}, ln=True)
        pdf.cell(0, 10, fKunde {kunde_navn}, ln=True)
        pdf.cell(0, 10, fModel {valgt_model_navn}, ln=True)
        pdf.cell(0, 10, fStelnummer {stelnummer}, ln=True)
        pdf.cell(0, 10, fServiceinterval {valgt_interval}, ln=True)
        pdf.ln(10)
        pdf.set_font(Arial, 'B', 14)
        pdf.cell(0, 10, fSamlet pris ekskl. moms DKK {total_pris,.2f}, ln=True)
        return pdf.output(dest='S').encode('latin-1')

    if st.button(Generer og download PDF)
        if kunde_navn and stelnummer
            pdf_output = generate_pdf()
            st.download_button(label=Download PDF, data=pdf_output, file_name=fTilbud_{kunde_navn}.pdf)
        else
            st.warning(Udfyld venligst kundenavn og stelnummer.)

except Exception as e
    st.error(fKunne ikke indlæse filen {filnavn}. Sørg for at den er uploadet korrekt.)