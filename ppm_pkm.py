import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import plotly.express as px
import mariadb
import streamlit as st

# Process of opening and cleansing the Data


conn = mariadb.connect(host='localhost',
                          database='mpninfo',
                          user='root',
                          passwd='gr4dea') # Create mariadb connection to database
query = '''
SELECT KET,
       NPWP,
       KPP,
       CABANG,
       NAMA,
       KDMAP,
       KDBAYAR,
       MASA,
       MASA2,
       TAHUN,
       TAHUNBAYAR,
       BULANBAYAR,
       DATEBAYAR,
       NOMINAL,
       NTPN,
       NOSK,
       CASE
         WHEN KDMAP = '411128' AND KDBAYAR IN ('427','428') THEN 'PPS'
         WHEN KDMAP = '411128' AND KDBAYAR = '422' THEN 'PKM'
         WHEN KET IN ('SPMKP','PBK KIRIM','PBK TERIMA') THEN 'PPM'
         WHEN TAHUNBAYAR - TAHUN IN (0,1) AND KDMAP IN ('411125','411126','411111','411112') AND KDBAYAR IN ('200','199','310','320','390','500','501') THEN 'PPM'
         WHEN TAHUNBAYAR - TAHUN IN (0,1) AND KDMAP IN ('411125','411126','411111','411112') AND KDBAYAR = '300' AND MASA = 1 AND MASA2 = 12 THEN 'PPM'
         WHEN NOSK IS NOT NULL AND NOSK <> '-' AND NOSK <> '' AND NOSK NOT LIKE '%PBK%' AND NOSK <> 'TIDAK DIKETAHUI' AND MOD (TAHUNBAYAR,100) - CAST(RIGHT(NOSK,2) AS INT) > 0 THEN 'PKM'
         WHEN TAHUNBAYAR = TAHUN THEN 'PPM'
         WHEN (TAHUNBAYAR - TAHUN IN (0,1) AND MASA = 12) THEN 'PPM'
         WHEN TAHUN > TAHUNBAYAR THEN 'PPM'
         ELSE 'PKM'
       END FLAG_PPM_PKM
FROM MPN
WHERE TAHUNBAYAR = 2022
''' # Mariadb Query

penerimaan = pd.read_sql(query, conn) # Open the data as pandas DataFrame
penerimaan['NPWP'] = penerimaan['NPWP']+penerimaan['KPP']+penerimaan['CABANG'] # Cari NPWP full
sort_col = ['KET', 'NPWP', 'NAMA', 'KDMAP', 'KDBAYAR', 'MASA',
       'MASA2', 'TAHUN', 'TAHUNBAYAR', 'BULANBAYAR', 'DATEBAYAR', 'NOMINAL',
       'NTPN', 'NOSK', 'FLAG_PPM_PKM'] # Susun ulang kolom (1)
penerimaan = penerimaan[sort_col] #Susun ulang kolom (2)

mfwp = pd.read_excel('MFWP 045 280822.xlsx',
                     usecols=['NPWP','KELURAHAN','JNS_WP','NAMA_AR','SEKSI', 'KD_KLU']
                     ,dtype='str') # Buka MFWP
mfwp.drop_duplicates('NPWP',inplace=True) # Drop NPWP yang berduplikat

penerimaan = pd.merge(penerimaan,mfwp,how='outer',left_on='NPWP', right_on='NPWP') # Merge kedua file
penerimaan = penerimaan[penerimaan['NOMINAL'].isna() ^ 1] # Hapus barus yg NA pada penerimaan
penerimaan.drop('KET',inplace=True,axis=1)



### Mulai Visualisasi ###
st.set_page_config(layout='wide')
st.title('Monitoring PPM PKM KPP Pratama Jakarta Koja')

#### Akumulasi Penerimaan Per Bulan (Main view) ####
main_view = penerimaan.groupby(['BULANBAYAR','FLAG_PPM_PKM']).sum()
main_view = main_view.reset_index()[['BULANBAYAR','FLAG_PPM_PKM','NOMINAL']]
st.plotly_chart(px.bar(main_view,
                        x='BULANBAYAR',
                        y='NOMINAL',
                        color='FLAG_PPM_PKM',
                        labels={'FLAG_PPM_PKM':'Jenis Kegiatan','BULANBAYAR':'Bulan'},
                        range_x=[0,12],
                        height=600),
                use_container_width=True)


##### Pembuatan kolom #####
col1, col2 = st.columns(2)

##### Col 1 untuk penerimaan per AR #####

per_ar = penerimaan.groupby(['NAMA_AR','SEKSI','FLAG_PPM_PKM']).sum().reset_index()[['NAMA_AR', 'SEKSI','FLAG_PPM_PKM','NOMINAL']]
with col1:
    st.header('PPM PKM Per AR')
    seksi = st.selectbox('Seksi Pengawasan',('I', 'II', 'III', 'IV', 'V', 'VI'))
    st.plotly_chart(px.bar(per_ar[per_ar['SEKSI'] == seksi],
                           x='NAMA_AR',
                           y = 'NOMINAL',
                           color='FLAG_PPM_PKM',
                           labels={'FLAG_PPM_PKM':'Jenis Kegiatan','NAMA_AR':'Nama AR'}))

##### col 2 untuk penerimaan per Sektor #####
klu_q ='''
SELECT *
FROM klu
'''

klu = pd.read_sql(klu_q, conn)
klu = klu.drop_duplicates('kode')
per_klu = pd.merge(penerimaan, klu, left_on='KD_KLU', right_on='kode', how='outer')
per_klu = per_klu[per_klu['NOMINAL'].isna() ^ 1]
per_klu = per_klu.groupby(['BULANBAYAR','sektor', 'FLAG_PPM_PKM']).sum()
per_klu = per_klu.reset_index()[['BULANBAYAR','sektor', 'FLAG_PPM_PKM','NOMINAL']]
per_klu['BULANBAYAR'] = per_klu['BULANBAYAR'].apply(int)

map_bulan = {'Januari':1,
             'Februari':2,
             'Maret':3,
             'April':4,
             'Mei':5,
             'Juni':6,
             'Juli':7,
             'Agustus':8,
             'September':9,
             'Oktober':10,
             'November':11,
             'Desember':12}

with col2:
    st.header('Penerimaan Per Sektor')
    bulan = ['Januari',
             'Februari',
             'Maret',
             'April',
             'Mei',
             'Juni',
             'Juli',
             'Agustus',
             'September',
             'Oktober',
             'November',
             'Desember']
    bulan_klu = st.selectbox("Bulan: ", bulan)
    st.plotly_chart(px.bar(per_klu[per_klu['BULANBAYAR'] == map_bulan[bulan_klu]],
                                                            x='sektor',
                                                            y='NOMINAL',
                                                            color='FLAG_PPM_PKM',
                                                            labels={'FLAG_PPM_PKM': 'Jenis Kegiatan', 'sektor': 'Sektor'})
)