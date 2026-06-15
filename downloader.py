import os
import yt_dlp
import imageio_ffmpeg

def get_dl_opts(user_id, quality='best', format_type='video'):
    outtmpl = f'downloads/{user_id}_%(id)s.%(ext)s'
    os.makedirs('downloads', exist_ok=True)
    
    opts = {
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': imageio_ffmpeg.get_ffmpeg_exe(),
        'extractor_args': {'youtube': ['player_client=android']},
    }
    
    if format_type == 'audio':
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    else:
        # Video
        if quality == 'worst':
            opts['format'] = 'worst'
        else:
            # Use 'best' to prevent video/audio splitting, which guarantees a single direct URL
            opts['format'] = 'best'
            
    return opts

def download_media(url, user_id, quality='best', format_type='video'):
    opts = get_dl_opts(user_id, quality, format_type)
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            if format_type == 'audio':
                # MP3 conversion requires ffmpeg, so we must download
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                filename = os.path.splitext(filename)[0] + '.mp3'
                return {'status': 'success', 'type': 'file', 'filepath': filename, 'title': info.get('title', 'Audio')}
            elif format_type == 'video_force_dl':
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                return {'status': 'success', 'type': 'file', 'filepath': filename, 'title': info.get('title', 'Video')}
            else:
                # For video, extract info first without downloading
                info = ydl.extract_info(url, download=False)
                direct_url = info.get('url')
                
                if direct_url:
                    # Return direct URL for instant sending
                    return {'status': 'success', 'type': 'url', 'url': direct_url, 'title': info.get('title', 'Video')}
                else:
                    # Fallback to download if direct URL is not available
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    return {'status': 'success', 'type': 'file', 'filepath': filename, 'title': info.get('title', 'Video')}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

def delete_file(filepath):
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except:
            pass
