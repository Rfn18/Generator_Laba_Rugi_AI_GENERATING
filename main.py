from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv
import google.generativeai as genai
import os
import logging

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)

# hanya tampilkan WARNING ke atas
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('absl').setLevel(logging.ERROR)

# Muat variabel lingkungan
load_dotenv()
# Pastikan GEMINI_API_KEY ada di file .env Anda
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    logging.error("GEMINI_API_KEY tidak ditemukan. Pastikan file .env sudah diatur.")

# Konfigurasi Gemini (dilakukan sekali di awal)
try:
    genai.configure(api_key=API_KEY)
except Exception as e:
    logging.error(f"Gagal mengonfigurasi Gemini API: {e}")

app = Flask(__name__)

# Menggunakan model yang lebih spesifik untuk pembuatan konten teks
MODEL_NAME = "gemini-2.5-flash-preview-05-20" 

@app.route("/")
def index():
    """Rute untuk menampilkan halaman input (index.html)."""
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    """Rute untuk menerima data transaksi dan memanggil Gemini API."""
    try:
        data = request.get_json()
    except Exception:
        return jsonify({"error": "Permintaan JSON tidak valid."}), 400

    # Ekstraksi data input
    perusahaan = data.get("perusahaan", "Nama Perusahaan Default")
    periode = data.get("periode", "Periode Tidak Diketahui")
    kategori = data.get("kategori", [])
    keterangan = data.get("keterangan", [])
    jumlah = data.get("jumlah", [])

    # Membangun string transaksi untuk prompt
    transaksi_list = []
    for i in range(len(kategori)):
        try:
            amount = float(jumlah[i]) if jumlah[i] else 0
            if keterangan[i] and amount != 0:
                transaksi_list.append(f"{kategori[i]} - {keterangan[i]} : {int(amount)}")
        except ValueError:
            logging.warning(f"Nilai jumlah tidak valid, dilewati: {jumlah[i]}")
            continue
    
    if not transaksi_list:
        return jsonify({"error": "Tidak ada transaksi valid yang ditemukan untuk diproses."}), 400

    transaksi_str = "\n".join(transaksi_list)

    # System Prompt: Instruksi untuk Model AI
    system_prompt = (
        "Anda adalah asisten AI yang ahli dalam akuntansi dan pemformatan HTML. "
        "Tugas Anda adalah membuat fragmen HTML yang elegan dan responsif untuk Laporan Laba Rugi. "
        "GUNAKAN KELAS TAILWIND CSS LENGKAP untuk semua styling, termasuk tata letak, warna, tipografi, dan responsivitas. "
        "JANGAN SERTAKAN tag <html>, <head>, atau <body>, hanya fragmen konten laporan."
        "\n\n--- MULAI LAPORAN ---\n\n"
    )

    # User Prompt: Data dan Aturan Laporan
    user_prompt = f"""
    Buatlah fragmen HTML Laporan Laba Rugi berdasarkan data transaksi berikut:

    Persuahaan: {perusahaan}
    Periode: {periode}

    Data Transaksi (Kategori - Keterangan : Jumlah):
    {transaksi_str}

    Aturan Pembuatan Laporan:
    1.  **HEADER**: Tampilkan Nama Perusahaan, Judul Laporan ("LAPORAN LABA RUGI"), Periode, dan Catatan "Dalam Rupiah (Rp)". Gunakan tipografi yang menonjol dan rata tengah.
    2.  **TABEL**: Gunakan elemen <table>, <thead>, dan <tbody>. Pastikan tabel **responsif penuh** (`w-full`) dengan padding dan batas yang bagus (menggunakan kelas Tailwind seperti `border-collapse`, `shadow-lg`, `rounded-lg`).
    3.  **KOLOM**: "Keterangan" (Rata Kiri, Lebar 70%) dan "Jumlah (Rp)" (Rata Kanan, Lebar 30%).
    4.  **PENGELOMPOKAN**: Kategorikan transaksi menjadi **Pendapatan** (dengan subtotal **Total Pendapatan**) dan **Beban** (dengan subtotal **Total Beban**).
    5.  **LABA BERSIH**: Hitung **LABA BERSIH (RUGI BERSIH)** sebagai Total Pendapatan dikurangi Total Beban. Nilai akhir ini harus **DIBOLD dan menonjol** dengan gaya khas Tailwind (misalnya, font tebal ekstra dan latar belakang hijau muda/merah muda).
    6.  **FORMAT ANGKA**: Semua nilai mata uang (Jumlah) harus diformat sebagai angka tanpa pemisah desimal, contoh: 1,000,000.
    """
    
    # PERBAIKAN STABILITAS: Menggabungkan system_prompt dan user_prompt
    # Ini mengatasi masalah SDK yang tidak mengenali keyword 'config' atau 'system_instruction'
    full_prompt = system_prompt + user_prompt

    logging.info(f"Mencoba menghasilkan laporan untuk {perusahaan} menggunakan model {MODEL_NAME}...")
    
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        
        # Panggilan API hanya dengan argumen 'contents'
        response = model.generate_content(
            contents=full_prompt
        )
        
        # Mengembalikan HTML fragmen yang dihasilkan
        return jsonify({"html_report": response.text}), 200

    except Exception as e:
        # Penanganan error umum pada saat panggilan API
        logging.error(f"Kesalahan dalam memanggil Gemini API: {e}")
        return jsonify({"error": f"Gagal menghasilkan laporan. Detail: {str(e)}"}), 500

if __name__ == "__main__":
    # Menggunakan port dari .env atau default ke 8080
    port = int(os.getenv("PORT", 8080))
    app.run(debug=True, port=port)
