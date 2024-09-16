from flask import Flask, request, jsonify, render_template, send_from_directory, url_for
import yt_dlp
import os
import ffmpeg
import subprocess

app = Flask(__name__)

# المسار الذي سيتم حفظ الفيديوهات فيه
DOWNLOAD_PATH = os.path.join(os.path.dirname(__file__), 'uploads')
if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)

@app.route('/')
def index():
    return render_template('index.html')  # صفحة HTML تحتوي على حقل إدخال وزر للتنزيل



def run_yt_dlp(url, cookies_path):
    try:
        result = subprocess.run(
            ['yt-dlp', '--cookies', cookies_path, url],
            capture_output=True,
            text=True
        )
        print("Standard Output:", result.stdout)
        print("Error Output:", result.stderr)
        if result.returncode != 0:
            raise Exception(f"yt-dlp failed with code {result.returncode}")
    except Exception as e:
        print(f"Error: {str(e)}")


@app.route('/get_formats')
def get_formats():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'رابط الفيديو مفقود'}), 400

    cookies_path = os.path.join(os.path.dirname(__file__), 'cookies.txt')
    
    # تشغيل yt-dlp من خلال subprocess
    run_yt_dlp(url, cookies_path)
    
    try:
        ydl_opts = {
            'cookies': cookies_path,
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',

        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            formats = info_dict.get('formats', [])
        
        format_list = [
            {
                "format_id": f.get("format_id", "unknown"),
                "resolution": f.get("resolution", "unknown"),
                "filesize": f.get("filesize", 0),
                "format_note": f.get("format_note", "No additional notes"),
            }
            for f in formats
            if f.get("vcodec", "none") != "none"
        ]

        return jsonify(format_list)

    except Exception as e:
        return jsonify({'error': f"حدث خطأ أثناء جلب الجودات: {str(e)}"}), 500

@app.route('/download', methods=['POST'])
def download_video():
    data = request.form
    url = data.get('url')
    format_id = data.get('format_id')
    video_file_path = None
    audio_file_path = None

    try:
        # إعدادات yt-dlp لتنزيل الفيديو والصوت
        cookies_path = os.path.join(os.path.dirname(__file__), 'cookies.txt')
        ydl_opts = {
            
            'outtmpl': os.path.join(DOWNLOAD_PATH, '%(title)s.%(ext)s'),
            'format': f'{format_id}+bestaudio/best',
            'merge_output_format': 'mp4',
            'cookies':cookies_path,
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',

        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_file_path = ydl.prepare_filename(info_dict)
            audio_file_path = video_file_path.rsplit('.', 1)[0] + '.m4a'  # افتراضياً الصوت سيكون بصيغة m4a

        # التأكد من وجود الملف النهائي بصيغة mp4
        if not video_file_path.endswith('.mp4'):
            video_file_path = video_file_path.rsplit('.', 1)[0] + '.mp4'

        # دمج الفيديو والصوت إذا كانا منفصلين
        if os.path.isfile(video_file_path) and os.path.isfile(audio_file_path):
            merged_file_path = video_file_path.rsplit('.', 1)[0] + '_merged.mp4'
            if not os.path.isfile(merged_file_path):
                # دمج الصوت والفيديو
                ffmpeg.input(video_file_path).output(audio_file_path, vcodec='copy', acodec='aac', strict='experimental').run()
                os.rename(video_file_path, merged_file_path)  # إعادة تسمية الملف النهائي
                video_file_path = merged_file_path

        # تحقق من وجود الملف قبل محاولة إرساله
        if not os.path.isfile(video_file_path):
            return jsonify({'error': 'الملف غير موجود'}), 500

        # إنشاء رابط التحميل
        file_url = url_for('download_file', filename=os.path.basename(video_file_path), _external=True)
        return jsonify({
            'url': file_url,
            'filename': os.path.basename(video_file_path)
        })

    except yt_dlp.DownloadError as e:
        return jsonify({'error': f"حدث خطأ أثناء التحميل باستخدام yt-dlp: {str(e)}"}), 500
    except Exception as e:
        return jsonify({'error': f"حدث خطأ أثناء التحميل: {str(e)}"}), 500

@app.route('/file/<filename>')
def download_file(filename):
    return send_from_directory(DOWNLOAD_PATH, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
