#!/usr/bin/env python3
"""Read-only MP4 verification. Does not certify editorial quality or caption accuracy."""
import argparse,json,math,shutil,subprocess,sys
from pathlib import Path

def verify(path, expected_duration=None, width=None, height=None, require_audio=False):
    path=Path(path)
    if not path.is_file(): raise ValueError('No existe el archivo indicado.')
    for tool in ('ffprobe','ffmpeg'):
        if not shutil.which(tool): raise ValueError('Falta '+tool+'. Ejecuta check-setup.sh.')
    probe=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],capture_output=True,text=True,timeout=30)
    if probe.returncode: raise ValueError('FFprobe no puede leer este archivo de video.')
    info=json.loads(probe.stdout); streams=info.get('streams',[])
    video=next((s for s in streams if s.get('codec_type')=='video'),None)
    audio=next((s for s in streams if s.get('codec_type')=='audio'),None)
    if not video: raise ValueError('El archivo no contiene video.')
    duration=float(info.get('format',{}).get('duration',0))
    if not math.isfinite(duration) or duration<=0: raise ValueError('Duración inválida.')
    if expected_duration is not None and abs(duration-expected_duration)>max(.15,expected_duration*.01): raise ValueError('La duración difiere del plan aprobado.')
    if width is not None and video.get('width')!=width: raise ValueError('El ancho no coincide con la entrega solicitada.')
    if height is not None and video.get('height')!=height: raise ValueError('El alto no coincide con la entrega solicitada.')
    if require_audio and not audio: raise ValueError('Falta el audio requerido.')
    # Decode every video/audio frame, not just the container header.
    decoded=subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror','-i',str(path),'-map','0:v:0','-map','0:a?','-f','null','-'],capture_output=True,text=True,timeout=max(120,min(1800,duration*5)))
    if decoded.returncode: raise ValueError('La decodificación completa detectó un error.')
    return {'status':'passed','duration_seconds':round(duration,3),'width':video['width'],'height':video['height'],'video_codec':video.get('codec_name'),'audio_present':bool(audio),'full_decode':'passed','human_review':'required: meaning, cuts, captions, framing and audio sync'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('file');p.add_argument('--duration',type=float);p.add_argument('--width',type=int);p.add_argument('--height',type=int);p.add_argument('--require-audio',action='store_true');a=p.parse_args()
    try:
        if any(x is not None and (not math.isfinite(x) or x<=0) for x in (a.duration,a.width,a.height)): raise ValueError('Las dimensiones y la duración deben ser positivas.')
        result=verify(a.file,a.duration,a.width,a.height,a.require_audio)
    except (ValueError,OSError,subprocess.SubprocessError) as e:
        print(json.dumps({'status':'failed','message':str(e)},ensure_ascii=False));sys.exit(1)
    print(json.dumps(result,ensure_ascii=False,indent=2))
