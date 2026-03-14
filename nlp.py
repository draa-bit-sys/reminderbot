from google import genai
import os
import json

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

SYSTEM_PROMPT = """
Kamu adalah asisten bot Telegram pribadi. Tugasmu adalah menganalisis pesan pengguna dan mengubahnya menjadi perintah JSON.

Perintah yang tersedia:
- tambah_reminder: {"action": "tambah_reminder", "time": "HH:MM", "days": "daily/mon/tue/wed/thu/fri/sat/sun", "text": "pesan"}
- hapus_reminder: {"action": "hapus_reminder", "index": nomor_urut}
- tambah_catatan: {"action": "tambah_catatan", "text": "isi catatan"}
- tambah_todo: {"action": "tambah_todo", "task": "nama tugas"}
- lihat_reminder: {"action": "lihat_reminder"}
- lihat_catatan: {"action": "lihat_catatan"}
- lihat_todo: {"action": "lihat_todo"}
- tidak_dikenal: {"action": "tidak_dikenal", "reply": "jawaban natural kamu"}

Aturan:
- Balas HANYA dengan JSON, tanpa teks lain, tanpa markdown
- Jika pesan tidak jelas, gunakan action "tidak_dikenal" dan isi reply dengan jawaban natural
- Untuk hari: daily=setiap hari, mon=senin, tue=selasa, wed=rabu, thu=kamis, fri=jumat, sat=sabtu, sun=minggu
- Format waktu selalu HH:MM
"""

def parse_pesan(pesan: str) -> dict:
    try:
       response = client.models.generate_content(
    model="gemini-2.0-flash-lite",
    contents=SYSTEM_PROMPT + f"\n\nUser: {pesan}"
)
        text = response.text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        return {"action": "tidak_dikenal", "reply": "Maaf, gw gak ngerti maksudnya. Coba pakai /help!"}