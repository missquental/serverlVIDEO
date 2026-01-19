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
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow

# Install required packages
try:
    import streamlit as st
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
    import streamlit as st

try:
    import google.auth
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import Flow
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-auth", "google-auth-oauthlib", "google-api-python-client"])
    import google.auth
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import Flow

# Konfigurasi OAuth untuk redirect otomatis
OAUTH_CONFIG = {
    "web": {
        "client_id": "1086578184958-hin4d45sit9ma5psovppiq543eho41sl.apps.googleusercontent.com",
        "project_id": "anjelikakozme", 
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": "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",
        "redirect_uris": ["http://localhost:8501", "https://livenews1x.streamlit.app"]
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

def setup_oauth_flow(redirect_uri):
    """Setup OAuth flow dengan redirect otomatis"""
    flow = Flow.from_client_config(
        OAUTH_CONFIG,
        scopes=['https://www.googleapis.com/auth/youtube.force-ssl'],
        redirect_uri=redirect_uri
    )
    return flow

def auto_handle_oauth():
    """Handle OAuth secara otomatis dengan redirect"""
    
    # Cek jika ada code di URL parameters
    query_params = st.query_params
    
    if 'code' in query_params:
        auth_code = query_params['code']
        
        # Cek apakah code sudah diproses
        if 'oauth_processed' not in st.session_state:
            st.session_state['oauth_processed'] = set()
            
        if auth_code not in st.session_state['oauth_processed']:
            st.info("🔄 Memproses otomatis authorization code...")
            
            # Tentukan redirect URI yang digunakan berdasarkan environment saat ini
            try:
                # Dapatkan base URL dari Streamlit
                base_url = st.query_params.to_dict().get('_stcore_host', [''])[0] if hasattr(st.query_params, 'to_dict') else "http://localhost:8501"
                if not base_url:
                    base_url = "http://localhost:8501"
            except:
                base_url = "http://localhost:8501"
            
            redirect_uri = base_url.rstrip('/')
            
            try:
                # Setup flow dengan redirect URI yang sesuai
                flow = setup_oauth_flow(redirect_uri)
                
                # Tukar code dengan token
                flow.fetch_token(code=auth_code)
                
                # Simpan credentials
                credentials = flow.credentials
                st.session_state['credentials'] = credentials_to_dict(credentials)
                st.session_state['oauth_processed'].add(auth_code)
                
                # Buat YouTube service
                service = create_youtube_service(st.session_state['credentials'])
                if service:
                    channels = get_channel_info(service)
                    if channels:
                        channel = channels[0]
                        st.session_state['youtube_service'] = service
                        st.session_state['channel_info'] = channel
                        
                        # Simpan channel auth secara persisten
                        save_channel_auth(
                            channel['snippet']['title'],
                            channel['id'],
                            st.session_state['credentials']
                        )
                        
                        st.success(f"✅ Berhasil terhubung ke: {channel['snippet']['title']}")
                        
                        # Bersihkan URL parameters
                        st.query_params.clear()
                        st.rerun()
                        
            except Exception as e:
                st.error(f"❌ Error dalam pemrosesan otomatis: {str(e)}")
                return False
                
        return True
        
    return False

def initiate_oauth_redirect():
    """Initiate OAuth redirect secara otomatis"""
    try:
        # Tentukan redirect URI berdasarkan environment saat ini
        try:
            # Dapatkan base URL dari Streamlit
            base_url = st.query_params.to_dict().get('_stcore_host', [''])[0] if hasattr(st.query_params, 'to_dict') else "http://localhost:8501"
            if not base_url:
                base_url = "http://localhost:8501"
        except:
            base_url = "http://localhost:8501"
        
        redirect_uri = base_url.rstrip('/')
        
        # Jika redirect_uri tidak valid, gunakan default
        if not redirect_uri or 'None' in redirect_uri:
            redirect_uri = "http://localhost:8501"
        
        flow = setup_oauth_flow(redirect_uri)
        
        # Generate authorization URL
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        # Simpan state untuk verifikasi
        st.session_state['oauth_state'] = state
        
        # Redirect otomatis menggunakan JavaScript
        st.markdown(f"""
        <script>
            window.location.href = "{authorization_url}";
        </script>
        """, unsafe_allow_html=True)
        
        st.info("🔄 Mengarahkan ke halaman autorisasi Google...")
        return True
        
    except Exception as e:
        st.error(f"❌ Gagal menginisiasi redirect: {str(e)}")
        return False

def credentials_to_dict(credentials):
    """Convert credentials object to dictionary"""
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

def dict_to_credentials(credentials_dict):
    """Convert dictionary to credentials object"""
    return Credentials(
        token=credentials_dict['token'],
        refresh_token=credentials_dict['refresh_token'],
        token_uri=credentials_dict['token_uri'],
        client_id=credentials_dict['client_id'],
        client_secret=credentials_dict['client_secret'],
        scopes=credentials_dict['scopes']
    )

def create_youtube_service(credentials_dict):
    """Create YouTube API service from credentials"""
    try:
        # Handle both old and new credential formats
        if isinstance(credentials_dict, Credentials):
            credentials = credentials_dict
        elif 'token' in credentials_dict:
            credentials = dict_to_credentials(credentials_dict)
        else:
            credentials = Credentials(
                token=credentials_dict.get('access_token') or credentials_dict.get('token'),
                refresh_token=credentials_dict.get('refresh_token'),
                token_uri=credentials_dict.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=credentials_dict.get('client_id'),
                client_secret=credentials_dict.get('client_secret'),
                scopes=credentials_dict.get('scopes', ['https://www.googleapis.com/auth/youtube.force-ssl'])
            )
            
        service = build('youtube', 'v3', credentials=credentials)
        return service
    except Exception as e:
        st.error(f"Error creating YouTube service: {e}")
        return None

def get_channel_info(service, channel_id=None):
    """Get channel information from YouTube API"""
    try:
        if channel_id:
            request = service.channels().list(
                part="snippet,statistics",
                id=channel_id
            )
        else:
            request = service.channels().list(
                part="snippet,statistics",
                mine=True
            )
        
        response = request.execute()
        return response.get('items', [])
    except Exception as e:
        st.error(f"Error fetching channel info: {e}")
        return []

def get_stream_key_only(service):
    """Get stream key without creating broadcast"""
    try:
        # Create a simple live stream to get stream key
        stream_request = service.liveStreams().insert(
            part="snippet,cdn",
            body={
                "snippet": {
                    "title": f"Stream Key Generator - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
                },
                "cdn": {
                    "resolution": "1080p",
                    "frameRate": "30fps",
                    "ingestionType": "rtmp"
                }
            }
        )
        stream_response = stream_request.execute()
        
        return {
            "stream_key": stream_response['cdn']['ingestionInfo']['streamName'],
            "stream_url": stream_response['cdn']['ingestionInfo']['ingestionAddress'],
            "stream_id": stream_response['id']
        }
    except Exception as e:
        st.error(f"Error getting stream key: {e}")
        return None

def show_auto_auth_button():
    """Tampilkan tombol untuk auto login"""
    st.markdown("### 🔐 Auto Login ke YouTube")
    st.info("Klik tombol di bawah untuk login otomatis ke YouTube")
    
    if st.button("🔑 Auto Login ke YouTube", key="auto_login_btn", type="primary"):
        if initiate_oauth_redirect():
            st.info("🔄 Mengarahkan ke halaman autorisasi...")
        else:
            st.error("❌ Gagal memulai proses autorisasi")

def main():
    # Page configuration
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
    
    st.title("🎥 Advanced YouTube Live Streaming Platform")
    st.markdown("---")
    
    # Sidebar untuk konfigurasi
    with st.sidebar:
        st.header("📋 Configuration")
        
        # Session info
        st.info(f"🆔 Session: {st.session_state['session_id']}")
        
        # Saved Channels Section
        st.subheader("💾 Saved Channels")
        saved_channels = load_saved_channels()
        
        if saved_channels:
            st.write("**Previously authenticated channels:**")
            for channel in saved_channels:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"📺 {channel['name']}")
                    st.caption(f"Last used: {channel['last_used'][:10]}")
                
                with col2:
                    if st.button("🔑 Use", key=f"use_{channel['name']}"):
                        # Load this channel's authentication
                        service = create_youtube_service(channel['auth'])
                        if service:
                            # Verify the authentication is still valid
                            channels = get_channel_info(service)
                            if channels:
                                channel_info = channels[0]
                                st.session_state['youtube_service'] = service
                                st.session_state['channel_info'] = channel_info
                                update_channel_last_used(channel['name'])
                                st.success(f"✅ Loaded: {channel['name']}")
                                st.rerun()
                            else:
                                st.error("❌ Authentication expired")
                        else:
                            st.error("❌ Failed to load authentication")
        else:
            st.info("No saved channels. Authenticate below to save.")
        
        # Auto handle OAuth jika ada code di URL
        if auto_handle_oauth():
            st.success("✅ Authentication berhasil!")
            st.rerun()
        
        # Tombol auto login jika belum terautentikasi
        if 'youtube_service' not in st.session_state:
            show_auto_auth_button()
        else:
            # Sudah terautentikasi
            channel = st.session_state['channel_info']
            st.success(f"✅ Connected to: {channel['snippet']['title']}")
            st.write(f"**Subscribers:** {channel['statistics'].get('subscriberCount', 'Hidden')}")
            st.write(f"**Views:** {channel['statistics'].get('viewCount', '0')}")
            
            # Tombol logout
            if st.button("🚪 Logout"):
                keys_to_remove = ['youtube_service', 'channel_info', 'credentials', 'oauth_processed']
                for key in keys_to_remove:
                    if key in st.session_state:
                        del st.session_state[key]
                st.success("Logged out successfully!")
                st.rerun()

# Fungsi tambahan yang dibutuhkan untuk kelengkapan
def get_youtube_categories():
    """Get YouTube video categories"""
    return {
        "1": "Film & Animation",
        "2": "Autos & Vehicles", 
        "10": "Music",
        "15": "Pets & Animals",
        "17": "Sports",
        "19": "Travel & Events",
        "20": "Gaming",
        "22": "People & Blogs",
        "23": "Comedy",
        "24": "Entertainment",
        "25": "News & Politics",
        "26": "Howto & Style",
        "27": "Education",
        "28": "Science & Technology"
    }

def create_live_stream(service, title, description, scheduled_start_time, tags=None, category_id="20", privacy_status="public", made_for_kids=False):
    """Create a live stream on YouTube with complete settings"""
    try:
        # Create live stream
        stream_request = service.liveStreams().insert(
            part="snippet,cdn",
            body={
                "snippet": {
                    "title": title,
                    "description": description
                },
                "cdn": {
                    "resolution": "1080p",
                    "frameRate": "30fps",
                    "ingestionType": "rtmp"
                }
            }
        )
        stream_response = stream_request.execute()
        
        # Prepare broadcast body
        broadcast_body = {
            "snippet": {
                "title": title,
                "description": description,
                "scheduledStartTime": scheduled_start_time.isoformat()
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": made_for_kids,
                "enableAutoStart": True,
                "enableAutoStop": True
            },
            "contentDetails": {
                "enableAutoStart": True,
                "enableAutoStop": True,
                "recordFromStart": True,
                "enableContentEncryption": False,
                "enableEmbed": True,
                "enableDvr": True,
                "enableLowLatency": False
            }
        }
        
        if tags:
            broadcast_body["snippet"]["tags"] = tags
            
        if category_id:
            broadcast_body["snippet"]["categoryId"] = category_id
        
        broadcast_request = service.liveBroadcasts().insert(
            part="snippet,status,contentDetails",
            body=broadcast_body
        )
        broadcast_response = broadcast_request.execute()
        
        bind_request = service.liveBroadcasts().bind(
            part="id,contentDetails",
            id=broadcast_response['id'],
            streamId=stream_response['id']
        )
        bind_response = bind_request.execute()
        
        return {
            "stream_key": stream_response['cdn']['ingestionInfo']['streamName'],
            "stream_url": stream_response['cdn']['ingestionInfo']['ingestionAddress'],
            "broadcast_id": broadcast_response['id'],
            "stream_id": stream_response['id'],
            "watch_url": f"https://www.youtube.com/watch?v={broadcast_response['id']}",
            "studio_url": f"https://studio.youtube.com/video/{broadcast_response['id']}/livestreaming",
            "broadcast_response": broadcast_response
        }
    except Exception as e:
        st.error(f"Error creating live stream: {e}")
        return None

def get_existing_broadcasts(service, max_results=10):
    """Get existing live broadcasts"""
    try:
        request = service.liveBroadcasts().list(
            part="snippet,status,contentDetails",
            mine=True,
            maxResults=max_results,
            broadcastStatus="all"
        )
        response = request.execute()
        return response.get('items', [])
    except Exception as e:
        st.error(f"Error getting existing broadcasts: {e}")
        return []

if __name__ == '__main__':
    main()
