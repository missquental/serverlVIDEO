import streamlit as st
import os
import shutil
from datetime import datetime

# Konfigurasi direktori penyimpanan
UPLOAD_DIR = "uploaded_videos"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Fungsi untuk menyimpan file yang diupload
def save_uploaded_file(uploaded_file):
    try:
        # Buat nama file unik dengan timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = uploaded_file.name.split('.')[-1]
        new_filename = f"{timestamp}_{uploaded_file.name}"
        
        file_path = os.path.join(UPLOAD_DIR, new_filename)
        
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return True, file_path
    except Exception as e:
        return False, str(e)

# Fungsi untuk mendapatkan daftar video yang tersimpan
def get_stored_videos():
    if not os.path.exists(UPLOAD_DIR):
        return []
    
    video_files = []
    for filename in os.listdir(UPLOAD_DIR):
        if filename.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
            file_path = os.path.join(UPLOAD_DIR, filename)
            file_time = os.path.getmtime(file_path)
            video_files.append({
                'name': filename,
                'path': file_path,
                'size': os.path.getsize(file_path),
                'date': datetime.fromtimestamp(file_time)
            })
    
    # Urutkan berdasarkan tanggal terbaru
    video_files.sort(key=lambda x: x['date'], reverse=True)
    return video_files

# Fungsi untuk menghapus video
def delete_video(filename):
    try:
        file_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        st.error(f"Error saat menghapus file: {str(e)}")
        return False

# Judul aplikasi
st.title("🎥 Video Storage & Upload Manager")
st.markdown("---")

# Tabs untuk navigasi
tab1, tab2 = st.tabs(["📤 Upload Video", "📁 Video Library"])

# Tab Upload Video
with tab1:
    st.header("Bulk Upload Video")
    
    # Upload multiple files
    uploaded_files = st.file_uploader(
        "Pilih satu atau lebih file video",
        type=['mp4', 'avi', 'mov', 'mkv', 'webm'],
        accept_multiple_files=True,
        key="video_uploader"
    )
    
    if uploaded_files:
        st.subheader("File yang akan diupload:")
        for uploaded_file in uploaded_files:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"📄 {uploaded_file.name} ({uploaded_file.size:,} bytes)")
            with col2:
                st.info(f"Tipe: {uploaded_file.type}")
        
        # Tombol upload
        if st.button("📤 Upload Semua Video", type="primary"):
            success_count = 0
            error_count = 0
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Mengupload {uploaded_file.name}...")
                success, result = save_uploaded_file(uploaded_file)
                
                if success:
                    success_count += 1
                    st.success(f"✅ Berhasil upload: {uploaded_file.name}")
                else:
                    error_count += 1
                    st.error(f"❌ Gagal upload {uploaded_file.name}: {result}")
                
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            progress_bar.empty()
            status_text.empty()
            
            st.markdown("---")
            st.success(f"""
                **Upload Selesai!**  
                ✅ Berhasil: {success_count} file  
                ❌ Gagal: {error_count} file
            """)
            
            if success_count > 0:
                st.info("🔄 Halaman akan refresh dalam 3 detik...")
                st.experimental_rerun()

# Tab Video Library
with tab2:
    st.header("Video Library")
    
    # Dapatkan daftar video
    videos = get_stored_videos()
    
    if not videos:
        st.info("📭 Belum ada video yang diupload. Silakan upload video di tab 'Upload Video'")
    else:
        st.subheader(f"Daftar Video ({len(videos)} file)")
        
        # Tampilkan video dengan pagination
        items_per_page = 10
        page = st.number_input('Halaman', min_value=1, max_value=(len(videos)//items_per_page)+1, value=1)
        start_idx = (page-1) * items_per_page
        end_idx = start_idx + items_per_page
        
        current_videos = videos[start_idx:end_idx]
        
        for video in current_videos:
            with st.expander(f"🎬 {video['name']}", expanded=False):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Player video
                    st.video(video['path'])
                    
                with col2:
                    st.write("**Detail File:**")
                    st.write(f"📁 Nama: `{video['name']}`")
                    st.write(f"💾 Ukuran: {video['size']:,} bytes")
                    st.write(f"📅 Diupload: {video['date'].strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # Tombol download
                    with open(video['path'], "rb") as file:
                        btn = st.download_button(
                            label="📥 Download Video",
                            data=file,
                            file_name=video['name'],
                            mime="video/mp4"
                        )
                    
                    # Tombol hapus
                    if st.button(f"🗑️ Hapus {video['name']}", key=f"delete_{video['name']}"):
                        if delete_video(video['name']):
                            st.success(f"✅ {video['name']} berhasil dihapus!")
                            st.experimental_rerun()
                        else:
                            st.error("❌ Gagal menghapus file")
        
        # Pagination info
        st.caption(f"Menampilkan {start_idx+1}-{min(end_idx, len(videos))} dari {len(videos)} video")

# Sidebar informasi
with st.sidebar:
    st.header("📊 Informasi Penyimpanan")
    
    # Hitung total ukuran dan jumlah file
    total_size = 0
    total_files = 0
    
    if os.path.exists(UPLOAD_DIR):
        for filename in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(file_path):
                total_size += os.path.getsize(file_path)
                total_files += 1
    
    st.metric("Total Video", f"{total_files} file")
    st.metric("Total Ukuran", f"{total_size / (1024*1024):.2f} MB")
    
    st.divider()
    
    st.subheader("📁 Format yang Didukung:")
    st.markdown("""
    - MP4 (.mp4)
    - AVI (.avi)
    - MOV (.mov)
    - MKV (.mkv)
    - WEBM (.webm)
    """)
    
    st.divider()
    
    st.info("💡 Tips:\n- Gunakan nama file yang deskriptif\n- Periksa ukuran file sebelum upload\n- Video akan disimpan secara permanen")

# Footer
st.markdown("---")
st.caption("🛠️ Video Storage Manager | Dibuat dengan Streamlit")
