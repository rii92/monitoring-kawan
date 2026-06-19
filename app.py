import streamlit as st

# Must be the first Streamlit command
st.set_page_config(page_title="Monitoring KAWAN", layout="wide")

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta

# =====================================
# 🔹 Page Navigation
# =====================================
PAGES = ["🤖 Analisis Chatbot KAWAN", "📋 Monitoring Progress SLS"]

if "page" not in st.session_state:
    st.session_state.page = PAGES[1]

# =====================================
# 🔹 PAGE 1: Chatbot Analysis
# =====================================
def page_chatbot():
    CHATBOT_API_URLS = [
        "https://script.google.com/macros/s/AKfycbwXynUCMX_pLTl1UU8UcbQzbrxvV9wsyloHEkrFH4vOCIrz4MaQ_B8HFrxgJ5L_Qmrz/exec",
        "https://script.google.com/macros/s/AKfycbxryhvmXetPamDTnX0PwgdQmo0t7dluEPIPHajXMRb4j0Res05WrPbM-lEMfBG3_39oMQ/exec"
    ]

    @st.cache_data
    def fetch_data_from_api(url):
        params = {"action": "read-history-message"}
        try:
            response = requests.get(url, params=params)
            data = response.json()
            df = pd.DataFrame(data['records'])

            df['datetime'] = pd.to_datetime(df['currentTime'], format='%d/%m/%Y, %H.%M.%S', errors='coerce')

            df.loc[df['datetime'].isna(), 'datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

            df['source'] = url.split('/')[-2][:10] + '...'

            return df
        except Exception as e:
            st.error(f"Error loading data from {url}: {str(e)}")
            return pd.DataFrame()

    @st.cache_data
    def load_data():
        dfs = [fetch_data_from_api(url) for url in CHATBOT_API_URLS]

        combined_df = pd.concat(dfs, ignore_index=True)

        combined_df = combined_df.drop_duplicates(subset=['id', 'message'])

        return combined_df

    df = load_data()

    st.title("🤖 Analisis History Chatbot KAWAN")
    st.markdown("Dashboard interaktif untuk menganalisis percakapan chatbot KAWAN berdasarkan data history pesan.")

    st.sidebar.header("⚙️ Filter Data")

    users = df['no'].unique()
    selected_user = st.sidebar.selectbox("Pilih User:", options=["Semua"] + list(users))

    if selected_user != "Semua":
        df = df[df['no'] == selected_user]

    date_range = st.sidebar.date_input(
        "Pilih Rentang Tanggal:",
        [df['datetime'].min().date(), df['datetime'].max().date()]
    )

    df = df[(df['datetime'].dt.date >= date_range[0]) & (df['datetime'].dt.date <= date_range[1])]

    st.subheader("📊 Statistik Ringkas")

    def calculate_working_hours(start, end):
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
        response_times_raw = []

        bot_no = CHATBOT_API_URLS[1]

        for i in range(len(df_sorted) - 1):
            current_row = df_sorted.iloc[i]
            next_row = df_sorted.iloc[i + 1]

            if (current_row['status'] == 'receive' and
                next_row['status'] == 'send' and
                next_row['no'] == bot_no):

                work_time = calculate_working_hours(
                    current_row['datetime'],
                    next_row['datetime']
                )

                raw_time = (next_row['datetime'] - current_row['datetime']).total_seconds()

                if 0 < work_time < 600:
                    response_times.append(work_time)
                    response_times_raw.append(raw_time)

        if response_times:
            avg_time = sum(response_times) / len(response_times)
            median_time = sorted(response_times)[len(response_times)//2]

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

    st.subheader("📈 Distribusi Status Pesan")
    status_count = df['status'].value_counts().reset_index()
    status_count.columns = ['Status', 'Jumlah']
    fig_status = px.pie(status_count, names='Status', values='Jumlah', color_discrete_sequence=px.colors.qualitative.Pastel)
    st.plotly_chart(fig_status, use_container_width=True)

    st.subheader("⏰ Aktivitas Pesan Seiring Waktu")
    df_time = df.groupby(df['datetime'].dt.floor('min')).size().reset_index(name='jumlah')
    fig_time = px.line(df_time, x="datetime", y="jumlah", markers=True)
    st.plotly_chart(fig_time, use_container_width=True)

    st.subheader("💬 Pesan Paling Sering Muncul")
    top_msg = df['message'].value_counts().head(15).reset_index()
    top_msg.columns = ["Pesan", "Frekuensi"]
    fig_topmsg = px.bar(top_msg, x="Frekuensi", y="Pesan", orientation="h", text="Frekuensi",
                        color="Frekuensi", color_continuous_scale="Blues")
    st.plotly_chart(fig_topmsg, use_container_width=True)

    st.subheader("☁️ Analisis Frekuensi Kata")

    stop_words = set(['yang', 'di', 'ke', 'dari', 'pada', 'dalam', 'untuk', 'dengan', 'dan', 'atau',
                     'ini', 'itu', 'juga', 'sudah', 'saya', 'anda', 'dia', 'mereka', 'kita', 'akan',
                     'bisa', 'ada', 'tidak', 'saat', 'oleh', 'setelah', 'para', 'seperti', 'serta',
                     'bagi', 'tentang', 'sampai', 'hingga', 'sebuah', 'telah', 'sih', 'ya', 'hal',
                     'ok', 'oke', 'ketika', 'kepada', 'kami', 'kamu', 'aku', 'kau', 'kalian', 'saya'])

    all_text = " ".join(df['message'].astype(str))
    words = [word.lower() for word in all_text.split() if word.lower() not in stop_words]
    word_freq = pd.Series(words).value_counts().head(20)

    fig_words = px.bar(
        x=word_freq.values,
        y=word_freq.index,
        orientation='h',
        title='20 Kata Paling Sering Muncul (Excluding Stop Words)',
        labels={'x': 'Frekuensi', 'y': 'Kata'},
        height=600
    )

    fig_words.update_layout(
        showlegend=False,
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor='white'
    )

    st.plotly_chart(fig_words, use_container_width=True)


# =====================================
# 🔹 PAGE 2: SLS Monitoring
# =====================================
def page_sls():
    SLS_API_URL = "https://script.google.com/macros/s/AKfycbxryhvmXetPamDTnX0PwgdQmo0t7dluEPIPHajXMRb4j0Res05WrPbM-lEMfBG3_39oMQ/exec"

    @st.cache_data(ttl=300)
    def fetch_sls_data():
        params = {"action": "readDBSLS"}
        try:
            response = requests.get(SLS_API_URL, params=params, timeout=60)
            data = response.json()
            return pd.DataFrame(data['records'])
        except Exception as e:
            st.error(f"Gagal memuat data SLS: {str(e)}")
            return pd.DataFrame()

    df = fetch_sls_data()

    if df.empty:
        st.warning("Tidak ada data SLS yang tersedia.")
        return

    st.title("📋 Monitoring Progress SLS")
    st.markdown("Dashboard monitoring progres pemutakhiran **Sensus Lingkungan Sensus (SLS)** — data real-time dari Google Apps Script.")

    # ─────────────────────────────────────────────
    # Data Preprocessing
    # ─────────────────────────────────────────────
    numeric_cols = [
        'jumlahSelesaiLapangan', 'jumlahSubmit', 'JumlahApproved', 'JumlahReject',
        'jumlahSelesaiLapanganSementara', 'jumlahSubmitSementara',
        'JumlahApprovedSementara', 'JumlahRejectSementara'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    str_cols = ['noHpPml', 'noHPMitra', 'kodeSLS', 'nmsls', 'nama_ketua',
                'nmprov', 'nmkab', 'nmkec', 'nmdesa', 'Nama_PML', 'Nama_PPL',
                'emailPPL', 'emailPML', 'statusSls']
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].fillna('-').astype(str)

    # ─────────────────────────────────────────────
    # Sidebar Filters
    # ─────────────────────────────────────────────
    st.sidebar.header("🔍 Filter SLS")

    def make_filter(col, label):
        options = sorted(df[col].unique())
        selected = st.sidebar.selectbox(label, ["Semua"] + options, key=f"filter_{col}")
        return selected if selected != "Semua" else None

    filtered = df.copy()

    sel_prov = make_filter('nmprov', 'Provinsi')
    if sel_prov:
        filtered = filtered[filtered['nmprov'] == sel_prov]

    sel_kab = make_filter('nmkab', 'Kabupaten')
    if sel_kab:
        filtered = filtered[filtered['nmkab'] == sel_kab]

    sel_kec = make_filter('nmkec', 'Kecamatan')
    if sel_kec:
        filtered = filtered[filtered['nmkec'] == sel_kec]

    sel_desa = make_filter('nmdesa', 'Desa')
    if sel_desa:
        filtered = filtered[filtered['nmdesa'] == sel_desa]

    sel_pml = make_filter('Nama_PML', 'PML')
    sel_ppl = make_filter('Nama_PPL', 'PPL')

    status_options = sorted(df['statusSls'].unique())
    sel_status = st.sidebar.selectbox("Status SLS", ["Semua"] + status_options, key="filter_status")
    if sel_status != "Semua":
        filtered = filtered[filtered['statusSls'] == sel_status]

    cari_text = st.sidebar.text_input("🔎 Cari Nama SLS / Ketua", "")

    # ─────────────────────────────────────────────
    # Apply search filter
    # ─────────────────────────────────────────────
    if cari_text:
        mask = (
            filtered['nmsls'].str.contains(cari_text, case=False, na=False) |
            filtered['nama_ketua'].str.contains(cari_text, case=False, na=False) |
            filtered['kodeSLS'].str.contains(cari_text, case=False, na=False)
        )
        filtered = filtered[mask]

    # ─────────────────────────────────────────────
    # Key Metrics
    # ─────────────────────────────────────────────
    total_sls = len(filtered)
    total_selesai = int(filtered['jumlahSelesaiLapangan'].sum())
    total_submit = int(filtered['jumlahSubmit'].sum())
    total_approved = int(filtered['JumlahApproved'].sum())
    total_reject = int(filtered['JumlahReject'].sum())
    total_ppl = filtered['Nama_PPL'].nunique()
    total_pml = filtered['Nama_PML'].nunique()

    st.subheader("📊 Ringkasan Progress")
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    col1.metric("Total SLS", total_sls)
    col2.metric("Selesai Lapangan", total_selesai)
    col3.metric("Submit", total_submit)
    col4.metric("Approved", total_approved)
    col5.metric("Reject", total_reject)
    col6.metric("Jumlah PPL", total_ppl)
    col7.metric("Jumlah PML", total_pml)

    if total_sls > 0:
        st.markdown(f"""
        <div style="display:flex; gap:8px; margin-top:8px; flex-wrap:wrap;">
            <span style="background:#E3F2FD; padding:4px 12px; border-radius:12px; font-size:0.85rem;">
                ✅ Selesai Lapangan: <b>{total_selesai/total_sls*100:.1f}%</b>
            </span>
            <span style="background:#FFF3E0; padding:4px 12px; border-radius:12px; font-size:0.85rem;">
                📤 Submit: <b>{total_submit/total_sls*100:.1f}%</b>
            </span>
            <span style="background:#E8F5E9; padding:4px 12px; border-radius:12px; font-size:0.85rem;">
                ✅ Approved: <b>{total_approved/total_sls*100:.1f}%</b>
            </span>
            <span style="background:#FFEBEE; padding:4px 12px; border-radius:12px; font-size:0.85rem;">
                ❌ Reject: <b>{total_reject/total_sls*100:.1f}%</b>
            </span>
        </div>
        """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────
    # Visualizations
    # ─────────────────────────────────────────────
    st.markdown("---")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("📈 Distribusi Status SLS")
        status_counts = filtered['statusSls'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Jumlah']
        if not status_counts.empty:
            color_map = {
                'belum': '#FFA726',
                'selesai': '#66BB6A',
                'proses': '#42A5F5',
                '-': '#BDBDBD'
            }
            fig_pie = px.pie(
                status_counts, names='Status', values='Jumlah',
                color='Status',
                color_discrete_map=color_map,
                hole=0.4
            )
            fig_pie.update_traces(textposition='outside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Tidak ada data status SLS.")

    with col_chart2:
        st.subheader("🏘️ Progress per Kecamatan")
        kec_progress = filtered.groupby('nmkec').agg(
            total_sls=('kodeSLS', 'count'),
            selesai=('jumlahSelesaiLapangan', 'sum'),
            submit=('jumlahSubmit', 'sum'),
            approved=('JumlahApproved', 'sum')
        ).reset_index().sort_values('total_sls', ascending=False).head(15)

        if not kec_progress.empty:
            fig_kec = go.Figure()
            fig_kec.add_trace(go.Bar(name='Selesai Lapangan', x=kec_progress['nmkec'], y=kec_progress['selesai'],
                                     marker_color='#2196F3'))
            fig_kec.add_trace(go.Bar(name='Submit', x=kec_progress['nmkec'], y=kec_progress['submit'],
                                     marker_color='#FFA726'))
            fig_kec.add_trace(go.Bar(name='Approved', x=kec_progress['nmkec'], y=kec_progress['approved'],
                                     marker_color='#66BB6A'))
            fig_kec.update_layout(barmode='group', xaxis_tickangle=-45, height=400,
                                  margin=dict(l=20, r=20, t=20, b=80))
            st.plotly_chart(fig_kec, use_container_width=True)
        else:
            st.info("Tidak ada data kecamatan.")

    st.markdown("---")

    col_chart3, col_chart4 = st.columns(2)

    with col_chart3:
        st.subheader("👷 Progress per PPL")
        ppl_progress = filtered.groupby('Nama_PPL').agg(
            total_sls=('kodeSLS', 'count'),
            selesai=('jumlahSelesaiLapangan', 'sum'),
            submit=('jumlahSubmit', 'sum'),
            approved=('JumlahApproved', 'sum')
        ).reset_index().sort_values('total_sls', ascending=False).head(15)

        if not ppl_progress.empty:
            fig_ppl = go.Figure()
            fig_ppl.add_trace(go.Bar(name='Selesai Lapangan', x=ppl_progress['Nama_PPL'], y=ppl_progress['selesai'],
                                     marker_color='#2196F3'))
            fig_ppl.add_trace(go.Bar(name='Submit', x=ppl_progress['Nama_PPL'], y=ppl_progress['submit'],
                                     marker_color='#FFA726'))
            fig_ppl.add_trace(go.Bar(name='Approved', x=ppl_progress['Nama_PPL'], y=ppl_progress['approved'],
                                     marker_color='#66BB6A'))
            fig_ppl.update_layout(barmode='group', xaxis_tickangle=-45, height=400,
                                  margin=dict(l=20, r=20, t=20, b=80))
            st.plotly_chart(fig_ppl, use_container_width=True)
        else:
            st.info("Tidak ada data PPL.")

    with col_chart4:
        st.subheader("🗺️ Sebaran SLS per Desa")
        desa_counts = filtered.groupby(['nmkec', 'nmdesa']).size().reset_index(name='jumlah')
        desa_counts = desa_counts.sort_values('jumlah', ascending=False).head(20)

        if not desa_counts.empty:
            fig_desa = px.bar(
                desa_counts, x='jumlah', y='nmdesa', orientation='h',
                color='nmkec', text='jumlah',
                labels={'jumlah': 'Jumlah SLS', 'nmdesa': 'Desa', 'nmkec': 'Kecamatan'},
                height=500, color_discrete_sequence=px.colors.qualitative.Bold
            )
            fig_desa.update_layout(yaxis={'categoryorder': 'total ascending'}, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_desa, use_container_width=True)
        else:
            st.info("Tidak ada data desa.")

    # ─────────────────────────────────────────────
    # Progress Table View (Grouped by Email PPL)
    # ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📊 Progress per PPL")

    progress_cols = [
        'jumlahSelesaiLapangan', 'jumlahSubmit', 'JumlahApproved', 'JumlahReject',
        'statusSls', 'Nama_PML', 'Nama_PPL', 'PJKuda', 'emailPPL', 'emailPML'
    ]

    progress_cols = [c for c in progress_cols if c in filtered.columns]

    col_label_map = {
        'emailPPL': 'Email PPL',
        'Nama_PPL': 'Nama PPL',
        'Nama_PML': 'Nama PML',
        'PJKuda': 'PJKuda',
        'emailPML': 'Email PML',
        'jumlahSelesaiLapangan': 'Selesai Lapangan',
        'jumlahSubmit': 'Submit',
        'JumlahApproved': 'Approved',
        'JumlahReject': 'Reject',
        'statusSls': 'Status SLS',
    }

    if 'emailPPL' in progress_cols:
        default_cols = ['emailPPL', 'Nama_PPL', 'Nama_PML', 'PJKuda',
                        'jumlahSelesaiLapangan', 'jumlahSubmit', 'JumlahApproved', 'JumlahReject', 'statusSls']
        default_cols = [c for c in default_cols if c in progress_cols]

        selected_cols = st.multiselect(
            "Pilih kolom yang ditampilkan:",
            options=progress_cols,
            default=default_cols,
            format_func=lambda c: col_label_map.get(c, c),
            key="progress_col_selector"
        )

        group_agg = {
            'Nama_PPL': 'first',
            'Nama_PML': 'first',
            'PJKuda': 'first',
            'emailPML': 'first',
            'jumlahSelesaiLapangan': 'sum',
            'jumlahSubmit': 'sum',
            'JumlahApproved': 'sum',
            'JumlahReject': 'sum',
            'statusSls': lambda x: ', '.join(f"{v} ({c})" for v, c in pd.Series(x).value_counts().items())
        }
        group_agg = {k: v for k, v in group_agg.items() if k in filtered.columns}

        progress_df = filtered.groupby('emailPPL').agg(group_agg).reset_index()

        cols_order = ['emailPPL', 'Nama_PPL', 'Nama_PML', 'PJKuda', 'emailPML',
                      'jumlahSelesaiLapangan', 'jumlahSubmit', 'JumlahApproved', 'JumlahReject', 'statusSls']
        cols_order = [c for c in cols_order if c in progress_df.columns]

        progress_df = progress_df[cols_order]

        progress_df.columns = [col_label_map.get(c, c) for c in progress_df.columns]

        if selected_cols:
            selected_labels = [col_label_map.get(c, c) for c in selected_cols]
            display_progress_df = progress_df[selected_labels]
        else:
            display_progress_df = progress_df

        st.dataframe(display_progress_df, use_container_width=True, hide_index=True, height=500)

        st.caption(f"Menampilkan {len(progress_df)} PPL dari {len(df)} total data SLS.")

        csv_progress = display_progress_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV Progress",
            data=csv_progress,
            file_name=f"progress_per_ppl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )
    else:
        st.info("Kolom emailPPL tidak tersedia.")

    # ─────────────────────────────────────────────
    # Detailed Data Table
    # ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 Data Detail SLS")

    display_cols = [
        'kodeSLS', 'nmsls', 'nama_ketua',
        'nmprov', 'nmkab', 'nmkec', 'nmdesa',
        'Nama_PML', 'Nama_PPL',
        'jumlahSelesaiLapangan', 'jumlahSubmit', 'JumlahApproved', 'JumlahReject',
        'statusSls', 'noHpPml', 'noHPMitra', 'emailPPL', 'emailPML'
    ]

    display_cols = [c for c in display_cols if c in filtered.columns]

    display_df = filtered[display_cols].copy()

    display_df.columns = [
        'Kode SLS', 'Nama SLS', 'Nama Ketua',
        'Provinsi', 'Kabupaten', 'Kecamatan', 'Desa',
        'PML', 'PPL',
        'Selesai Lapangan', 'Submit', 'Approved', 'Reject',
        'Status', 'No. HP PML', 'No. HP Mitra', 'Email PPL', 'Email PML'
    ]

    st.dataframe(display_df, use_container_width=True, hide_index=True, height=500)

    st.caption(f"Menampilkan {len(display_df)} dari {len(df)} total data SLS.")

    # Download button
    csv = display_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=f"data_sls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )


# =====================================
# 🔹 Main App
# =====================================
def main():
    with st.sidebar:
        st.title("🏠 Menu Utama")
        st.divider()
        VISIBLE_PAGES = [PAGES[1]]  # Hanya tampilkan Monitoring Progress SLS
        for page in VISIBLE_PAGES:
            btn_type = "primary" if st.session_state.page == page else "secondary"
            if st.button(page, use_container_width=True, type=btn_type):
                st.session_state.page = page
        st.divider()
        st.caption(f"Monitoring KAWAN v1.0\nTerakhir diakses: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    if st.session_state.page == PAGES[0]:
        page_chatbot()
    else:
        page_sls()


if __name__ == "__main__":
    main()
