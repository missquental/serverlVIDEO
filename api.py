from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List
import os
import uuid
from datetime import datetime
import json
from pathlib import Path
import shutil

app = FastAPI(title="Video Streaming API", version="1.0.0")

# Konfigurasi direktori penyimpanan
UPLOAD_DIR = "uploaded_videos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Model data video
class VideoInfo:
    def __init__(self, video_id: str, filename: str, size: int, upload_date: str):
        self.id = video_id
        self.filename = filename
        self.size = size
        self.upload_date = upload_date

# Helper functions
def get_video_info(video_id: str):
    metadata_file = os.path.join(UPLOAD_DIR, f"{video_id}.json")
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r') as f:
            return json.load(f)
    return None

def get_all_videos():
    videos = []
    for filename in os.listdir(UPLOAD_DIR):
        if filename.endswith('.json'):
            video_id = filename.replace('.json', '')
            video_info = get_video_info(video_id)
            if video_info:
                videos.append(video_info)
    return videos

def format_bytes(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

@app.get("/")
async def root():
    return {"message": "Video Streaming API is running!"}

@app.get("/health")
async def health_check():
    # Hitung total video dan ukuran storage
    total_videos = len([f for f in os.listdir(UPLOAD_DIR) if f.endswith('.json')])
    total_size = sum(os.path.getsize(os.path.join(UPLOAD_DIR, f)) 
                     for f in os.listdir(UPLOAD_DIR) 
                     if f.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')))
    
    return {
        "status": "healthy",
        "total_videos": total_videos,
        "storage_used": format_bytes(total_size)
    }

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    try:
        # Generate unique ID
        video_id = str(uuid.uuid4())[:8]
        file_extension = file.filename.split('.')[-1]
        safe_filename = f"{video_id}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Save metadata
        file_size = os.path.getsize(file_path)
        metadata = {
            "id": video_id,
            "filename": file.filename,
            "safe_filename": safe_filename,
            "size": file_size,
            "upload_date": datetime.now().isoformat(),
            "content_type": file.content_type
        }
        
        metadata_file = os.path.join(UPLOAD_DIR, f"{video_id}.json")
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)
        
        return JSONResponse(content={
            "status": "success",
            "message": "Video uploaded successfully",
            "video_id": video_id,
            "filename": file.filename,
            "size": file_size
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/videos")
async def list_videos():
    videos = get_all_videos()
    return {"videos": videos, "count": len(videos)}

@app.get("/stream/{video_id}")
async def stream_video(video_id: str, range_header: str = None):
    # Get video metadata
    video_info = get_video_info(video_id)
    if not video_info:
        raise HTTPException(status_code=404, detail="Video not found")
    
    file_path = os.path.join(UPLOAD_DIR, video_info["safe_filename"])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    file_size = os.path.getsize(file_path)
    
    # Handle range requests for seeking
    if range_header:
        byte1, byte2 = 0, file_size - 1
        match = range_header.replace('bytes=', '').split('-')
        if match[0]:
            byte1 = int(match[0])
        if match[1]:
            byte2 = int(match[1])
        else:
            byte2 = file_size - 1
        
        chunk_size = byte2 - byte1 + 1
        
        def iterfile():
            with open(file_path, 'rb') as f:
                f.seek(byte1)
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    yield chunk
        
        headers = {
            'Content-Range': f'bytes {byte1}-{byte2}/{file_size}',
            'Accept-Ranges': 'bytes',
            'Content-Length': str(chunk_size),
            'Content-Type': video_info.get('content_type', 'video/mp4')
        }
        
        return StreamingResponse(
            iterfile(),
            status_code=206,
            headers=headers
        )
    else:
        # Full file streaming
        def iterfile():
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    yield chunk
        
        return StreamingResponse(
            iterfile(),
            media_type=video_info.get('content_type', 'video/mp4'),
            headers={
                'Accept-Ranges': 'bytes',
                'Content-Length': str(file_size)
            }
        )

@app.delete("/delete/{video_id}")
async def delete_video(video_id: str):
    try:
        # Get video metadata
        video_info = get_video_info(video_id)
        if not video_info:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Delete video file
        file_path = os.path.join(UPLOAD_DIR, video_info["safe_filename"])
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete metadata file
        metadata_file = os.path.join(UPLOAD_DIR, f"{video_id}.json")
        if os.path.exists(metadata_file):
            os.remove(metadata_file)
        
        return {"status": "success", "message": "Video deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
