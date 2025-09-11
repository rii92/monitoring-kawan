import streamlit as st

# Must be the first Streamlit command
st.set_page_config(page_title="Analisis Chatbot KAWAN", layout="wide")

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import requests
from datetime import datetime

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

# Calculate average response time
def calculate_avg_response_time(df):
    # Sort by datetime to ensure correct order
    df_sorted = df.sort_values('datetime').copy()
    
    response_times = []
    MAX_RESPONSE_TIME = 180  # Maximum 3 minutes response time threshold
    
    # Group messages by conversation
    current_conversation = None
    last_receive_time = None
    bot_no = "https://script.google.com/macros/s/AKfycbxryhvmXetPamDTnX0PwgdQmo0t7dluEPIPHajXMRb4j0Res05WrPbM-lEMfBG3_39oMQ/exec"
    
    for idx, row in df_sorted.iterrows():
        current_time = row['datetime']
        
        # If it's a user message (receive)
        if row['status'] == 'receive':
            # Start new conversation
            last_receive_time = current_time
            current_conversation = row['no']
            
        # If it's a bot response (send) and we have a pending user message
        elif (row['status'] == 'send' and 
              last_receive_time is not None and 
              current_conversation is not None and 
              row['no'] == bot_no):
            
            # Calculate response time
            response_time = (current_time - last_receive_time).total_seconds()
            
            # Only count if response time is reasonable
            if 0 < response_time < MAX_RESPONSE_TIME:
                response_times.append(response_time)
            
            # Reset conversation tracking
            last_receive_time = None
            current_conversation = None
            
        # If too much time has passed, reset conversation
        elif last_receive_time is not None:
            time_passed = (current_time - last_receive_time).total_seconds()
            if time_passed > MAX_RESPONSE_TIME:
                last_receive_time = None
                current_conversation = None
    
    if response_times:
        avg_response_time = sum(response_times) / len(response_times)
        # Convert to minutes and seconds
        minutes = int(avg_response_time // 60)
        seconds = int(avg_response_time % 60)
        
        # Calculate median for more accurate typical response time
        median_time = sorted(response_times)[len(response_times)//2]
        median_minutes = int(median_time // 60)
        median_seconds = int(median_time % 60)
        
        stats = {
            'avg': f"{minutes} menit {seconds} detik",
            'median': f"{median_minutes} menit {median_seconds} detik",
            'min': f"{int(min(response_times))} detik",
            'max': f"{int(max(response_times))} detik",
            'total_samples': len(response_times)
        }
        return stats
    
    return {
        'avg': "N/A",
        'median': "N/A",
        'min': "N/A",
        'max': "N/A",
        'total_samples': 0
    }

response_stats = calculate_avg_response_time(df)

col1, col2, col3, col4 = st.columns(4)

# Basic metrics
col1.metric("Total Pesan", len(df))
col1.metric("Pesan Diterima", len(df[df['status'] == "receive"]))
col1.metric("Pesan Dikirim", len(df[df['status'] == "send"]))

# User metrics
col2.metric("Jumlah User Unik", df['no'].nunique())
col2.metric("Jumlah Sampel Response", response_stats['total_samples'])

# Response time averages
col3.metric("Rata-rata Waktu Respon", response_stats['avg'])
col3.metric("Median Waktu Respon", response_stats['median'])

# Response time extremes
col4.metric("Response Tercepat", response_stats['min'])
col4.metric("Response Terlama", response_stats['max'])

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
