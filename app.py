import streamlit as st

# Must be the first Streamlit command
st.set_page_config(page_title="Analisis Chatbot KAWAN", layout="wide")

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import requests
from datetime import datetime, timedelta

# =====================================
# 🔹 Load Data
# =====================================
@st.cache_data
def fetch_data_from_api(url):
    params = {"action": "read-history-message"}
    try:
        response = requests.get(url, params=params)
        data = response.json()
        df = pd.DataFrame(data['records'])
        
        # Convert timestamp to datetime
        df['datetime'] = pd.to_datetime(df['currentTime'], format='%d/%m/%Y, %H.%M.%S', errors='coerce')
        
        # Convert timestamp (milliseconds) to datetime as backup if currentTime parsing fails
        df.loc[df['datetime'].isna(), 'datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Add source column to track which API the data came from
        df['source'] = url.split('/')[-2][:10] + '...'  # Short version of API ID
        
        return df
    except Exception as e:
        st.error(f"Error loading data from {url}: {str(e)}")
        return pd.DataFrame()

@st.cache_data
def load_data():
    # URLs for both APIs
    urls = [
        "https://script.google.com/macros/s/AKfycbwXynUCMX_pLTl1UU8UcbQzbrxvV9wsyloHEkrFH4vOCIrz4MaQ_B8HFrxgJ5L_Qmrz/exec",
        "https://script.google.com/macros/s/AKfycbxryhvmXetPamDTnX0PwgdQmo0t7dluEPIPHajXMRb4j0Res05WrPbM-lEMfBG3_39oMQ/exec"
    ]
    
    # Fetch data from both sources
    dfs = [fetch_data_from_api(url) for url in urls]
    
    # Combine the dataframes
    combined_df = pd.concat(dfs, ignore_index=True)
    
    # Remove duplicates based on id and message
    combined_df = combined_df.drop_duplicates(subset=['id', 'message'])
    
    return combined_df

df = load_data()

# =====================================
# 🔹 Header
# =====================================
st.title("🤖 Analisis History Chatbot KAWAN")
st.markdown("Dashboard interaktif untuk menganalisis percakapan chatbot KAWAN berdasarkan data history pesan.")

# =====================================
# 🔹 Sidebar
# =====================================
st.sidebar.header("⚙️ Filter Data")

# Filter by data source
# sources = df['source'].unique()
# selected_source = st.sidebar.selectbox("Pilih Sumber Data:", options=["Semua"] + list(sources))

# if selected_source != "Semua":
#     df = df[df['source'] == selected_source]

# Filter by user
users = df['no'].unique()
selected_user = st.sidebar.selectbox("Pilih User:", options=["Semua"] + list(users))

if selected_user != "Semua":
    df = df[df['no'] == selected_user]

date_range = st.sidebar.date_input(
    "Pilih Rentang Tanggal:",
    [df['datetime'].min().date(), df['datetime'].max().date()]
)

df = df[(df['datetime'].dt.date >= date_range[0]) & (df['datetime'].dt.date <= date_range[1])]

# =====================================
# 🔹 Statistik Ringkas
# =====================================
st.subheader("📊 Statistik Ringkas")

# Calculate working hours response time
def calculate_working_hours(start, end):
    """Menghitung waktu respon dalam jam kerja."""
    work_start_time = datetime.strptime('08:00', '%H:%M').time()
    work_end_time = datetime.strptime('20:00', '%H:%M').time()

    if start.time() > work_end_time:
        start = datetime.combine(start.date() + timedelta(days=1), work_start_time)
    if end.time() < work_start_time:
        end = datetime.combine(end.date() - timedelta(days=1), work_end_time)

    if start.time() < work_start_time:
        start = datetime.combine(start.date(), work_start_time)
    if end.time() > work_end_time:
        end = datetime.combine(end.date(), work_end_time)

    total_seconds = 0
    while start.date() <= end.date():
        work_start = datetime.combine(start.date(), work_start_time)
        work_end = datetime.combine(start.date(), work_end_time)
        if start > work_end:
            start = work_start + timedelta(days=1)
            continue
        if end < work_start:
            break
        total_seconds += (min(end, work_end) - max(start, work_start)).total_seconds()
        start = work_start + timedelta(days=1)
    return total_seconds

def calculate_avg_response_time(df):
    df_sorted = df.sort_values('datetime').copy()
    response_times = []
    response_times_raw = []  # For raw time (including non-working hours)
    
    bot_no = "https://script.google.com/macros/s/AKfycbxryhvmXetPamDTnX0PwgdQmo0t7dluEPIPHajXMRb4j0Res05WrPbM-lEMfBG3_39oMQ/exec"
    
    for i in range(len(df_sorted) - 1):
        current_row = df_sorted.iloc[i]
        next_row = df_sorted.iloc[i + 1]
        
        # Check if current message is 'receive' and next is 'send' from bot
        if (current_row['status'] == 'receive' and 
            next_row['status'] == 'send' and 
            next_row['no'] == bot_no):
            
            # Calculate working hours response time
            work_time = calculate_working_hours(
                current_row['datetime'],
                next_row['datetime']
            )
            
            # Calculate raw response time
            raw_time = (next_row['datetime'] - current_row['datetime']).total_seconds()
            
            if 0 < work_time < 600:  # Max 10 minutes threshold
                response_times.append(work_time)
                response_times_raw.append(raw_time)
    
    if response_times:
        # Calculate statistics for working hours
        avg_time = sum(response_times) / len(response_times)
        median_time = sorted(response_times)[len(response_times)//2]
        
        # Calculate statistics for raw time
        avg_time_raw = sum(response_times_raw) / len(response_times_raw)
        median_time_raw = sorted(response_times_raw)[len(response_times_raw)//2]
        
        def format_time(seconds):
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes} menit {secs} detik"
        
        stats = {
            'avg': format_time(avg_time),
            'avg_raw': format_time(avg_time_raw),
            'median': format_time(median_time),
            'median_raw': format_time(median_time_raw),
            'min': f"{int(min(response_times))} detik",
            'max': f"{int(max(response_times))} detik",
            'total_samples': len(response_times)
        }
        return stats
    
    return {
        'avg': "N/A",
        'avg_raw': "N/A",
        'median': "N/A",
        'median_raw': "N/A",
        'min': "N/A",
        'max': "N/A",
        'total_samples': 0
    }

response_stats = calculate_avg_response_time(df)

st.subheader("📊 Statistik Pesan")
col1, col2 = st.columns(2)
with col1:
    col1.metric("Total Pesan", len(df))
    col1.metric("Pesan Diterima", len(df[df['status'] == "receive"]))
    col1.metric("Pesan Dikirim", len(df[df['status'] == "send"]))
    col1.metric("Jumlah User Unik", df['no'].nunique())

st.subheader("⏱️ Analisis Waktu Respon")
st.markdown("*Waktu respon dihitung dalam jam kerja (08:00-20:00)*")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Jumlah Sampel Response", response_stats['total_samples'])
    st.metric("Response Tercepat", response_stats['min'])
    st.metric("Response Terlama", response_stats['max'])

with col2:
    st.metric("Rata-rata Waktu Respon (Jam Kerja)", response_stats['avg'])
    st.metric("Rata-rata Waktu Respon (24 Jam)", response_stats['avg_raw'])

with col3:
    st.metric("Median Waktu Respon (Jam Kerja)", response_stats['median'])
    st.metric("Median Waktu Respon (24 Jam)", response_stats['median_raw'])

# =====================================
# 🔹 Distribusi Status Pesan
# =====================================
st.subheader("📈 Distribusi Status Pesan")
status_count = df['status'].value_counts().reset_index()
status_count.columns = ['Status', 'Jumlah']  # Rename columns for clarity
fig_status = px.pie(status_count, names='Status', values='Jumlah', color_discrete_sequence=px.colors.qualitative.Pastel)
st.plotly_chart(fig_status, use_container_width=True)

# =====================================
# 🔹 Aktivitas Pesan Seiring Waktu
# =====================================
st.subheader("⏰ Aktivitas Pesan Seiring Waktu")
df_time = df.groupby(df['datetime'].dt.floor('min')).size().reset_index(name='jumlah')
fig_time = px.line(df_time, x="datetime", y="jumlah", markers=True)
st.plotly_chart(fig_time, use_container_width=True)

# =====================================
# 🔹 Pesan Terpopuler
# =====================================
st.subheader("💬 Pesan Paling Sering Muncul")
top_msg = df['message'].value_counts().head(15).reset_index()
top_msg.columns = ["Pesan", "Frekuensi"]
fig_topmsg = px.bar(top_msg, x="Frekuensi", y="Pesan", orientation="h", text="Frekuensi",
                    color="Frekuensi", color_continuous_scale="Blues")
st.plotly_chart(fig_topmsg, use_container_width=True)

# =====================================
# 🔹 Word Frequency Analysis
# =====================================
st.subheader("☁️ Analisis Frekuensi Kata")

# Define stop words (kata penghubung) in Indonesian
stop_words = set(['yang', 'di', 'ke', 'dari', 'pada', 'dalam', 'untuk', 'dengan', 'dan', 'atau', 
                 'ini', 'itu', 'juga', 'sudah', 'saya', 'anda', 'dia', 'mereka', 'kita', 'akan',
                 'bisa', 'ada', 'tidak', 'saat', 'oleh', 'setelah', 'para', 'seperti', 'serta',
                 'bagi', 'tentang', 'sampai', 'hingga', 'sebuah', 'telah', 'sih', 'ya', 'hal',
                 'ok', 'oke', 'ketika', 'kepada', 'kami', 'kamu', 'aku', 'kau', 'kalian', 'saya'])

# Process text
all_text = " ".join(df['message'].astype(str))
words = [word.lower() for word in all_text.split() if word.lower() not in stop_words]
word_freq = pd.Series(words).value_counts().head(20)

# Create bar chart
fig_words = px.bar(
    x=word_freq.values,
    y=word_freq.index,
    orientation='h',
    title='20 Kata Paling Sering Muncul (Excluding Stop Words)',
    labels={'x': 'Frekuensi', 'y': 'Kata'},
    height=600
)

# Simple layout update
fig_words.update_layout(
    showlegend=False,
    margin=dict(l=20, r=20, t=40, b=20),
    plot_bgcolor='white'
)

# Display chart
st.plotly_chart(fig_words, use_container_width=True)

# =====================================
# 🔹 Analisis Intent
# =====================================
# if 'intent' in df.columns:
#     st.subheader("🎯 Distribusi Intent")
#     intent_count = df['intent'].value_counts().reset_index()
#     fig_intent = px.bar(intent_count, x="intent", y="count", color="count",
#                         color_continuous_scale="Tealgrn", text="count")
#     st.plotly_chart(fig_intent, use_container_width=True)

# =====================================
# 🔹 Timeline Percakapan
# =====================================
# st.subheader("📜 Timeline Percakapan")
# for _, row in df.sort_values("datetime").iterrows():
#     if row['status'] == "receive":
#         st.chat_message("user", avatar="🧑").write(f"**{row['name']}**: {row['message']}")
#     else:
#         st.chat_message("assistant", avatar="🤖").write(f"{row['message']}")
