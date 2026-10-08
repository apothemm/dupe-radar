"""Read-only duplicate discovery using size buckets and streaming SHA-256."""
import argparse
import hashlib
import json
import os
from pathlib import Path

def scan(root: Path, exclude: Path | None = None):
    root = root.resolve(strict=True)
    if not root.is_dir(): raise ValueError('Root must be a directory')
    buckets, errors = {}, []
    def onerror(e): errors.append({'path': str(e.filename), 'error': str(e)})
    for directory, _, names in os.walk(root, followlinks=False, onerror=onerror):
        for name in names:
            path = Path(directory) / name
            if path.is_symlink() or (exclude and path.resolve() == exclude.resolve()): continue
            try:
                st = path.stat()
                if not path.is_file(): continue
                buckets.setdefault(st.st_size, []).append((path, st.st_mtime_ns))
            except OSError as e: errors.append({'path': str(path), 'error': str(e)})
    groups = []
    for size, files in buckets.items():
        if len(files) < 2: continue
        hashes = {}
        for path, stamp in files:
            try:
                h = hashlib.sha256()
                with path.open('rb') as f:
                    while chunk := f.read(1024 * 1024): h.update(chunk)
                after = path.stat()
                if (after.st_size, after.st_mtime_ns) != (size, stamp): raise OSError('File changed during scan')
                hashes.setdefault(h.hexdigest(), []).append(str(path.relative_to(root)))
            except OSError as e: errors.append({'path': str(path), 'error': str(e)})
        for digest, paths in hashes.items():
            if len(paths) > 1: groups.append({'sha256': digest, 'size': size, 'files': sorted(paths), 'reclaimable_bytes': size * (len(paths) - 1)})
    groups.sort(key=lambda g: (-g['reclaimable_bytes'], g['files']))
    return {'root': str(root), 'groups': groups, 'reclaimable_bytes': sum(g['reclaimable_bytes'] for g in groups), 'errors': errors}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path); parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        report = scan(args.root, args.output)
        data = json.dumps(report, ensure_ascii=False, indent=2)
        if args.output:
            tmp = args.output.with_name(args.output.name + '.tmp')
            with tmp.open('w', encoding='utf-8') as f: f.write(data); f.flush(); os.fsync(f.fileno())
            os.replace(tmp, args.output)
        else: print(data)
        return 2 if report['errors'] else 0
    except (OSError, ValueError) as e: parser.exit(1, f'{e}\n')
if __name__ == '__main__': raise SystemExit(main())
