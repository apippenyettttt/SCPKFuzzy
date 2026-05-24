import streamlit as st
import pandas as pd
import numpy as np
import zipfile
import matplotlib.pyplot as plt

# Konigurasi awal
st.set_page_config(
    page_title="SIPETA v5.1 - Perencana Masa Tanam & Panen",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Usia tanaman
Data_panen = {
    "Padi": {"usia_bulan": 4, "keterangan": "± 115 - 120 Hari"},
    "Palawija / Jagung": {"usia_bulan": 3, "keterangan": "± 90 - 100 Hari"},
    "Hortikultura / Sayuran": {"usia_bulan": 2, "keterangan": "± 60 - 70 Hari"}
}

# Logika fuzzy
def fz_suhu(x):
    dingin = np.maximum(0, np.minimum((26 - x) / (26 - 22), 1)) if x <= 26 else 0
    if x <= 24: normal = 0
    elif 24 < x <= 28: normal = (x - 24) / (28 - 24)
    elif 28 < x <= 32: normal = (32 - x) / (32 - 28)
    else: normal = 0
    panas = np.maximum(0, np.minimum((x - 30) / (35 - 30), 1)) if x >= 30 else 0
    return dingin, normal, panas

def fz_kelembapan(x):
    rendah = np.maximum(0, np.minimum((65 - x) / (65 - 45), 1)) if x <= 65 else 0
    if x <= 55: sedang = 0
    elif 55 < x <= 75: sedang = (x - 55) / (75 - 55)
    elif 75 < x <= 88: sedang = (88 - x) / (88 - 75)
    else: sedang = 0
    tinggi = np.maximum(0, np.minimum((x - 80) / (98 - 80), 1)) if x >= 80 else 0
    return rendah, sedang, tinggi

def fz_angin(x):
    pelan = np.maximum(0, np.minimum((3.5 - x) / (3.5 - 1.5), 1)) if x <= 3.5 else 0
    kencang = np.maximum(0, np.minimum((x - 2.5) / (5.5 - 2.5), 1)) if x >= 2.5 else 0
    return pelan, kencang

def fz_awan(x):
    cerah = np.maximum(0, np.minimum((50 - x) / (50 - 0), 1)) if x <= 50 else 0
    mendung = np.maximum(0, np.minimum((x - 35) / (85 - 35), 1)) if x >= 35 else 0
    return cerah, mendung

def fz_hujan(x):
    kering = np.maximum(0, np.minimum((2.0 - x) / 2.0, 1)) if x <= 2.0 else 0
    basah = np.maximum(0, np.minimum((x - 1.0) / (50.0 - 1.0), 1)) if x >= 1.0 else 0
    return kering, basah


# Interferensi fuzzy
def cek_kelayakan(opsi_suhu, opsi_lembap, opsi_angin, opsi_awan, opsi_hujan, komoditas):
    dingin, normal, panas = opsi_suhu
    rendah, sedang, tinggi = opsi_lembap
    angin_pelan, angin_kencang = opsi_angin
    cerah, mendung = opsi_awan
    kering, basah = opsi_hujan
    
    sangatcocok = 0
    cukupcocok = 0
    tidakcocok = 0
    
    if komoditas == "Padi":
        r1 = min(normal, tinggi, angin_pelan, cerah, basah)      
        r2 = min(normal, sedang, angin_pelan, cerah, kering)      
        r3 = min(panas, rendah, angin_pelan, cerah, kering)      
        r4 = min(normal, tinggi, angin_kencang, mendung, basah)      
        
        sangatcocok = r1
        cukupcocok = r2
        tidakcocok = max(r3, r4)
        
    elif komoditas == "Palawija / Jagung":
        r1 = min(normal, sedang, angin_pelan, cerah, kering)   
        r2 = min(panas, rendah, angin_pelan, cerah, kering)   
        r3 = min(dingin, tinggi, angin_pelan, mendung, basah)   
        r4 = min(normal, tinggi, angin_kencang, basah)       
        
        sangatcocok = r1
        cukupcocok = max(r2, min(normal, sedang, angin_pelan, mendung, kering))
        tidakcocok = max(r3, r4)
        
    else:
        r1 = min(dingin, sedang, angin_pelan, cerah, kering)   
        r2 = min(normal, sedang, angin_pelan, cerah, kering)   
        r3 = min(panas, rendah, angin_pelan, cerah, kering)   
        r4 = min(normal, tinggi, angin_kencang, mendung, basah)   
        
        sangatcocok = r1
        cukupcocok = r2
        tidakcocok = max(r3, r4)

    bobottidak, bobotcukup, bobotsangat = 20, 60, 90
    totalbobot = tidakcocok + cukupcocok + sangatcocok
    
    if totalbobot == 0: 
        return 50, "Cukup Cocok"
    
    skor = ((tidakcocok * bobottidak) + (cukupcocok * bobotcukup) + (sangatcocok * bobotsangat)) / totalbobot
    
    if skor < 45: status_kelayakan = "Tidak Cocok"
    elif skor < 75: status_kelayakan = "Cukup Cocok"
    else: status_kelayakan = "Sangat Cocok"
    
    return round(skor, 2), status_kelayakan

# Grafik fungsi keanggotaan
def plot_fuzzy(nilai_input, tipe_kriteria='suhu'):
    warna_teks = 'white'
    warna_latar = 'black' 
    
    fig, ax = plt.subplots(figsize=(6, 1.5), facecolor=warna_latar)
    ax.set_facecolor(warna_latar)
    ax.tick_params(colors=warna_teks)
    ax.title.set_color(warna_teks)
    
    if tipe_kriteria == 'suhu':
        x = np.linspace(15, 40, 500)
        ax.plot(x, [fz_suhu(i)[0] for i in x], label='Dingin', color='blue')
        ax.plot(x, [fz_suhu(i)[1] for i in x], label='Normal', color='green')
        ax.plot(x, [fz_suhu(i)[2] for i in x], label='Panas', color='red')
        ax.axvline(nilai_input, color=warna_teks, linestyle='--')
        ax.set_title("Kriteria 1: Keanggotaan Suhu Rata-rata Harian (°C)")
    elif tipe_kriteria == 'kelembapan':
        x = np.linspace(20, 100, 500)
        ax.plot(x, [fz_kelembapan(i)[0] for i in x], label='Rendah', color='orange')
        ax.plot(x, [fz_kelembapan(i)[1] for i in x], label='Sedang', color='aquamarine')
        ax.plot(x, [fz_kelembapan(i)[2] for i in x], label='Tinggi', color='deepskyblue')
        ax.axvline(nilai_input, color=warna_teks, linestyle='--')
        ax.set_title("Kriteria 2: Keanggotaan Kelembapan Rata-rata Harian (%)")
    elif tipe_kriteria == 'angin':
        x = np.linspace(0, 8, 500)
        ax.plot(x, [fz_angin(i)[0] for i in x], label='Pelan', color='teal')
        ax.plot(x, [fz_angin(i)[1] for i in x], label='Kencang', color='red')
        ax.axvline(nilai_input, color=warna_teks, linestyle='--')
        ax.set_title("Kriteria 3: Kecepatan Angin Rata-rata Harian (m/s)")
    elif tipe_kriteria == 'awan':
        x = np.linspace(0, 100, 500)
        ax.plot(x, [fz_awan(i)[0] for i in x], label='Cerah', color='yellow')
        ax.plot(x, [fz_awan(i)[1] for i in x], label='Mendung', color='slategray')
        ax.axvline(nilai_input, color=warna_teks, linestyle='--')
        ax.set_title("Kriteria 4: Rata-rata Cakupan Awan Harian (%)")
    else: 
        x = np.linspace(0, 60, 500)
        ax.plot(x, [fz_hujan(i)[0] for i in x], label='Kering', color='orange')
        ax.plot(x, [fz_hujan(i)[1] for i in x], label='Basah', color='blue')
        ax.axvline(nilai_input, color=warna_teks, linestyle='--')
        ax.set_title("Kriteria 5: Total Akumulasi Hujan Harian (mm)")
        
    ax.legend(loc='upper right', fontsize='xx-small', framealpha=0.3)
    ax.grid(True, alpha=0.15, color=warna_teks)
    return fig

def plot_tren_harian(df_lini_masa):
    df_terurut = df_lini_masa.sort_values(by='Tanggal', ascending=True)
    warna_teks = 'white'
    warna_latar = 'black'
    warna_garis_kisi = '#444444'
    
    fig, axes = plt.subplots(5, 1, figsize=(11, 8.5), sharex=True, facecolor=warna_latar)
    daftar_warna = ['red', 'skyblue', 'green', 'orange', 'blue']
    label_y = ['Suhu Rata² (°C)', 'Kelembapan Rata² (%)', 'Angin Rata² (m/s)', 'Awan Rata² (%)', 'Total Hujan (mm)']
    nama_kolom = ['temp', 'humidity', 'wind_speed', 'clouds_all', 'rain_1h']
    
    for i, ax in enumerate(axes):
        ax.set_facecolor(warna_latar)
        ax.plot(df_terurut['Tanggal'], df_terurut[nama_kolom[i]], color=daftar_warna[i], linewidth=1.5)
        ax.set_ylabel(label_y[i], color=warna_teks, fontsize=9)
        ax.tick_params(colors=warna_teks, labelsize=8)
        ax.grid(True, alpha=0.25, color=warna_garis_kisi)
        
    axes[0].set_title("Tren Data Cuaca Mingguan (Tahun 2019 - Sekarang)", color=warna_teks, fontsize=12)
    axes[4].set_xlabel('Garis Waktu (Hasil Resampling Mingguan Berkelanjutan)', color=warna_teks)
    
    plt.xticks(rotation=25, ha='right')
    fig.autofmt_xdate()
    plt.tight_layout()
    return fig

# Papeline data
@st.cache_data
def load_data():
    jalur_zip = "openweatherdata-denpasar-1990-2020.csv.zip"
    nama_csv = "openweatherdata-denpasar-1990-2020.csv"
    
    with zipfile.ZipFile(jalur_zip, 'r') as z:
        with z.open(nama_csv) as f:
            df = pd.read_csv(f)
            
    df['dt_iso'] = pd.to_datetime(df['dt_iso'].str.replace(' +0000 UTC', '', regex=False))
    df['rain_1h'] = df['rain_1h'].fillna(0)
    df['Tahun'] = df['dt_iso'].dt.year
    df['Bulan'] = df['dt_iso'].dt.month
    
    # rekam jejak
    df_rekaman_bulanan = df.groupby(['Tahun', 'Bulan']).agg({'rain_1h': 'sum'}).reset_index()
    df_historis_bulanan = df_rekaman_bulanan.groupby('Bulan').agg({'rain_1h': 'mean'}).reset_index()
    df_historis_bulanan.rename(columns={'rain_1h': 'Hujan_Historis_Bulanan'}, inplace=True)
    
    #kondisi lapangan mingguan
    df_modern = df[df['Tahun'] >= 2019].copy()
    df_modern.set_index('dt_iso', inplace=True)
    
    df_mingguan = df_modern.resample('W').agg({
        'temp': 'mean',        
        'humidity': 'mean',    
        'wind_speed': 'mean',  
        'clouds_all': 'mean',  
        'rain_1h': 'sum'       
    }).reset_index().rename(columns={'dt_iso': 'Tanggal'})
    
    return df_historis_bulanan, df_mingguan.dropna().sort_values(by='Tanggal', ascending=True).head(250)

df_historis, df_mentah = load_data()

# seid bar
st.sidebar.markdown("### 🛠️ SPK Control Panel")
komoditas_pilihan = st.sidebar.selectbox(
    "Pilih Target Komoditas Tanam:",
    list(Data_panen.keys())
)

bulan_target = st.sidebar.selectbox(
    "Rencana Bulan Mulai Tanam:",
    ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
)
list_nama_bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
bulan_angka = list_nama_bulan.index(bulan_target) + 1

menu = st.sidebar.radio("Menu Navigasi Dashboard:", ["Dashboard Utama", "Eksplorasi Data & Tren", "Simulasi FIS Interaktif", "Profil Anggota Kelompok"])

# Kalkulasi Global
hujan_bulanan = df_historis[df_historis['Bulan'] == bulan_angka]['Hujan_Historis_Bulanan'].values[0]
usia_panen_komoditas = Data_panen[komoditas_pilihan]["usia_bulan"]

skor_list, status_list, tgl_panen_list = [], [], []
for _, baris in df_mentah.iterrows():
    # analisis kondisi cuaca
    f_suhu = fz_suhu(baris['temp'])
    f_lembap = fz_kelembapan(baris['humidity'])
    f_angin = fz_angin(baris['wind_speed'])
    f_awan = fz_awan(baris['clouds_all'])
    f_hujan = fz_hujan(baris['rain_1h'])
    
    skor_aktual, _ = cek_kelayakan(f_suhu, f_lembap, f_angin, f_awan, f_hujan, komoditas_pilihan)
    
    # Logika keputusan
    if komoditas_pilihan == "Padi":
        if hujan_bulanan < 45:  
            skor_final = max(10, skor_aktual - 25)
        else:
            skor_final = min(100, skor_aktual + 5)
    elif komoditas_pilihan == "Palawija / Jagung":
        if 35 <= hujan_bulanan <= 100:  
            skor_final = min(100, skor_aktual + 10)
        else:
            skor_final = max(10, skor_aktual - 15)
    else:  
        if hujan_bulanan > 100:  
            skor_final = max(10, skor_aktual - 20)
        else:
            skor_final = skor_aktual

    if skor_final < 45: status_rekomendasi = "Tidak Disarankan"
    elif skor_final < 75: status_rekomendasi = "Cukup Aman (Pantau Lapangan)"
    else: status_rekomendasi = "Sangat Disarankan (Musim & Cuaca Ideal)"
    
    skor_list.append(round(skor_final, 2))
    status_list.append(status_rekomendasi)
    
    # Prediksi masa panen
    estimasi_panen = baris['Tanggal'] + pd.DateOffset(months=usia_panen_komoditas)
    tgl_panen_list.append(estimasi_panen.strftime('%Y-%m-%d'))
    
df_cuaca = df_mentah.copy()
df_cuaca['Skor_Kelayakan'] = skor_list
df_cuaca['Rekomendasi'] = status_list
df_cuaca['Estimasi_Masa_Panen'] = tgl_panen_list

# Tampilan Header
st.title("🌾 SIPETA v5.1")
st.markdown(f"### Kalender Pintar Perencanaan Masa Tanam & Panen Efektif")
st.caption(f"Integrasi Pola Musim Jangka Panjang & Kesiapan Cuaca Lapangan")
st.markdown("---")

# Dashboard utama
if menu == "Dashboard Utama":
    st.markdown(f"## 🗓️ Ringkasan Evaluasi & Prediksi Masa Panen")
    
    # HITUNG ESTIMASI BULAN PANEN SECARA TEORITIS
    index_bulan_panen = (bulan_angka - 1 + usia_panen_komoditas) % 12
    bulan_panen_teoritis = list_nama_bulan[index_bulan_panen]
    
    col_kotak1, col_kotak2, col_kotak3 = st.columns(3)
    with col_kotak1:
        with st.container(border=True):
            st.markdown("#### ⏳ Analisis Pola Tahun Lalu")
            st.metric("Rata-rata Curah Hujan Historis", f"{hujan_bulanan:.2f} mm/bulan")
            if hujan_bulanan < 45: st.error("Klasifikasi: Dominan Kemarau / Kering")
            elif hujan_bulanan <= 100: st.warning("Klasifikasi: Peralihan / Pancaroba")
            else: st.success("Klasifikasi: Musim Hujan Aktif")
                
    with col_kotak2:
        with st.container(border=True):
            st.markdown("#### 🚜 Hasil Kesesuaian Lahan")
            total_data = len(df_cuaca)
            sangat_layak = len(df_cuaca[df_cuaca['Rekomendasi'] == "Sangat Disarankan (Musim & Cuaca Ideal)"])
            st.metric("Minggu Sangat Layak Tanam", f"{sangat_layak} / {total_data} Minggu")
            st.write(f"Komoditas: **{komoditas_pilihan}**")

    with col_kotak3:
        with st.container(border=True):
            st.markdown("#### ⏱️ Prediksi Hasil Masa Panen")
            st.metric("Estimasi Bulan Panen Anda", f"🧺 {bulan_panen_teoritis}")
            st.info(f"Durasi Tanam: **{Data_panen[komoditas_pilihan]['keterangan']}**")

    st.markdown("---")
    
    col_grafik1, col_grafik2 = st.columns([1, 1.2])
    with col_grafik1:
        st.markdown("#### 📊 Distribusi Kelayakan Kalender Tanam")
        st.bar_chart(df_cuaca['Rekomendasi'].value_counts())
        
    with col_grafik2:
        st.markdown("#### 💡 Logika Pengambilan Keputusan Terintegrasi")
        with st.container(border=True):
            st.write(
                f"Sistem ini menggabungkan dua analisis:\n\n"
                f"- **Data Historis Bulanan:** Untuk memperkirakan bulan panen komoditas {komoditas_pilihan} jika mulai ditanam bulan {bulan_target}.\n\n"
                f"- **Kondisi Cuaca Mingguan:** Untuk menguji kelayakan parameter lapangan (suhu, kelembapan, angin, awan, hujan) menggunakan logika fuzzy."
            )

# Eksplorasi data & tren
elif menu == "Eksplorasi Data & Tren":
    st.markdown("### 📈 Grafik Runtun Waktu & Log Tabel Kalender Tanam-Panen")
    
    tab1, tab2 = st.tabs(["Visualisasi Tren Iklim Mingguan", "Tabel Log Transparansi (Tanam & Panen)"])
    with tab1:
        fig_lini_masa = plot_tren_harian(df_cuaca)
        st.pyplot(fig_lini_masa)
    with tab2:
        data_csv = df_cuaca.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Unduh Hasil Kalender Tanam & Panen (.csv)",
            data=data_csv,
            file_name=f"Kalender_Tanam_Panen_{bulan_target}_{komoditas_pilihan}.csv",
            mime="text/csv",
        )
        st.dataframe(
            df_cuaca[['Tanggal', 'Estimasi_Masa_Panen', 'temp', 'humidity', 'wind_speed', 'Skor_Kelayakan', 'Rekomendasi']], 
            use_container_width=True
        )

# Simulasi fis interaktif
elif menu == "Simulasi FIS Interaktif":
    st.markdown("### 🎛️ Ruang Simulasi Pengujian Parameter & Prediksi Waktu")
    col_simulasi1, col_simulasi2 = st.columns([1, 1.8])
    
    with col_simulasi1:
        st.markdown("#### 🎚️ Input Kondisi Cuaca")
        input_suhu = st.slider("Temperatur Rata-rata Seminggu (°C)", 15.0, 40.0, 27.0, 0.1)
        input_lembap = st.slider("Kelembapan Rata-rata Seminggu (%)", 20.0, 100.0, 80.0, 1.0)
        input_angin = st.slider("Kecepatan Angin Rata-rata Seminggu (m/s)", 0.0, 10.0, 2.5, 0.1)
        input_awan = st.slider("Rata-rata Cakupan Awan Seminggu (%)", 0, 100, 40, 1)
        input_hujan = st.slider("Total Akumulasi Hujan Seminggu (mm)", 0.0, 150.0, 10.0, 0.5)
        st.markdown("---")
        tombol_hitung = st.button("🚀 Uji Kelayakan & Prediksi Panen", use_container_width=True)
        
        if tombol_hitung:
            sim_suhu = fz_suhu(input_suhu)
            sim_lembap = fz_kelembapan(input_lembap)
            sim_angin = fz_angin(input_angin)
            sim_awan = fz_awan(input_awan)
            sim_hujan = fz_hujan(input_hujan)
            
            skor_simulasi, _ = cek_kelayakan(sim_suhu, sim_lembap, sim_angin, sim_awan, sim_hujan, komoditas_pilihan)
            
            if komoditas_pilihan == "Padi" and hujan_bulanan < 45:
                skor_simulasi = max(10, skor_simulasi - 25)
            elif komoditas_pilihan == "Palawija / Jagung" and (hujan_bulanan < 35 or hujan_bulanan > 100):
                skor_simulasi = max(10, skor_simulasi - 15)
            elif komoditas_pilihan == "Hortikultura / Sayuran" and hujan_bulanan > 100:
                skor_simulasi = max(10, skor_simulasi - 20)
                
            if skor_simulasi < 45: teks_status = "Tidak Disarankan"
            elif skor_simulasi < 75: teks_status = "Cukup Aman"
            else: teks_status = "Sangat Disarankan"
            
            idx_bulan_panen_sim = (bulan_angka - 1 + usia_panen_komoditas) % 12
            bln_panen_sim = list_nama_bulan[idx_bulan_panen_sim]
            
            st.markdown("#### 🎯 Hasil Keputusan Terintegrasi")
            if teks_status == "Sangat Disarankan": st.success(f"### {teks_status}\n**Skor Akhir: {skor_simulasi}/100**")
            elif teks_status == "Cukup Aman": st.warning(f"### {teks_status}\n**Skor Akhir: {skor_simulasi}/100**")
            else: st.error(f"### {teks_status}\n**Skor Akhir: {skor_simulasi}/100**")
            
            st.info(f"💡 Jika Anda menanam di bulan **{bulan_target}**, maka komoditas ini diperkirakan siap panen pada bulan **{bln_panen_sim}** ({Data_panen[komoditas_pilihan]['keterangan']}).")

    with col_simulasi2:
        st.markdown("#### 📉 Grafik Fungsi Keanggotaan")
        st.pyplot(plot_fuzzy(input_suhu, 'suhu'))
        st.pyplot(plot_fuzzy(input_lembap, 'kelembapan'))
        st.pyplot(plot_fuzzy(input_angin, 'angin'))
        st.pyplot(plot_fuzzy(input_awan, 'awan'))
        st.pyplot(plot_fuzzy(input_hujan, 'hujan'))

# Profil pembuat
elif menu == "Profil Anggota Kelompok":
    st.markdown("### 👥 Profil Anggota Kelompok")
    col_mhs1, col_mhs2 = st.columns(2)
    with col_mhs1:
        with st.container(border=True):
            st.markdown("#### **Muhammad Afif Pratama N**")
            st.write("NIM: 123240031")
    with col_mhs2:
        with st.container(border=True):
            st.markdown("#### **Wahyu Fahri Roisya**")
            st.write("NIM: 123240052")

st.sidebar.markdown("---")
st.sidebar.caption("SIPETA Perencana Masa Tanam v5.1")