import os
import yt_dlp
import imageio_ffmpeg

import requests

def get_cobalt_url(url, format_type='video'):
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    data = {
        "url": url,
        "isAudioOnly": format_type == 'audio'
    }
    
    # Ro'yxatdagi turli xil bepul Cobalt serverlaridan birma-bir urinib ko'ramiz
    instances = [
        'https://co.wuk.sh/api/json',
        'https://cobalt.kwiatekmateusz.pl/api/json',
        'https://cobalt.qewertyy.dev/api/json',
        'https://api.cobalt.tools/api/json'
    ]
    
    for ep in instances:
        try:
            r = requests.post(ep, headers=headers, json=data, timeout=10)
            if r.status_code == 200:
                res = r.json()
                if 'url' in res:
                    return res['url']
        except:
            continue
            
    return None

def get_dl_opts(user_id, url, quality='best', format_type='video'):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    outtmpl = os.path.join(base_dir, f'downloads/{user_id}_%(id)s.%(ext)s')
    os.makedirs(os.path.join(base_dir, 'downloads'), exist_ok=True)
    
    opts = {
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': imageio_ffmpeg.get_ffmpeg_exe(),
    }
    
    if 'youtube' in url.lower() or 'youtu.be' in url.lower():
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
            opts['format'] = 'worstvideo+worstaudio/worst'
        elif quality == 'medium':
            opts['format'] = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best'
        else:
            opts['format'] = 'bestvideo+bestaudio/best'
            
    return opts

def download_media(url, user_id, quality='best', format_type='video'):
    opts = get_dl_opts(user_id, url, quality, format_type)
    
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
                cobalt_url = get_cobalt_url(url, format_type)
                if cobalt_url:
                    return {'status': 'success', 'type': 'url', 'url': cobalt_url, 'title': 'YouTube Video'}
                else:
                    return {'status': 'error', 'message': "Yangi kod ishladi: Cobalt API serveri ham, YouTube ham videoni Renderga berishni rad etdi. Bot to'liq blokda."}
            return {'status': 'error', 'message': err_msg}

def delete_file(filepath):
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except:
            pass
