import sys
import subprocess
import threading
import time
import os
import json
import streamlit.components.v1 as components
from datetime import datetime, timedelta
import urllib.parse
import requests
import sqlite3
from pathlib import Path

# ... (semua import dan fungsi yang sudah ada tetap sama) ...

def main():
    # ... (setup awal yang sudah ada) ...
    
    # Tabs for main interface
    tab1, tab2, tab3 = st.tabs(["📺 Streaming", "📁 Video Library", "⚙️ Configuration"])
    
    # ... (tab1 dan tab3 tetap sama) ...
    
    with tab2:
        st.header("📁 Video Library")
        
        # Upload new videos section (multiple files)
        st.subheader("📤 Upload Multiple Videos")
        uploaded_files = st.file_uploader(
            "Choose video files", 
            type=['mp4', '.flv', '.avi', '.mov', '.mkv'], 
            key="video_library_uploader",
            accept_multiple_files=True  # Izinkan multiple upload
        )
        
        if uploaded_files is not None and len(uploaded_files) > 0:
            uploaded_count = 0
            error_count = 0
            
            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Simpan file ke direktori khusus
                VIDEO_UPLOAD_DIR = "uploaded_videos_library"
                os.makedirs(VIDEO_UPLOAD_DIR, exist_ok=True)
                
                for i, uploaded_file in enumerate(uploaded_files):
                    status_text.text(f"Uploading {uploaded_file.name}... ({i+1}/{len(uploaded_files)})")
                    progress_bar.progress((i + 1) / len(uploaded_files))
                    
                    try:
                        # Simpan file
                        file_path = os.path.join(VIDEO_UPLOAD_DIR, uploaded_file.name)
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        # Simpan ke database
                        file_size = os.path.getsize(file_path)
                        duration = get_video_duration(file_path)
                        save_uploaded_video(uploaded_file.name, file_path, file_size, duration)
                        uploaded_count += 1
                        
                    except Exception as e:
                        st.error(f"❌ Error uploading {uploaded_file.name}: {str(e)}")
                        error_count += 1
                
                progress_bar.empty()
                status_text.empty()
                
                if uploaded_count > 0:
                    st.success(f"✅ Successfully uploaded {uploaded_count} videos! {f'(Errors: {error_count})' if error_count > 0 else ''}")
                    st.rerun()
                else:
                    st.error("❌ No videos were uploaded successfully")
                    
            except Exception as e:
                st.error(f"❌ Error during upload process: {str(e)}")
        
        # Bulk upload from local directory
        st.subheader("📥 Bulk Import from Local Directory")
        col_import1, col_import2 = st.columns(2)
        
        with col_import1:
            local_directory = st.text_input("Local Directory Path", value="./videos", key="local_dir_path")
            
        with col_import2:
            st.write("")  # Spacer
            st.write("")  # Spacer
            if st.button("Import Videos from Directory"):
                if os.path.exists(local_directory):
                    imported_count = 0
                    error_count = 0
                    
                    # Supported video extensions
                    video_extensions = ('.mp4', '.flv', '.avi', '.mov', '.mkv')
                    
                    # Get all video files from directory
                    video_files = [f for f in os.listdir(local_directory) 
                                 if f.lower().endswith(video_extensions)]
                    
                    if video_files:
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        try:
                            VIDEO_UPLOAD_DIR = "uploaded_videos_library"
                            os.makedirs(VIDEO_UPLOAD_DIR, exist_ok=True)
                            
                            for i, filename in enumerate(video_files):
                                status_text.text(f"Importing {filename}... ({i+1}/{len(video_files)})")
                                progress_bar.progress((i + 1) / len(video_files))
                                
                                try:
                                    source_path = os.path.join(local_directory, filename)
                                    dest_path = os.path.join(VIDEO_UPLOAD_DIR, filename)
                                    
                                    # Copy file
                                    with open(source_path, "rb") as src, open(dest_path, "wb") as dst:
                                        dst.write(src.read())
                                    
                                    # Simpan ke database
                                    file_size = os.path.getsize(dest_path)
                                    duration = get_video_duration(dest_path)
                                    save_uploaded_video(filename, dest_path, file_size, duration)
                                    imported_count += 1
                                    
                                except Exception as e:
                                    st.error(f"❌ Error importing {filename}: {str(e)}")
                                    error_count += 1
                            
                            progress_bar.empty()
                            status_text.empty()
                            
                            if imported_count > 0:
                                st.success(f"✅ Successfully imported {imported_count} videos! {f'(Errors: {error_count})' if error_count > 0 else ''}")
                                st.rerun()
                            else:
                                st.error("❌ No videos were imported successfully")
                                
                        except Exception as e:
                            st.error(f"❌ Error during import process: {str(e)}")
                    else:
                        st.info("No video files found in the specified directory")
                else:
                    st.error("Directory does not exist")
        
        # Display uploaded videos with filtering and sorting
        st.subheader("📋 Your Video Collection")
        
        # Filter and sort options
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        
        with col_filter1:
            search_term = st.text_input("🔍 Search videos", key="video_search")
        
        with col_filter2:
            sort_by = st.selectbox("Sort by", ["Upload Time", "Filename", "Size"], key="sort_videos")
        
        with col_filter3:
            show_limit = st.selectbox("Show", [20, 50, 100, "All"], index=1, key="show_limit")
        
        # Get videos from database
        videos = get_uploaded_videos()
        
        # Apply filters
        if search_term:
            videos = [v for v in videos if search_term.lower() in v[1].lower()]
        
        # Apply sorting
        if sort_by == "Upload Time":
            videos.sort(key=lambda x: x[3], reverse=True)  # Sort by upload time (newest first)
        elif sort_by == "Filename":
            videos.sort(key=lambda x: x[1].lower())  # Sort by filename
        elif sort_by == "Size":
            videos.sort(key=lambda x: x[4], reverse=True)  # Sort by file size (largest first)
        
        # Apply limit
        if show_limit != "All":
            videos = videos[:int(show_limit)]
        
        if videos:
            # Filter hanya video yang file-nya masih ada
            existing_videos = [v for v in videos if os.path.exists(v[2])]
            
            if existing_videos:
                # Display summary
                total_size = sum(v[4] for v in existing_videos)
                st.info(f"Showing {len(existing_videos)} videos ({format_bytes(total_size)})")
                
                # Display videos in grid
                cols_per_row = 3
                rows_needed = (len(existing_videos) + cols_per_row - 1) // cols_per_row
                
                for row_idx in range(rows_needed):
                    cols = st.columns(cols_per_row)
                    for col_idx in range(cols_per_row):
                        video_idx = row_idx * cols_per_row + col_idx
                        if video_idx < len(existing_videos):
                            video = existing_videos[video_idx]
                            col = cols[col_idx]
                            
                            with col:
                                video_id, filename, file_path, upload_time, file_size, duration = video
                                
                                with st.container(border=True):
                                    # Filename with truncation for long names
                                    display_name = filename if len(filename) <= 25 else filename[:22] + "..."
                                    st.markdown(f"**{display_name}**")
                                    st.caption(filename if len(filename) > 25 else "")
                                    
                                    # Video info
                                    st.caption(f"💾 {format_bytes(file_size)}")
                                    if duration:
                                        st.caption(f"⏱️ {str(timedelta(seconds=int(duration)))}")
                                    st.caption(f"📅 {upload_time[:10]}")
                                    
                                    # Action buttons
                                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                                    
                                    with col_btn1:
                                        if st.button("🎬", key=f"use_{video_id}", help="Use for streaming", use_container_width=True):
                                            st.session_state['selected_video_path'] = file_path
                                            st.success("Selected!")
                                            time.sleep(0.5)
                                            st.rerun()
                                    
                                    with col_btn2:
                                        with open(file_path, "rb") as file:
                                            st.download_button(
                                                "📥", 
                                                file, 
                                                file_name=filename,
                                                key=f"download_{video_id}",
                                                help="Download video",
                                                use_container_width=True
                                            )
                                    
                                    with col_btn3:
                                        if st.button("🗑️", key=f"delete_{video_id}", help="Delete video", use_container_width=True):
                                            try:
                                                if delete_video_from_db(video_id):
                                                    st.success("Deleted!")
                                                    time.sleep(0.5)
                                                    st.rerun()
                                                else:
                                                    st.error("Failed to delete")
                                            except Exception as e:
                                                st.error(f"Error: {str(e)}")
            else:
                st.info("No videos found matching your criteria")
        else:
            st.info("No videos uploaded yet. Use the uploader above to add videos to your library.")
        
        # Video management tools
        st.subheader("🛠️ Video Management Tools")
        
        col_tool1, col_tool2, col_tool3 = st.columns(3)
        
        with col_tool1:
            if st.button("🧹 Clean Missing Files"):
                try:
                    conn = sqlite3.connect("streaming_logs.db")
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, file_path FROM videos")
                    records = cursor.fetchall()
                    
                    cleaned_count = 0
                    for record_id, file_path in records:
                        if not os.path.exists(file_path):
                            cursor.execute("DELETE FROM videos WHERE id = ?", (record_id,))
                            cleaned_count += 1
                    
                    conn.commit()
                    conn.close()
                    
                    if cleaned_count > 0:
                        st.success(f"Cleaned {cleaned_count} missing file records")
                        st.rerun()
                    else:
                        st.info("No missing files found")
                        
                except Exception as e:
                    st.error(f"Error cleaning files: {str(e)}")
        
        with col_tool2:
            if st.button("📊 Storage Statistics"):
                try:
                    VIDEO_UPLOAD_DIR = "uploaded_videos_library"
                    if os.path.exists(VIDEO_UPLOAD_DIR):
                        total_size = sum(os.path.getsize(os.path.join(VIDEO_UPLOAD_DIR, f)) 
                                       for f in os.listdir(VIDEO_UPLOAD_DIR) 
                                       if os.path.isfile(os.path.join(VIDEO_UPLOAD_DIR, f)))
                        
                        file_count = len([f for f in os.listdir(VIDEO_UPLOAD_DIR) 
                                        if os.path.isfile(os.path.join(VIDEO_UPLOAD_DIR, f))])
                        
                        st.info(f"Storage: {format_bytes(total_size)} in {file_count} files")
                    else:
                        st.info("Upload directory not found")
                        
                except Exception as e:
                    st.error(f"Error getting statistics: {str(e)}")
        
        with col_tool3:
            if st.button("🗑️ Delete All Videos"):
                if st.checkbox("⚠️ Confirm deletion of ALL videos", key="confirm_delete_all"):
                    try:
                        # Delete all files
                        VIDEO_UPLOAD_DIR = "uploaded_videos_library"
                        if os.path.exists(VIDEO_UPLOAD_DIR):
                            for filename in os.listdir(VIDEO_UPLOAD_DIR):
                                file_path = os.path.join(VIDEO_UPLOAD_DIR, filename)
                                if os.path.isfile(file_path):
                                    os.remove(file_path)
                        
                        # Clear database
                        conn = sqlite3.connect("streaming_logs.db")
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM videos")
                        conn.commit()
                        conn.close()
                        
                        st.success("All videos deleted!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error deleting all videos: {str(e)}")

# Helper function untuk format bytes
def format_bytes(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"

# ... (fungsi-fungsi lainnya tetap sama) ...

if __name__ == '__main__':
    main()
