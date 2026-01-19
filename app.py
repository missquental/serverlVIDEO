import streamlit as st
import urllib.parse
from google_auth_oauthlib.flow import Flow
import google.auth.transport.requests
from google.oauth2.credentials import Credentials

# Konfigurasi OAuth untuk redirect otomatis
OAUTH_CONFIG = {
    "web": {
        "client_id": "1086578184958-hin4d45sit9ma5psovppiq543eho41sl.apps.googleusercontent.com",
        "project_id": "anjelikakozme", 
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": "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",
        "redirect_uris": ["http://localhost:8501", "https://livenews1x.streamlit.app"]  # Multiple redirect URIs
    }
}

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
            
            # Tentukan redirect URI yang digunakan
            redirect_uri = st.request.url_root.rstrip('/') if hasattr(st, 'request') else "http://localhost:8501"
            
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
        # Tentukan redirect URI berdasarkan environment
        if 'localhost' in st.request.url_root or '127.0.0.1' in st.request.url_root:
            redirect_uri = "http://localhost:8501"
        else:
            redirect_uri = "https://livenews1x.streamlit.app"
            
        flow = setup_oauth_flow(redirect_uri)
        
        # Generate authorization URL
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        # Simpan state untuk verifikasi
        st.session_state['oauth_state'] = state
        
        # Redirect otomatis
        st.markdown(f"""
        <meta http-equiv="refresh" content="0;url={authorization_url}">
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

# Modifikasi fungsi create_youtube_service untuk handle credentials baru
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

# Fungsi untuk tombol auto-login
def show_auto_auth_button():
    """Tampilkan tombol untuk auto login"""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("### 🔐 Auto Login ke YouTube")
        st.info("Klik tombol di samping untuk login otomatis ke YouTube")
    
    with col2:
        if st.button("🔑 Auto Login", key="auto_login_btn"):
            if initiate_oauth_redirect():
                st.info("🔄 Mengarahkan ke halaman autorisasi...")
            else:
                st.error("❌ Gagal memulai proses autorisasi")

# Integrasi dalam main function
def main():
    # ... kode lainnya ...
    
    # Di bagian sidebar atau tempat yang sesuai
    if 'youtube_service' not in st.session_state:
        # Coba handle OAuth otomatis dulu
        if not auto_handle_oauth():
            # Jika tidak ada proses otomatis, tampilkan tombol manual
            show_auto_auth_button()
    else:
        # Sudah terautentikasi
        st.success("✅ Sudah terautentikasi ke YouTube")
        
        # Tampilkan info channel
        if 'channel_info' in st.session_state:
            channel = st.session_state['channel_info']
            st.write(f"📺 Channel: {channel['snippet']['title']}")
