import streamlit as st

# Must be the first Streamlit command
st.set_page_config(page_title="Analisis Chatbot KAWAN", layout="wide")

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud
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
sources = df['source'].unique()
selected_source = st.sidebar.selectbox("Pilih Sumber Data:", options=["Semua"] + list(sources))

if selected_source != "Semua":
    df = df[df['source'] == selected_source]

# Filter by user
users = df['name'].unique()
selected_user = st.sidebar.selectbox("Pilih User:", options=["Semua"] + list(users))

if selected_user != "Semua":
    df = df[df['name'] == selected_user]

date_range = st.sidebar.date_input(
    "Pilih Rentang Tanggal:",
    [df['datetime'].min().date(), df['datetime'].max().date()]
)

df = df[(df['datetime'].dt.date >= date_range[0]) & (df['datetime'].dt.date <= date_range[1])]

# =====================================
# 🔹 Statistik Ringkas
# =====================================
st.subheader("📊 Statistik Ringkas")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Pesan", len(df))
col2.metric("Pesan Diterima", len(df[df['status'] == "receive"]))
col3.metric("Pesan Dikirim", len(df[df['status'] == "send"]))
col4.metric("Jumlah User Unik", df['name'].nunique())

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
# 🔹 Wordcloud Pesan
# =====================================
st.subheader("☁️ Wordcloud Pesan")
all_text = " ".join(df['message'].astype(str))
wc = WordCloud(width=800, height=400, background_color="white", colormap="viridis").generate(all_text)
fig_wc, ax = plt.subplots(figsize=(10,5))
ax.imshow(wc, interpolation="bilinear")
ax.axis("off")
st.pyplot(fig_wc)

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
