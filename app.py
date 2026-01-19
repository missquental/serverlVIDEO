import streamlit as st
from gtts import gTTS
import os
from moviepy.editor import AudioFileClip
import uuid

# Judul aplikasi
st.title("🔤 Teks ke Video (Text-to-Speech)")

# Input teks dari user
text_input = st.text_area("Masukkan teks:", height=150)

# Tombol untuk generate video
if st.button("Buat Video"):
    if not text_input.strip():
        st.warning("Silakan masukkan teks terlebih dahulu.")
    else:
        with st.spinner("Membuat video..."):
            # Generate nama unik untuk file sementara
            unique_id = str(uuid.uuid4())
            audio_path = f"temp_audio_{unique_id}.mp3"
            video_path = f"output_video_{unique_id}.mp4"

            try:
                # Buat audio dari teks
                tts = gTTS(text=text_input, lang='id')  # Bahasa Indonesia ('id'), bisa diganti jadi 'en' dll
                tts.save(audio_path)

                # Buat video kosong hanya dengan audio
                audio_clip = AudioFileClip(audio_path)
                video_clip = audio_clip.to_videoclip()
                video_clip.write_videofile(video_path, codec='libx264', fps=24)

                # Hapus audio sementara setelah selesai
                os.remove(audio_path)
                audio_clip.close()
                video_clip.close()

                # Tampilkan video hasil
                st.video(video_path)

                # Opsi download
                with open(video_path, "rb") as file:
                    btn = st.download_button(
                        label="Unduh Video",
                        data=file,
                        file_name="video_hasil.mp4",
                        mime="video/mp4"
                    )

                # Hapus video setelah ditampilkan/download
                os.remove(video_path)

            except Exception as e:
                st.error(f"Terjadi kesalahan: {str(e)}")
