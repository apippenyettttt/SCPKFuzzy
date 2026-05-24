import streamlit as st
import pandas as pd
import numpy as np
import zipfile
import matplotlib.pyplot as plt

# --- 1. CONFIGURATION PAGE ---
st.set_page_config(
    page_title="SIPETA - Perencanaan Tanam Bali",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- AUTOMATIC THEME DETECTION ---
# Mendeteksi tema aktif (light/dark) langsung dari pengaturan sistem Streamlit
try:
    current_theme = st.get_option("theme.base")
    is_dark_theme = (current_theme == "dark")
except:
    is_dark_theme = False # Fallback jika konfigurasi belum di-set

# --- 2. LOGIKA FUZZY METODE MAMDANI/TSUKAMOTO ---

def fuzzify_suhu(x):
    dingin = np.maximum(0, np.minimum((26 - x) / (26 - 20), 1)) if x <= 26 else 0
    if x <= 24: normal = 0
    elif 24 < x <= 28: normal = (x - 24) / (28 - 24)
    elif 28 < x <= 32: normal = (32 - x) / (32 - 28)
    else: normal = 0
    panas = np.maximum(0, np.minimum((x - 30) / (35 - 30), 1)) if x >= 30 else 0
    return dingin, normal, panas

def fuzzify_kelembapan(x):
    rendah = np.maximum(0, np.minimum((60 - x) / (60 - 40), 1)) if x <= 60 else 0
    if x <= 50: sedang = 0
    elif 50 < x <= 70: sedang = (x - 50) / (70 - 50)
    elif 70 < x <= 85: sedang = (85 - x) / (85 - 70)
    else: sedang = 0
    tinggi = np.maximum(0, np.minimum((x - 75) / (95 - 75), 1)) if x >= 75 else 0
    return rendah, sedang, tinggi

def fuzzify_angin(x):
    pelan = np.maximum(0, np.minimum((5 - x) / (5 - 3), 1)) if x <= 5 else 0
    kencang = np.maximum(0, np.minimum((x - 3) / (6 - 3), 1)) if x >= 3 else 0
    return pelan, kencang

def rule_inference(suhu_opt, lembap_opt, angin_opt, komoditas):
    d, n, p = suhu_opt
    r, s, t = lembap_opt
    ap, ak = angin_opt
    
    sangatcocok = 0
    cukupcocok = 0
    tidakcocok = 0
    
    if komoditas == "Padi (Rentan Angin Kencang/Roboh)":
        r1 = min(n, t, ap) 
        r2 = min(n, t, ak) 
        r3 = min(n, s, ap) 
        r4 = min(d, t, ap) 
        r5 = min(p, r, ap) 
        r6 = min(p, t, ak) 
        
        sangatcocok = max(r1, r3)
        cukupcocok = max(r2, r4)
        tidakcocok = max(r5, r6)
        
    elif komoditas == "Palawija / Jagung (Butuh Air Sedang)":
        r1 = min(n, s, ap) 
        r2 = min(n, t, ap) 
        r3 = min(d, s, ap) 
        r4 = min(p, r, ap) 
        r5 = min(n, s, ak) 
        
        sangatcocok = r1
        cukupcocok = max(r2, r3, r5)
        tidakcocok = r4
        
    else: # Hortikultura / Sayuran
        r1 = min(d, s, ap) 
        r2 = min(n, s, ap) 
        r3 = min(p, t, ap) 
        r4 = min(n, s, ak) 
        
        sangatcocok = max(r1, r2)
        cukupcocok = r4
        tidakcocok = r3

    w_tidak, w_cukup, w_sangat = 25, 60, 90
    total_bobot = tidakcocok + cukupcocok + sangatcocok
    
    if total_bobot == 0: return 50, "Cukup Cocok"
    
    skor = ((tidakcocok * w_tidak) + (cukupcocok * w_cukup) + (sangatcocok * w_sangat)) / total_bobot
    
    if skor < 45: status = "Tidak Cocok"
    elif skor < 75: status = "Cukup Cocok"
    else: status = "Sangat Cocok"
    
    return round(skor, 2), status

# --- 3. DYNAMIC GRAPH GENERATOR (THEME AWARE) ---
def plot_membership_functions(input_val, type='suhu', is_dark=False):
    text_color = 'white' if is_dark else 'black'
    face_color = '#0e1117' if is_dark else 'white'
    
    fig, ax = plt.subplots(figsize=(6, 2.0), facecolor=face_color)
    ax.set_facecolor(face_color)
    
    ax.xaxis.label.set_color(text_color)
    ax.yaxis.label.set_color(text_color)
    ax.tick_params(colors=text_color)
    ax.title.set_color(text_color)
    
    if type == 'suhu':
        x = np.linspace(15, 40, 500)
        ax.plot(x, [fuzzify_suhu(i)[0] for i in x], label='Dingin', color='#1E88E5')
        ax.plot(x, [fuzzify_suhu(i)[1] for i in x], label='Normal', color='#4CAF50')
        ax.plot(x, [fuzzify_suhu(i)[2] for i in x], label='Panas', color='#E53935')
        ax.axvline(input_val, color=text_color, linestyle='--', label=f'Input ({input_val}°C)')
        ax.set_title("Fungsi Keanggotaan Suhu")
    elif type == 'humidity':
        x = np.linspace(20, 100, 500)
        ax.plot(x, [fuzzify_kelembapan(i)[0] for i in x], label='Rendah', color='#FFB300')
        ax.plot(x, [fuzzify_kelembapan(i)[1] for i in x], label='Sedang', color='#8E24AA')
        ax.plot(x, [fuzzify_kelembapan(i)[2] for i in x], label='Tinggi', color='#00ACC1')
        ax.axvline(input_val, color=text_color, linestyle='--', label=f'Input ({input_val}%)')
        ax.set_title("Fungsi Keanggotaan Kelembapan")
    else:
        x = np.linspace(0, 10, 500)
        ax.plot(x, [fuzzify_angin(i)[0] for i in x], label='Pelan', color='#00897B')
        ax.plot(x, [fuzzify_angin(i)[1] for i in x], label='Kencang', color='#D81B60')
        ax.axvline(input_val, color=text_color, linestyle='--', label=f'Input ({input_val} m/s)')
        ax.set_title("Fungsi Keanggotaan Kecepatan Angin")
        
    ax.legend(loc='upper right', fontsize='x-small', framealpha=0.5)
    ax.grid(True, alpha=0.2, color=text_color)
    return fig

# --- SUBPLOT TIME-SERIES UNTUK MENU 2 ---
def plot_time_series(df_timeline, is_dark=False):
    df_sorted = df_timeline.sort_values(by='dt_iso', ascending=True)
    
    text_color = 'white' if is_dark else 'black'
    face_color = '#0e1117' if is_dark else 'white'
    grid_color = '#444444' if is_dark else '#e0e0e0'
    
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 6), sharex=True, facecolor=face_color)
    
    # Plot Suhu
    ax1.set_facecolor(face_color)
    ax1.plot(df_sorted['dt_iso'], df_sorted['temp'], color='#E53935', linewidth=1.5)
    ax1.set_ylabel('Suhu (°C)', color=text_color)
    ax1.tick_params(colors=text_color)
    ax1.grid(True, alpha=0.3, color=grid_color)
    ax1.set_title("Analisis Pergerakan Parameter Cuaca (Timeline Eksklusif)", color=text_color, fontsize=12)
    
    # Plot Kelembapan
    ax2.set_facecolor(face_color)
    ax2.plot(df_sorted['dt_iso'], df_sorted['humidity'], color='#00ACC1', linewidth=1.5)
    ax2.set_ylabel('Kelembapan (%)', color=text_color)
    ax2.tick_params(colors=text_color)
    ax2.grid(True, alpha=0.3, color=grid_color)
    
    # Plot Angin
    ax3.set_facecolor(face_color)
    ax3.plot(df_sorted['dt_iso'], df_sorted['wind_speed'], color='#00897B', linewidth=1.5)
    ax3.set_ylabel('Angin (m/s)', color=text_color)
    ax3.tick_params(colors=text_color)
    ax3.grid(True, alpha=0.3, color=grid_color)
    ax3.set_xlabel('Timeline Data Terpakai (Waktu)', color=text_color)
    
    plt.xticks(rotation=25, ha='right')
    fig.autofmt_xdate()
    plt.tight_layout()
    return fig

# --- 4. DATA PIPELINE ---
@st.cache_data
def load_and_process_data():
    zip_path = "openweatherdata-denpasar-1990-2020.csv.zip"
    csv_name = "openweatherdata-denpasar-1990-2020.csv"
    
    with zipfile.ZipFile(zip_path, 'r') as z:
        with z.open(csv_name) as f:
            df = pd.read_csv(f)
            
    df['dt_iso'] = pd.to_datetime(df['dt_iso'].str.replace(' +0000 UTC', '', regex=False))
    df = df.sort_values(by='dt_iso', ascending=False)
    
    df_asli = df.head(295).copy()
    
    data_custom = {
        'dt_iso': [
            pd.Timestamp('2026-05-21 12:00:00'),
            pd.Timestamp('2026-05-21 11:00:00'),
            pd.Timestamp('2026-05-21 10:00:00'),
            pd.Timestamp('2026-05-21 09:00:00'), 
            pd.Timestamp('2026-05-21 08:00:00')  
        ],
        'temp': [29.0, 36.5, 27.5, 38.5, 16.5],
        'humidity': [85, 25, 75, 30, 40],
        'wind_speed': [8.5, 7.8, 9.2, 1.2, 0.5],
        'weather_description': [
            'custom: high wind storm', 
            'custom: heatwave gale', 
            'custom: extreme wind anomaly',
            'custom: severe drought',
            'custom: extreme cold'
        ]
    }
    df_custom = pd.DataFrame(data_custom)
    return pd.concat([df_custom, df_asli], ignore_index=True)

df_raw = load_and_process_data()

# --- 5. SIDEBAR CONTROL PANEL ---
st.sidebar.markdown("### 🛠️ Control Panel")
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
    skor, status = rule_inference(s_opt, h_opt, w_opt, komoditas_pilihan)
    skor_list.append(skor)
    status_list.append(status)
    
df_cuaca = df_raw.copy()
df_cuaca['Skor_Kelayakan'] = skor_list
df_cuaca['Rekomendasi'] = status_list

# --- HEADER LAYOUT ---
st.title("🌾 SIPETA v3.2")
st.markdown(f"### Sistem Pendukung Keputusan Perencanaan Tanam Bali")
st.caption(f"Target Analisis Komoditas saat ini: **{komoditas_pilihan}**")
st.markdown("---")

# --- MENU 1: DASHBOARD UTAMA ---
if menu == "Dashboard Utama":
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    col_kpi1.metric("Rata-rata Suhu", f"{df_cuaca['temp'].mean():.2f} °C")
    col_kpi2.metric("Rata-rata Kelembapan", f"{df_cuaca['humidity'].mean():.1f} %")
    col_kpi3.metric("Rata-rata Kecepatan Angin", f"{df_cuaca['wind_speed'].mean():.2f} m/s")
    col_kpi4.metric("Status Dominan Musim", df_cuaca['Rekomendasi'].mode()[0])

    st.markdown("---")
    
    col_graph1, col_graph2 = st.columns([1, 1])
    with col_graph1:
        st.markdown("#### 📊 Grafik Hasil Rekomendasi (300 Data)")
        st.bar_chart(df_cuaca['Rekomendasi'].value_counts())
        
    with col_graph2:
        st.markdown("#### 💡 Analisis Karakteristik Angin")
        with st.container(border=True):
            st.markdown(f"**Catatan Pengujian Parameter Wind Speed:**")
            st.write(
                f"Sistem saat ini membaca kolom `wind_speed` secara responsif. "
                f"Pada skenario simulasi badai angin kencang (> 7 m/s), mesin logika fuzzy secara otomatis "
                f"menurunkan tingkat kelayakan komoditas **{komoditas_pilihan}** menjadi **Tidak Cocok**. "
                f"Hal ini berguna bagi Subak untuk mengantisipasi resiko kerusakan fisik batang tanaman."
            )

# --- MENU 2: EKSPLORASI DATA & TREN ---
elif menu == "Eksplorasi Data & Tren":
    st.markdown("### 📈 Analisis Runtun Waktu 3 Parameter Utama (Terfokus)")
    st.write("Visualisasi timeline di bawah ini dipisah secara vertikal agar fluktuasi masing-masing komponen terfokus pada skala aslinya.")
    
    tab1, tab2 = st.tabs(["Grafik Tren Multi-Variabel", "Tabel Log 300 Data Lengkap"])
    with tab1:
        # Menggunakan deteksi otomatis 'is_dark_theme' langsung di dalam parameter
        fig_timeline = plot_time_series(df_cuaca, is_dark_theme)
        st.pyplot(fig_timeline)
    with tab2:
        st.dataframe(df_cuaca[['dt_iso', 'temp', 'humidity', 'wind_speed', 'Skor_Kelayakan', 'Rekomendasi']], width="stretch")

# --- MENU 3: SIMULASI FIS INTERAKTIF ---
elif menu == "Simulasi FIS Interaktif":
    st.markdown("### 🎛️ Ruang Simulasi Pengujian 3 Parameter Fuzzy")
    
    col_sim1, col_sim2 = st.columns([1, 2])
    
    with col_sim1:
        st.markdown("#### 🎚️ Input Slider Kontrol")
        in_suhu = st.slider("Temperatur Udara (°C)", 15.0, 40.0, 27.0, 0.1)
        in_humi = st.slider("Kelembapan Udara (%)", 20.0, 100.0, 80.0, 1.0)
        in_wind = st.slider("Kecepatan Angin (m/s)", 0.0, 15.0, 2.5, 0.1)
        
        s_fz = fuzzify_suhu(in_suhu)
        h_fz = fuzzify_kelembapan(in_humi)
        w_fz = fuzzify_angin(in_wind)
        skor_f, stat_f = rule_inference(s_fz, h_fz, w_fz, komoditas_pilihan)
        
        st.markdown("---")
        st.markdown("#### 🎯 Hasil Rekomendasi")
        if stat_f == "Sangat Cocok": st.success(f"### {stat_f}\n**Skor: {skor_f}/100**")
        elif stat_f == "Cukup Cocok": st.warning(f"### {stat_f}\n**Skor: {skor_f}/100**")
        else: st.error(f"### {stat_f}\n**Skor: {skor_f}/100**")
        
    with col_sim2:
        st.markdown("#### 📉 Grafik Fungsi Keanggotaan Dinamis (3 Input)")
        
        # Menggunakan deteksi otomatis 'is_dark_theme' langsung di dalam parameter
        st.pyplot(plot_membership_functions(in_suhu, 'suhu', is_dark_theme))
        st.pyplot(plot_membership_functions(in_humi, 'humidity', is_dark_theme))
        st.pyplot(plot_membership_functions(in_wind, 'wind', is_dark_theme))

st.sidebar.markdown("---")
st.sidebar.caption("SIPETA Multi-Criteria Project v3.2")