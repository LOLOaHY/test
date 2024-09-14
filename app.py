from flask import Flask, request, send_file, render_template
import yt_dlp
import os

app = Flask(__name__)

# مسار مجلد لتحميل الفيديوهات
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')  # صفحة HTML فيها حقل لإدخال الرابط وزر لتحميل الفيديو

@app.route('/download', methods=['POST'])
def download_video():
    url = request.form['url']
    
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_file = ydl.prepare_filename(info)
            
            return send_file(video_file, as_attachment=True)
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)
