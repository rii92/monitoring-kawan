# Analisis Chatbot KAWAN

Aplikasi dashboard interaktif untuk menganalisis percakapan chatbot KAWAN menggunakan Streamlit.

## Fitur

- Visualisasi distribusi status pesan
- Analisis aktivitas pesan seiring waktu
- Pesan terpopuler
- Wordcloud dari pesan
- Filter berdasarkan user dan rentang tanggal
- Analisis intent (jika tersedia)

## Cara Menjalankan

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Jalankan aplikasi:
```bash
streamlit run app.py
```

## Format Data

Aplikasi ini mengharapkan file CSV (`chat_history.csv`) dengan kolom-kolom berikut:
- name: Nama pengguna
- message: Isi pesan
- currentTime: Waktu pesan
- status: Status pesan (receive/send)
- intent (opsional): Intent dari pesan

## Requirements

- Python 3.7+
- Streamlit
- Pandas
- Plotly
- WordCloud
- Matplotlib
