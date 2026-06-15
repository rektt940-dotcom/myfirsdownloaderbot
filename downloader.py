import os
import yt_dlp
import imageio_ffmpeg
import requests

def get_pytubefix_url(url, format_type='video'):
    try:
        from pytubefix import YouTube
        yt = YouTube(url, use_po_token=True)
        if format_type == 'audio':
            stream = yt.streams.get_audio_only()
        else:
            stream = yt.streams.get_highest_resolution()
        if stream and stream.url:
            return stream.url
    except Exception as e:
        print("Pytubefix error:", e)
    return None

def get_dl_opts(user_id, quality='best', format_type='video'):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    outtmpl = os.path.join(base_dir, f'downloads/{user_id}_%(id)s.%(ext)s')
    os.makedirs(os.path.join(base_dir, 'downloads'), exist_ok=True)
    
    opts = {
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': imageio_ffmpeg.get_ffmpeg_exe(),
    }
    
    cookie_path = os.path.join(base_dir, 'cookies.txt')
    if os.path.exists(cookie_path):
        opts['cookiefile'] = cookie_path
    
    if format_type == 'audio':
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    else:
        if quality == 'worst':
            opts['format'] = 'worst'
        else:
            opts['format'] = 'best'
            
    return opts

def download_media(url, user_id, quality='best', format_type='video'):
    opts = get_dl_opts(user_id, quality, format_type)
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            if format_type == 'audio':
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                filename = os.path.splitext(filename)[0] + '.mp3'
                return {'status': 'success', 'type': 'file', 'filepath': filename, 'title': info.get('title', 'Audio')}
            elif format_type == 'video_force_dl':
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                return {'status': 'success', 'type': 'file', 'filepath': filename, 'title': info.get('title', 'Video')}
            else:
                info = ydl.extract_info(url, download=False)
                direct_url = info.get('url')
                
                if direct_url:
                    return {'status': 'success', 'type': 'url', 'url': direct_url, 'title': info.get('title', 'Video')}
                else:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    return {'status': 'success', 'type': 'file', 'filepath': filename, 'title': info.get('title', 'Video')}
        except Exception as e:
            err_msg = str(e)
            if 'youtube' in url.lower() or 'youtu.be' in url.lower():
                pytube_url = get_pytubefix_url(url, format_type)
                if pytube_url:
                    return {'status': 'success', 'type': 'url', 'url': pytube_url, 'title': 'YouTube Video'}
            return {'status': 'error', 'message': err_msg}

def delete_file(filepath):
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except:
            pass
