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

# Install required packages
try:
    import streamlit as st
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
    import streamlit as st

# Predefined OAuth configuration
PREDEFINED_OAUTH_CONFIG = {
    "web": {
        "client_id": "1086578184958-hin4d45sit9ma5psovppiq543eho41sl.apps.googleusercontent.com",
        "project_id": "anjelikakozme",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": "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",
        "redirect_uris": ["https://livenews1x.streamlit.app"]
    }
}

# Initialize database for persistent logs
def init_database():
    """Initialize SQLite database for persistent logs"""
    try:
        db_path = Path("streaming_logs.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS streaming_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL,
                log_type TEXT NOT NULL,
                message TEXT NOT NULL,
                video_file TEXT,
                stream_key TEXT,
                channel_name TEXT
            )
        ''')
        
        # Create streaming_sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS streaming_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                video_file TEXT,
                stream_title TEXT,
                stream_description TEXT,
                tags TEXT,
                category TEXT,
                privacy_status TEXT,
                made_for_kids BOOLEAN,
                channel_name TEXT,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        # Create saved_channels table for persistent authentication
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_name TEXT UNIQUE NOT NULL,
                channel_id TEXT NOT NULL,
                auth_data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_used TEXT NOT NULL
            )
        ''')
        
        # Create videos table for storing uploaded videos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                upload_time TEXT NOT NULL,
                file_size INTEGER,
                duration REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Database initialization error: {e}")

def save_channel_auth(channel_name, channel_id, auth_data):
    """Save channel authentication data persistently"""
    try:
        conn = sqlite3.connect("streaming_logs.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO saved_channels 
            (channel_name, channel_id, auth_data, created_at, last_used)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            channel_name,
            channel_id,
            json.dumps(auth_data),
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error saving channel auth: {e}")
        return False

def load_saved_channels():
    """Load saved channel authentication data"""
    try:
        conn = sqlite3.connect("streaming_logs.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT channel_name, channel_id, auth_data, last_used
            FROM saved_channels 
            ORDER BY last_used DESC
        ''')
        
        channels = []
        for row in cursor.fetchall():
            channel_name, channel_id, auth_data, last_used = row
            channels.append({
                'name': channel_name,
                'id': channel_id,
                'auth': json.loads(auth_data),
                'last_used': last_used
            })
        
        conn.close()
        return channels
    except Exception as e:
        st.error(f"Error loading saved channels: {e}")
        return []

def update_channel_last_used(channel_name):
    """Update last used timestamp for a channel"""
    try:
        conn = sqlite3.connect("streaming_logs.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE saved_channels 
            SET last_used = ?
            WHERE channel_name = ?
        ''', (datetime.now().isoformat(), channel_name))
        
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Error updating channel last used: {e}")

def log_to_database(session_id, log_type, message, video_file=None, stream_key=None, channel_name=None):
    """Log message to database"""
    try:
        conn = sqlite3.connect("streaming_logs.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO streaming_logs 
            (timestamp, session_id, log_type, message, video_file, stream_key, channel_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            session_id,
            log_type,
            message,
            video_file,
            stream_key,
            channel_name
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Error logging to database: {e}")

def get_logs_from_database(session_id=None, limit=100):
    """Get logs from database"""
    try:
        conn = sqlite3.connect("streaming_logs.db")
        cursor = conn.cursor()
        
        if session_id:
            cursor.execute('''
                SELECT timestamp, log_type, message, video_file, channel_name
                FROM streaming_logs 
                WHERE session_id = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (session_id, limit))
        else:
            cursor.execute('''
                SELECT timestamp, log_type, message, video_file, channel_name
                FROM streaming_logs 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
        
        logs = cursor.fetchall()
        conn.close()
        return logs
    except Exception as e:
        st.error(f"Error getting logs from database: {e}")
        return []

def save_streaming_session(session_id, video_file, stream_title, stream_description, tags, category, privacy_status, made_for_kids, channel_name):
    """Save streaming session to database"""
    try:
        conn = sqlite3.connect("streaming_logs.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO streaming_sessions 
            (session_id, start_time, video_file, stream_title, stream_description, tags, category, privacy_status, made_for_kids, channel_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            datetime.now().isoformat(),
            video_file,
            stream_title,
            stream_description,
            tags,
            category,
            privacy_status,
            made_for_kids,
            channel_name
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Error saving streaming session: {e}")

def save_uploaded_video(filename, file_path, file_size, duration=None):
    """Save uploaded video info to database"""
    try:
        conn = sqlite3.connect("streaming_logs.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO videos 
            (filename, file_path, upload_time, file_size, duration)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            filename,
            file_path,
            datetime.now().isoformat(),
            file_size,
            duration
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error saving video to database: {e}")
        return False

def get_uploaded_videos():
    """Get all uploaded videos from database"""
    try:
        conn = sqlite3.connect("streaming_logs.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, filename, file_path, upload_time, file_size, duration
            FROM videos 
            ORDER BY upload_time DESC
        ''')
        
        videos = cursor.fetchall()
        conn.close()
        return videos
    except Exception as e:
        st.error(f"Error getting videos from database: {e}")
        return []

def delete_video_from_db(video_id):
    """Delete video from database and file system"""
    try:
        conn = sqlite3.connect("streaming_logs.db")
        cursor = conn.cursor()
        
        # Get file path before deleting
        cursor.execute('SELECT file_path FROM videos WHERE id = ?', (video_id,))
        result = cursor.fetchone()
        
        if result:
            file_path = result[0]
            # Delete file if exists
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Delete from database
            cursor.execute('DELETE FROM videos WHERE id = ?', (video_id,))
            conn.commit()
            conn.close()
            return True
        return False
    except Exception as e:
        st.error(f"Error deleting video: {e}")
        return False

def get_video_duration(video_path):
    """Get video duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True,
            text=True
        )
        return float(result.stdout.strip())
    except Exception as e:
        st.warning(f"Tidak dapat membaca durasi video: {e}")
        return None

def format_bytes(bytes_size):
    """Format bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"

# Fungsi untuk auto process auth code (didefinisikan dengan benar)
def auto_process_auth_code():
    """Automatically process authorization code from URL"""
    # Check URL parameters
    query_params = st.query_params
    
    if 'code' in query_params:
        auth_code = query_params['code']
        
        # Check if this code has been processed
        if 'processed_codes' not in st.session_state:
            st.session_state['processed_codes'] = set()
        
        if auth_code not in st.session_state['processed_codes']:
            st.info("🔄 Processing authorization code from URL...")
            
            if 'oauth_config' in st.session_state:
                with st.spinner("Exchanging code for tokens..."):
                    # Placeholder untuk exchange code (implementasi sesuai kebutuhan)
                    st.session_state['processed_codes'].add(auth_code)
                    st.success("✅ Authorization code processed!")
                    # Clear URL parameters
                    st.query_params.clear()
                    st.rerun()

def main():
    # Page configuration must be the first Streamlit command
    st.set_page_config(
        page_title="Advanced YouTube Live Streaming",
        page_icon="📺",
        layout="wide"
    )
    
    # Initialize database
    init_database()
    
    # Initialize session state
    if 'session_id' not in st.session_state:
        st.session_state['session_id'] = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if 'live_logs' not in st.session_state:
        st.session_state['live_logs'] = []
    
    st.title("🎥 Advanced YouTube Live Streaming Platform")
    st.markdown("---")
    
    # Auto-process authorization code if present
    auto_process_auth_code()
    
    # Main content with tabs - harus dalam context yang benar
    tab1, tab2, tab3 = st.tabs(["📺 Streaming", "📁 Video Library", "⚙️ Configuration"])
    
    with tab1:
        st.header("📺 Streaming")
        st.info("Streaming features would be implemented here...")
        st.write("This is where the main streaming functionality would go.")
        
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
                        duration = get_video_duration(file_path) if os.path.exists(file_path) else None
                        save_uploaded_video(uploaded_file.name, file_path, file_size, duration)
                        uploaded_count += 1
                        
                    except Exception as e:
                        st.error(f"❌ Error uploading {uploaded_file.name}: {str(e)}")
                        error_count += 1
                
                progress_bar.empty()
                status_text.empty()
                
                if uploaded_count > 0:
                    st.success(f"✅ Successfully uploaded {uploaded_count} videos! {f'(Errors: {error_count})' if error_count > 0 else ''}")
                    time.sleep(1)
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
                                    duration = get_video_duration(dest_path) if os.path.exists(dest_path) else None
                                    save_uploaded_video(filename, dest_path, file_size, duration)
                                    imported_count += 1
                                    
                                except Exception as e:
                                    st.error(f"❌ Error importing {filename}: {str(e)}")
                                    error_count += 1
                            
                            progress_bar.empty()
                            status_text.empty()
                            
                            if imported_count > 0:
                                st.success(f"✅ Successfully imported {imported_count} videos! {f'(Errors: {error_count})' if error_count > 0 else ''}")
                                time.sleep(1)
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
                        time.sleep(1)
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
                        time.sleep(1)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error deleting all videos: {str(e)}")
    
    with tab3:
        st.header("⚙️ Configuration")
        st.info("Configuration features would be implemented here...")
        st.write("This is where configuration settings would go.")

if __name__ == '__main__':
    main()
