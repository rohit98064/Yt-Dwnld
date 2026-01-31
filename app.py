from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from pytube import YouTube
import os
import re

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)  # Enable CORS for frontend requests

DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/get_video_info', methods=['POST'])
def get_video_info():
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        
        # Create YouTube object
        yt = YouTube(url)
        
        # Get available streams
        streams = []
        for stream in yt.streams.filter(progressive=True):
            streams.append({
                'itag': stream.itag,
                'mime_type': stream.mime_type,
                'resolution': stream.resolution,
                'filesize': stream.filesize_mb if hasattr(stream, 'filesize_mb') else f"{stream.filesize / (1024*1024):.2f}MB",
                'quality': stream.quality,
                'type': 'video+audio' if stream.is_progressive else 'video only'
            })
        
        # Add audio-only streams
        for stream in yt.streams.filter(only_audio=True):
            streams.append({
                'itag': stream.itag,
                'mime_type': stream.mime_type,
                'resolution': 'audio only',
                'filesize': stream.filesize_mb if hasattr(stream, 'filesize_mb') else f"{stream.filesize / (1024*1024):.2f}MB",
                'quality': stream.abr if hasattr(stream, 'abr') else 'audio',
                'type': 'audio only'
            })
        
        return jsonify({
            'title': yt.title,
            'author': yt.author,
            'length': yt.length,
            'views': yt.views,
            'thumbnail_url': yt.thumbnail_url,
            'formats': streams
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download', methods=['POST'])
def download_video():
    try:
        data = request.json
        url = data.get('url')
        itag = data.get('itag')
        
        if not url or not itag:
            return jsonify({'error': 'Missing parameters'}), 400
        
        yt = YouTube(url)
        stream = yt.streams.get_by_itag(int(itag))
        
        if not stream:
            return jsonify({'error': 'Stream not found'}), 404
        
        # Clean filename for safe download
        filename = re.sub(r'[^\w\s-]', '', yt.title)
        filename = re.sub(r'[-\s]+', '-', filename)
        
        # Add appropriate extension
        if 'audio' in stream.mime_type:
            filename += '.mp3'
        elif 'mp4' in stream.mime_type:
            filename += '.mp4'
        else:
            filename += '.mp4'
        
        # Download the stream
        download_path = stream.download(output_path=DOWNLOAD_FOLDER, filename=filename)
        
        # Send the file
        response = send_file(
            download_path,
            as_attachment=True,
            download_name=filename,
            mimetype=stream.mime_type
        )
        
        # Clean up the file after sending (optional, but recommended for server storage)
        @response.call_on_close
        def cleanup_file():
            try:
                os.remove(download_path)
            except:
                pass
        
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Cleanup downloaded files"""
    try:
        for file in os.listdir(DOWNLOAD_FOLDER):
            file_path = os.path.join(DOWNLOAD_FOLDER, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        return jsonify({'message': 'Cleanup successful'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)