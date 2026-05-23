import streamlit as st
import pandas as pd
import numpy as np
import zipfile
import matplotlib.pyplot as plt

# --- 1. CONFIGURATION PAGE ---
st.set_page_config(
    page_title="SIPETA v5.1 - Daily SPK Balanced (Fixed Dark)",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. LOGIKA FUZZY 5 KRITERIA HARIAN ---

# Kriteria 1: Suhu Udara Rata-rata Harian
def fuzzify_suhu(x):
    dingin = np.maximum(0, np.minimum((26 - x) / (26 - 22), 1)) if x <= 26 else 0
    if x <= 24: normal = 0
    elif 24 < x <= 28: normal = (x - 24) / (28 - 24)
    elif 28 < x <= 32: normal = (32 - x) / (32 - 28)
    else: normal = 0
    panas = np.maximum(0, np.minimum((x - 30) / (35 - 30), 1)) if x >= 30 else 0
    return dingin, normal, panas

# Kriteria 2: Kelembapan Udara Rata-rata Harian
def fuzzify_kelembapan(x):
    rendah = np.maximum(0, np.minimum((65 - x) / (65 - 45), 1)) if x <= 65 else 0
    if x <= 55: sedang = 0
    elif 55 < x <= 75: sedang = (x - 55) / (75 - 55)
    elif 75 < x <= 88: sedang = (88 - x) / (88 - 75)
    else: sedang = 0
    tinggi = np.maximum(0, np.minimum((x - 80) / (98 - 80), 1)) if x >= 80 else 0
    return rendah, sedang, tinggi

# Kriteria 3: Kecepatan Angin Rata-rata Harian
def fuzzify_angin(x):
    pelan = np.maximum(0, np.minimum((3.5 - x) / (3.5 - 1.5), 1)) if x <= 3.5 else 0
    kencang = np.maximum(0, np.minimum((x - 2.5) / (5.5 - 2.5), 1)) if x >= 2.5 else 0
    return pelan, kencang

# Kriteria 4: Rata-rata Cakupan Awan Harian
def fuzzify_awan(x):
    cerah = np.maximum(0, np.minimum((50 - x) / (50 - 0), 1)) if x <= 50 else 0
    mendung = np.maximum(0, np.minimum((x - 35) / (85 - 35), 1)) if x >= 35 else 0
    return cerah, mendung

# Kriteria 5: Total Akumulasi Curah Hujan Harian (mm/hari)
def fuzzify_hujan(x):
    kering = np.maximum(0, np.minimum((2.0 - x) / 2.0, 1)) if x <= 2.0 else 0
    basah = np.maximum(0, np.minimum((x - 1.0) / 15.0, 1)) if x >= 1.0 else 0
    return kering, basah


# MESIN INFERENSI
def rule_inference(suhu_opt, lembap_opt, angin_opt, awan_opt, hujan_opt, komoditas):
    d, n, p = suhu_opt
    r, s, t = lembap_opt
    ap, ak = angin_opt
    cr, md = awan_opt
    kr, bs = hujan_opt
    
    sangat_cocok = 0
    cukup_cocok = 0
    tidak_cocok = 0
    
    if komoditas == "Padi (Rentan Angin Kencang/Roboh)":
        r1 = min(n, t, ap, bs)       
        r2 = min(n, s, ap, kr)       
        r3 = min(p, r, ap, kr)       
        r4 = min(n, t, ak, md)       
        
        sangat_cocok = r1
        cukup_cocok = max(r2, min(n, t, ap, cr, kr))
        tidak_cocok = max(r3, r4)
        
    elif komoditas == "Palawija / Jagung (Butuh Air Sedang)":
        r1 = min(n, s, ap, cr, kr)   
        r2 = min(p, r, ap, cr, kr)   
        r3 = min(d, t, ap, md, bs)   
        r4 = min(n, t, ak, bs)       
        
        sangat_cocok = r1
        cukup_cocok = max(r2, min(n, s, ap, md, kr))
        tidak_cocok = max(r3, r4)
        
    else: 
        r1 = min(d, s, ap, cr, kr)   
        r2 = min(n, s, ap, cr, kr)   
        r3 = min(p, r, ap, cr, kr)   
        r4 = min(n, t, ak, md, bs)   
        
        sangat_cocok = r1
        cukup_cocok = r2
        tidak_cocok = max(r3, r4)

    w_tidak, w_cukup, w_sangat = 20, 60, 90
    total_bobot = tidak_cocok + cukup_cocok + sangat_cocok
    
    if total_bobot == 0: 
        return 50, "Cukup Cocok"
    
    skor = ((tidak_cocok * w_tidak) + (cukup_cocok * w_cukup) + (sangat_cocok * w_sangat)) / total_bobot
    
    if skor < 45: status = "Tidak Cocok"
    elif skor < 75: status = "Cukup Cocok"
    else: status = "Sangat Cocok"
    
    return round(skor, 2), status

# --- 3. FIXED DARK GRAPH GENERATOR ---
def plot_membership_functions(input_val, type='suhu'):
    # Warna dikunci ke Hitam/Gelap secara permanen
    text_color = 'white'
    face_color = '#0e1117' 
    
    fig, ax = plt.subplots(figsize=(6, 1.5), facecolor=face_color)
    ax.set_facecolor(face_color)
    ax.tick_params(colors=text_color)
    ax.title.set_color(text_color)
    
    if type == 'suhu':
        x = np.linspace(15, 40, 500)
        ax.plot(x, [fuzzify_suhu(i)[0] for i in x], label='Dingin', color='#1E88E5')
        ax.plot(x, [fuzzify_suhu(i)[1] for i in x], label='Normal', color='#4CAF50')
        ax.plot(x, [fuzzify_suhu(i)[2] for i in x], label='Panas', color='#E53935')
        ax.axvline(input_val, color=text_color, linestyle='--')
        ax.set_title("Kriteria 1: Keanggotaan Suhu Rata-rata Harian (°C)")
    elif type == 'humidity':
        x = np.linspace(20, 100, 500)
        ax.plot(x, [fuzzify_kelembapan(i)[0] for i in x], label='Rendah', color='#FFB300')
        ax.plot(x, [fuzzify_kelembapan(i)[1] for i in x], label='Sedang', color='#8E24AA')
        ax.plot(x, [fuzzify_kelembapan(i)[2] for i in x], label='Tinggi', color='#00ACC1')
        ax.axvline(input_val, color=text_color, linestyle='--')
        ax.set_title("Kriteria 2: Keanggotaan Kelembapan Rata-rata Harian (%)")
    elif type == 'wind':
        x = np.linspace(0, 8, 500)
        ax.plot(x, [fuzzify_angin(i)[0] for i in x], label='Pelan', color='#00897B')
        ax.plot(x, [fuzzify_angin(i)[1] for i in x], label='Kencang', color='#D81B60')
        ax.axvline(input_val, color=text_color, linestyle='--')
        ax.set_title("Kriteria 3: Kecepatan Angin Rata-rata Harian (m/s)")
    elif type == 'cloud':
        x = np.linspace(0, 100, 500)
        ax.plot(x, [fuzzify_awan(i)[0] for i in x], label='Cerah', color='#F57C00')
        ax.plot(x, [fuzzify_awan(i)[1] for i in x], label='Mendung', color='#78909C')
        ax.axvline(input_val, color=text_color, linestyle='--')
        ax.set_title("Kriteria 4: Rata-rata Cakupan Awan Harian (%)")
    else:
        x = np.linspace(0, 40, 500)
        ax.plot(x, [fuzzify_hujan(i)[0] for i in x], label='Kering', color='#8D6E63')
        ax.plot(x, [fuzzify_hujan(i)[1] for i in x], label='Basah', color='#29B6F6')
        ax.axvline(input_val, color=text_color, linestyle='--')
        ax.set_title("Kriteria 5: Total Akumulasi Hujan Harian (mm)")
        
    ax.legend(loc='upper right', fontsize='xx-small', framealpha=0.3)
    ax.grid(True, alpha=0.15, color=text_color)
    return fig

# --- SUBPLOT TIME-SERIES DAILY UNTUK MENU 2 ---
def plot_daily_time_series(df_timeline):
    df_sorted = df_timeline.sort_values(by='Tanggal', ascending=True)
    
    text_color = 'white'
    face_color = '#0e1117'
    grid_color = '#444444'
    
    fig, axes = plt.subplots(5, 1, figsize=(11, 8.5), sharex=True, facecolor=face_color)
    colors = ['#E53935', '#00ACC1', '#00897B', '#F57C00', '#29B6F6']
    labels = ['Suhu Rata² (°C)', 'Kelembapan Rata² (%)', 'Angin Rata² (m/s)', 'Awan Rata² (%)', 'Total Hujan (mm)']
    columns = ['temp', 'humidity', 'wind_speed', 'clouds_all', 'rain_1h']
    
    for i, ax in enumerate(axes):
        ax.set_facecolor(face_color)
        ax.plot(df_sorted['Tanggal'], df_sorted[columns[i]], color=colors[i], linewidth=1.5)
        ax.set_ylabel(labels[i], color=text_color, fontsize=9)
        ax.tick_params(colors=text_color, labelsize=8)
        ax.grid(True, alpha=0.25, color=grid_color)
        
    axes[0].set_title("Analisis Runtun Waktu Makro-Klimatologi 250 Hari Berkelanjutan (Era 2019+)", color=text_color, fontsize=12)
    axes[4].set_xlabel('Timeline Tanggal Berkelanjutan (Hasil Resampling Harian)', color=text_color)
    
    plt.xticks(rotation=25, ha='right')
    fig.autofmt_xdate()
    plt.tight_layout()
    return fig

# --- 4. DATA PIPELINE ---
@st.cache_data
def load_and_process_daily_250_days():
    zip_path = "openweatherdata-denpasar-1990-2020.csv.zip"
    csv_name = "openweatherdata-denpasar-1990-2020.csv"
    
    with zipfile.ZipFile(zip_path, 'r') as z:
        with z.open(csv_name) as f:
            df = pd.read_csv(f)
            
    df['dt_iso'] = pd.to_datetime(df['dt_iso'].str.replace(' +0000 UTC', '', regex=False))
    df['rain_1h'] = df['rain_1h'].fillna(0)
    
    df_modern = df[df['dt_iso'].dt.year >= 2019].copy()
    df_modern.set_index('dt_iso', inplace=True)
    
    df_daily = df_modern.resample('D').agg({
        'temp': 'mean',        
        'humidity': 'mean',    
        'wind_speed': 'mean',  
        'clouds_all': 'mean',  
        'rain_1h': 'sum'       
    })
    
    df_daily = df_daily.reset_index().rename(columns={'dt_iso': 'Tanggal'})
    df_daily = df_daily.dropna()
    
    df_daily = df_daily.sort_values(by='Tanggal', ascending=True)
    return df_daily.head(250)

df_raw = load_and_process_daily_250_days()

# --- 5. SIDEBAR CONTROL PANEL ---
st.sidebar.markdown("### 🛠️ SPK Control Panel")
komoditas_pilihan = st.sidebar.selectbox(
    "Pilih Target Komoditas Tanam:",
    ["Padi (Rentan Angin Kencang/Roboh)", "Palawija / Jagung (Butuh Air Sedang)", "Hortikultura / Sayuran"]
)

menu = st.sidebar.radio("Menu Navigasi Dashboard:", ["Dashboard Utama", "Eksplorasi Data & Tren", "Simulasi FIS Interaktif"])

# --- 6. PRE-CALCULATION GLOBAL ---
skor_list, status_list = [], []
for _, row in df_raw.iterrows():
    s_opt = fuzzify_suhu(row['temp'])
    h_opt = fuzzify_kelembapan(row['humidity'])
    w_opt = fuzzify_angin(row['wind_speed'])
    c_opt = fuzzify_awan(row['clouds_all'])
    r_opt = fuzzify_hujan(row['rain_1h'])
    
    skor, status = rule_inference(s_opt, h_opt, w_opt, c_opt, r_opt, komoditas_pilihan)
    skor_list.append(skor)
    status_list.append(status)
    
df_cuaca = df_raw.copy()
df_cuaca['Skor_Kelayakan'] = skor_list
df_cuaca['Rekomendasi'] = status_list

# --- HEADER LAYOUT ---
st.title("🌾 SIPETA v5.1")
st.markdown(f"### SPK Perencanaan Tanam - Transformasi 250 Hari Berkelanjutan")
st.caption(f"Fuzzy Inference System | **5 Kriteria Klimatologi Seimbang** | Komoditas: **{komoditas_pilihan}**")
st.markdown("---")

# --- MENU 1: DASHBOARD UTAMA ---
if menu == "Dashboard Utama":
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    col_kpi1.metric("Rata-rata Suhu Rentang Data", f"{df_cuaca['temp'].mean():.2f} °C")
    col_kpi2.metric("Rata-rata Kelembapan Udara", f"{df_cuaca['humidity'].mean():.1f} %")
    col_kpi3.metric("Rata-rata Kecepatan Angin", f"{df_cuaca['wind_speed'].mean():.2f} m/s")
    col_kpi4.metric("Total Garis Waktu", f"{len(df_cuaca)} Hari Berkelanjutan")

    st.markdown("---")
    
    col_graph1, col_graph2 = st.columns([1, 1.2])
    with col_graph1:
        st.markdown("#### 📊 Distribusi Hasil Kelayakan Tanam")
        st.bar_chart(df_cuaca['Rekomendasi'].value_counts())
        
    with col_graph2:
        st.markdown("#### 💡 Catatan Kalibrasi Logika Fuzzy")
        with st.container(border=True):
            st.markdown(f"**Mengapa Hasilnya Sekarang Sangat Ideal?**")
            st.write(
                f"1. **Normalisasi Parameter Angin:** Masalah 'Tidak Cocok Semua' berhasil diatasi dengan mengubah agregasi angin menjadi nilai **Rata-rata Harian (`mean`)**.\n\n"
                f"2. **Kronologis 250 Hari Realistis:** Dengan menyajikan 250 hari berturut-turut dari era modern 2019+, sistem berhasil menangkap siklus iklim harian Bali secara objektif.\n\n"
                f"3. **Grafik Terkunci Gelap:** Semua visualisasi grafik Matplotlib sekarang dikunci secara absolut pada tema hitam/gelap agar visualisasi terlihat kontras, elegan, dan konsisten."
            )

# --- MENU 2: EKSPLORASI DATA & TREN ---
elif menu == "Eksplorasi Data & Tren":
    st.markdown("### 📈 Grafik Runtun Waktu Berkelanjutan (Skala 250 Hari)")
    st.write("Grafik kronologis di bawah ini memetakan pergerakan cuaca harian maju secara kontinu.")
    
    tab1, tab2 = st.tabs(["Visualisasi Tren Iklim Harian", "Tabel Log Transparansi Data"])
    with tab1:
        fig_timeline = plot_daily_time_series(df_cuaca)
        st.pyplot(fig_timeline)
    with tab2:
        st.dataframe(
            df_cuaca[['Tanggal', 'temp', 'humidity', 'wind_speed', 'clouds_all', 'rain_1h', 'Skor_Kelayakan', 'Rekomendasi']], 
            use_container_width=True
        )

# --- MENU 3: SIMULASI FIS INTERAKTIF ---
elif menu == "Simulasi FIS Interaktif":
    st.markdown("### 🎛️ Ruang Simulasi Pengujian 5 Parameter Fuzzy")
    
    col_sim1, col_sim2 = st.columns([1, 1.8])
    
    with col_sim1:
        st.markdown("#### 🎚️ Input Slider Kontrol (1 Hari)")
        in_suhu = st.slider("Temperatur Rata-rata Sehari (°C)", 15.0, 40.0, 27.0, 0.1)
        in_humi = st.slider("Kelembapan Rata-rata Sehari (%)", 20.0, 100.0, 80.0, 1.0)
        in_wind = st.slider("Kecepatan Angin Rata-rata Sehari (m/s)", 0.0, 10.0, 2.5, 0.1)
        in_cloud = st.slider("Rata-rata Cakupan Awan Sehari (%)", 0, 100, 40, 1)
        in_rain = st.slider("Total Akumulasi Hujan Sehari (mm/hari)", 0.0, 50.0, 0.0, 0.5)
        
        # Eksekusi FIS
        s_fz = fuzzify_suhu(in_suhu)
        h_fz = fuzzify_kelembapan(in_humi)
        w_fz = fuzzify_angin(in_wind)
        c_fz = fuzzify_awan(in_cloud)
        r_fz = fuzzify_hujan(in_rain)
        
        skor_f, stat_f = rule_inference(s_fz, h_fz, w_fz, c_fz, r_fz, komoditas_pilihan)
        
        st.markdown("---")
        st.markdown("#### 🎯 Hasil Keputusan SPK")
        if stat_f == "Sangat Cocok": st.success(f"### {stat_f}\n**Skor Kelayakan: {skor_f}/100**")
        elif stat_f == "Cukup Cocok": st.warning(f"### {stat_f}\n**Skor Kelayakan: {skor_f}/100**")
        else: st.error(f"### {stat_f}\n**Skor Kelayakan: {skor_f}/100**")
        
    with col_sim2:
        st.markdown("#### 📉 Grafik Fungsi Keanggotaan Dinamis (5 Kriteria)")
        
        st.pyplot(plot_membership_functions(in_suhu, 'suhu'))
        st.pyplot(plot_membership_functions(in_humi, 'humidity'))
        st.pyplot(plot_membership_functions(in_wind, 'wind'))
        st.pyplot(plot_membership_functions(in_cloud, 'cloud'))
        st.pyplot(plot_membership_functions(in_rain, 'rain'))

st.sidebar.markdown("---")
st.sidebar.caption("SIPETA Multi-Criteria SPK Project v5.1")
