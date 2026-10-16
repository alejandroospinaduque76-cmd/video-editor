#!/usr/bin/env python3
"""Promote an explicitly approved MP4 without deleting drafts or overwriting finals."""
import argparse,importlib.util,shutil,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('verify_export',Path(__file__).with_name('verify-export.py'))
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('job');p.add_argument('--source',help='Exact filename inside the job outputs folder');p.add_argument('--apply',action='store_true');p.add_argument('--approved',action='store_true',help='Use only after the creator approved this exact draft')
    # 2026.09.28 package flags: --keep-drafts is what this finalize always does (it never deletes a draft), so it is
    # accepted and changes nothing; --variant NAME finalizes a second deliverable living in outputs/NAME/ (an ad cut,
    # the 4K Shorts file) as outputs/NAME/<job>.NAME.final.mp4, with the same rules.
    p.add_argument('--keep-drafts',action='store_true',help='Sin efecto: este finalize nunca borra borradores.')
    p.add_argument('--variant',help='Segundo entregable en outputs/<variant>/ (p. ej. ad, shorts)')
    a=p.parse_args();root=Path(__file__).resolve().parents[1]
    if a.job in ('.','..') or not a.job or any(c in a.job for c in '/\\\0'): p.error('Nombre de proyecto inválido.')
    projects=(root/'projects').resolve();out=root/'projects'/a.job/'outputs'
    if a.variant is not None and (not a.variant or a.variant in ('.','..') or any(c in a.variant for c in '/\\\0')): p.error('--variant debe ser un nombre simple, p. ej. ad o shorts.')
    if a.variant: out=out/a.variant
    if not out.is_dir() or not out.resolve().is_relative_to(projects):
        p.error(('No existe outputs/'+a.variant+'/: el segundo entregable vive ahí (p. ej. outputs/ad/<job>.ad.mp4); créala y pon el archivo aprobado dentro.') if a.variant else 'No existe outputs o está fuera de projects.')
    target=out/(a.job+('.'+a.variant if a.variant else '')+'.final.mp4')
    if not a.source:
        if not target.is_file(): p.error('Selecciona el borrador aprobado: --source nombre.mp4. No se elige por fecha.')
        source=target
    else:
        # a path is accepted when it points INSIDE this job's outputs folder (CLAUDE.md shows <approved-file.mp4>, and an
        # agent passes outputs/<job>.draft-v1.mp4 as often as the bare name: 6c, the owner's VSL, 2026-09-29)
        cand=Path(a.source)
        if cand.name!=a.source or '\\' in a.source:
            # the file NAMED is the one finalized: a path outside outputs/ is refused even when outputs/ holds a file with
            # the same name (6c D5: /elsewhere/<name>.mp4 passed, and the outputs/ twin was the file verified)
            hits=[q for q in (cand, root/cand, root/'projects'/a.job/cand) if q.is_file()]
            if not hits or hits[0].resolve().parent!=out.resolve(): p.error('--source debe ser un archivo dentro de projects/'+a.job+'/outputs'+('/'+a.variant if a.variant else '')+' (el nombre basta).')
            source=out/hits[0].name
        else:
            source=out/a.source
    if source.is_symlink() or target.is_symlink() or source.suffix.lower()!='.mp4' or not source.resolve().is_relative_to(out.resolve()): p.error('Se requiere un MP4 local dentro de outputs, sin enlaces simbólicos.')
    if target.exists() and source!=target: p.error('Ya existe un final. Se conserva intacto; usa un proyecto/versionado nuevo.')
    print(v.verify(source))
    if not a.apply:
        print('SIMULACIÓN: se verificó el video. No se cambió ningún archivo.');return
    if not a.approved: p.error('Falta --approved. Primero revisa y aprueba este borrador con el creador.')
    if source!=target:
        # Exclusive creation prevents a concurrent job from replacing an existing final.
        with source.open('rb') as src,target.open('xb') as dst: shutil.copyfileobj(src,dst)
        v.verify(target)
    print('Final verificado: '+str(target))
    print('Originales, borradores y proyectos conservados. No se copia ni sobrescribe nada en Descargas.')

if __name__=='__main__':
    try: main()
    except (ValueError,OSError,TimeoutError) as e: print('ERROR: '+str(e),file=sys.stderr);sys.exit(1)
