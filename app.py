import streamlit as st
import os
from datetime import datetime
import requests
import json

# Konfigurasi
API_BASE_URL = "http://localhost:8000"  # Sesuaikan dengan URL API Anda
UPLOAD_DIR = "uploaded_videos"

# Judul aplikasi
st.title("🎥 Video Storage & Streaming Manager")
st.markdown("---")

# Tabs untuk navigasi
tab1, tab2, tab3 = st.tabs(["📤 Upload Video", "📁 Video Library", "📱 API Info"])

# Tab Upload Video
with tab1:
    st.header("Bulk Upload Video")
    
    # Upload multiple files
    uploaded_files = st.file_uploader(
        "Pilih satu atau lebih file video",
        type=['mp4', '.avi', '.mov', '.mkv', '.webm'],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        st.subheader("File yang akan diupload:")
        for uploaded_file in uploaded_files:
            st.write(f"📄 {uploaded_file.name} ({uploaded_file.size:,} bytes)")
        
        # Tombol upload
        if st.button("📤 Upload Semua Video", type="primary"):
            success_count = 0
            error_count = 0
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Mengupload {uploaded_file.name}...")
                
                try:
                    # Upload via API
                    files = {'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    response = requests.post(f"{API_BASE_URL}/upload", files=files)
                    
                    if response.status_code == 200:
                        success_count += 1
                        st.success(f"✅ Berhasil upload: {uploaded_file.name}")
                    else:
                        error_count += 1
                        st.error(f"❌ Gagal upload {uploaded_file.name}: {response.text}")
                        
                except Exception as e:
                    error_count += 1
                    st.error(f"❌ Error upload {uploaded_file.name}: {str(e)}")
                
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            progress_bar.empty()
            status_text.empty()
            
            st.markdown("---")
            st.success(f"""
                **Upload Selesai!**  
                ✅ Berhasil: {success_count} file  
                ❌ Gagal: {error_count} file
            """)

# Tab Video Library
with tab2:
    st.header("Video Library")
    
    try:
        # Dapatkan daftar video dari API
        response = requests.get(f"{API_BASE_URL}/videos")
        if response.status_code == 200:
            videos_data = response.json()
            videos = videos_data.get('videos', [])
            
            if not videos:
                st.info("📭 Belum ada video yang diupload.")
            else:
                st.subheader(f"Daftar Video ({len(videos)} file)")
                
                # Filter pencarian
                search_term = st.text_input("🔍 Cari video berdasarkan nama:")
                if search_term:
                    videos = [v for v in videos if search_term.lower() in v['filename'].lower()]
                    st.info(f"Ditemukan {len(videos)} hasil pencarian")
                
                # Tampilkan video
                for video in videos:
                    with st.expander(f"🎬 {video['filename']}", expanded=False):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            # Player video streaming
                            video_url = f"{API_BASE_URL}/stream/{video['id']}"
                            st.video(video_url)
                            
                        with col2:
                            st.write("**Detail File:**")
                            st.write(f"📁 Nama: `{video['filename']}`")
                            st.write(f"💾 Ukuran: {video['size']:,} bytes")
                            st.write(f"📅 Diupload: {video['upload_date']}")
                            
                            # Link streaming langsung
                            st.markdown(f"[🔗 Link Streaming]({video_url})")
                            
                            # Tombol hapus
                            if st.button(f"🗑️ Hapus", key=f"delete_{video['id']}"):
                                try:
                                    delete_response = requests.delete(f"{API_BASE_URL}/delete/{video['id']}")
                                    if delete_response.status_code == 200:
                                        st.success(f"✅ Video berhasil dihapus!")
                                        st.experimental_rerun()
                                    else:
                                        st.error("❌ Gagal menghapus video")
                                except Exception as e:
                                    st.error(f"❌ Error: {str(e)}")
        else:
            st.error("❌ Gagal mengambil daftar video")
            
    except Exception as e:
        st.error(f"❌ Error connecting to API: {str(e)}")
        st.info("Pastikan server API sudah berjalan di port 8000")

# Tab API Info
with tab3:
    st.header("📱 API Documentation")
    
    st.subheader("📚 Endpoint yang Tersedia:")
    
    with st.expander("📤 Upload Video", expanded=True):
        st.markdown("""
        **POST** `/upload`
        - Upload file video
        - Content-Type: multipart/form-data
        - Response: JSON dengan status dan info file
        """)
        st.code("""
        curl -X POST \\
          -F "file=@video.mp4" \\
          http://localhost:8000/upload
        """, language="bash")
    
    with st.expander("📋 Daftar Video", expanded=True):
        st.markdown("""
        **GET** `/videos`
        - Mendapatkan daftar semua video
        - Response: JSON array video info
        """)
        st.code("""
        curl http://localhost:8000/videos
        """, language="bash")
    
    with st.expander("▶️ Streaming Video", expanded=True):
        st.markdown("""
        **GET** `/stream/{video_id}`
        - Streaming video berdasarkan ID
        - Support range requests untuk seek
        - Response: Video stream dengan headers yang sesuai
        """)
        st.code("""
        curl http://localhost:8000/stream/12345
        """, language="bash")
    
    with st.expander("🗑️ Hapus Video", expanded=True):
        st.markdown("""
        **DELETE** `/delete/{video_id}`
        - Menghapus video berdasarkan ID
        - Response: Status penghapusan
        """)
        st.code("""
        curl -X DELETE http://localhost:8000/delete/12345
        """, language="bash")
    
    st.subheader("🔧 Contoh Implementasi Frontend:")
    st.code("""
    // Streaming video di HTML5 player
    <video controls>
        <source src="http://localhost:8000/stream/12345" type="video/mp4">
        Browser tidak support video.
    </video>
    """, language="html")
    
    st.info("💡 Video bisa di-stream langsung tanpa perlu download terlebih dahulu!")

# Sidebar
with st.sidebar:
    st.header("📊 Status Server")
    
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            st.success("🟢 API Server Online")
            data = response.json()
            st.metric("Total Videos", data.get('total_videos', 0))
            st.metric("Storage Used", data.get('storage_used', '0 MB'))
        else:
            st.error("🔴 API Server Offline")
    except:
        st.error("🔴 API Server Offline")
        st.info("Jalankan API server dengan: `uvicorn api:app --reload`")
    
    st.divider()
    st.info("💡 Video di-stream langsung dari server tanpa perlu download!")

st.markdown("---")
st.caption("🛠️ Video Storage & Streaming Manager | Dibuat dengan Streamlit + FastAPI")
