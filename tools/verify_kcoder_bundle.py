#!/usr/bin/env python3
"""Validate this repository's portable KCoder bundle; no third-party packages.

This is a file/format/packaging verifier, NOT the KCoder parser or a runtime test.
Run from any cwd: python tools/verify_kcoder_bundle.py --self-test
Maintainers: --write-manifest after intended template edits, then verify again.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

REPO = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = REPO / 'templates' / 'kcoder-match'
SKILLS = ('cp29-debug', 'cp29-innovation', 'cp29-delivery')
FILES = tuple(sorted((
    'AGENTS.md', 'README-现场配置.md', 'SKILLS-现场安装.md', 'INSTALL.ps1',
    'THIRD_PARTY_NOTICES.md', 'docs/PROJECT.md', 'docs/TASKS.md', 'docs/EVIDENCE.md',
    *(f'.kcoder/skills/{name}/SKILL.md' for name in SKILLS),
)))

def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def validate_structure(root: Path) -> None:
    require(root.is_dir(), 'Bundle directory is missing')
    paths = list(root.rglob('*'))
    require(not any(p.is_symlink() for p in paths), 'Symlinks are not allowed')
    actual = {p.relative_to(root).as_posix() for p in paths if p.is_file()}
    require(actual - {'MANIFEST.json'} == set(FILES),
            'Unexpected or missing bundle files: ' + repr(sorted(actual ^ (set(FILES) | ({'MANIFEST.json'} if 'MANIFEST.json' in actual else set())))))
    for relative in FILES:
        raw = (root / relative).read_bytes()
        text = raw.decode('utf-8', errors='strict')
        require(not text.startswith('\ufeff'), 'Unexpected BOM: ' + relative)
        require(0 < len(raw) < 64_000, 'Invalid file size: ' + relative)
    require((root / 'AGENTS.md').stat().st_size < 8_000, 'AGENTS exceeds team size target')
    require('Central Park 参赛项目工作指令' in (root / 'AGENTS.md').read_text(encoding='utf-8'), 'Missing project scope marker')
    # ASCII-only avoids PowerShell 5.1's UTF-8-without-BOM script decoding ambiguity.
    (root / 'INSTALL.ps1').read_bytes().decode('ascii')
    for name in SKILLS:
        text = (root / '.kcoder' / 'skills' / name / 'SKILL.md').read_text(encoding='utf-8')
        match = re.fullmatch(r'---\nname: ([a-z0-9][a-z0-9._-]{0,63})\ndescription: ("[^\n]+")\n---\n\n(.+)', text, re.S)
        require(match is not None, 'Invalid restricted frontmatter: ' + name)
        require(match.group(1) == name, 'Skill name/path mismatch: ' + name)
        description = json.loads(match.group(2))
        require(description.startswith('Use when '), 'Missing trigger prefix: ' + name)
        require(len(description) < 350, 'Trigger description too long: ' + name)
        for section in ('适用边界', '方法', '常见误区', '验收与交接', '触发测试'):
            require(section in match.group(3), 'Missing skill section: ' + name + '/' + section)
    # Actual Markdown links within portable instructions must resolve inside the package.
    for p in root.rglob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)', p.read_text(encoding='utf-8')):
            if '://' not in target and not target.startswith('#'):
                require((p.parent / target.split('#')[0]).exists(), 'Broken link: ' + target)

def write_manifest(root: Path) -> None:
    validate_structure(root)
    data = {'schemaVersion': 1, 'purpose': 'File integrity only; not a publisher signature or runtime certification.',
            'files': [{'path': p, 'sha256': sha(root / p)} for p in FILES]}
    (root / 'MANIFEST.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def verify(root: Path) -> None:
    validate_structure(root)
    data = json.loads((root / 'MANIFEST.json').read_text(encoding='utf-8'))
    require(data.get('schemaVersion') == 1, 'Invalid manifest version')
    records = data.get('files', [])
    names = [item['path'] for item in records]
    require(len(names) == len(set(names)), 'Duplicate manifest entries')
    require(set(names) == set(FILES), 'Manifest file set mismatch')
    for item in records:
        require(re.fullmatch(r'[0-9a-f]{64}', item['sha256']) is not None, 'Invalid digest')
        require(sha(root / item['path']) == item['sha256'], 'Hash mismatch: ' + item['path'])

def self_test(root: Path) -> int:
    verify(root)
    tests = 0
    for case in ('hash', 'missing', 'invalid_utf8', 'name', 'description', 'extra', 'symlink', 'duplicate_manifest'):
        with tempfile.TemporaryDirectory(prefix='cp29-verify-') as temporary:
            copy = Path(temporary) / 'bundle'
            shutil.copytree(root, copy)
            if case == 'hash':
                p = copy / 'docs/TASKS.md'; p.write_bytes(p.read_bytes() + b'\nmodified\n')
            elif case == 'missing':
                (copy / '.kcoder/skills/cp29-debug/SKILL.md').unlink()
            elif case == 'invalid_utf8':
                (copy / 'docs/TASKS.md').write_bytes(b'\xff')
            elif case in ('name', 'description'):
                p = copy / '.kcoder/skills/cp29-debug/SKILL.md'
                text = p.read_text(encoding='utf-8')
                text = text.replace('name: cp29-debug', 'name: Wrong Name') if case == 'name' else text.replace('description: "Use when ', 'description: "Always ')
                p.write_text(text, encoding='utf-8')
            elif case == 'extra':
                (copy / 'unexpected.exe').write_bytes(b'not-an-installer')
            elif case == 'symlink':
                try:
                    (copy / 'linked.md').symlink_to(copy / 'AGENTS.md')
                except OSError:
                    print('SKIP: symlink creation is not permitted by this OS/account')
                    continue
            elif case == 'duplicate_manifest':
                p = copy / 'MANIFEST.json'; data = json.loads(p.read_text(encoding='utf-8'))
                data['files'].append(data['files'][0]); p.write_text(json.dumps(data), encoding='utf-8')
            try:
                verify(copy)
            except (ValueError, OSError, KeyError):
                print('PASS: rejected ' + case)
                tests += 1
            else:
                raise ValueError('Negative test unexpectedly accepted: ' + case)
    return tests

def export_zip(root: Path, target: Path) -> None:
    verify(root)
    require(not target.is_relative_to(root), 'Keep generated ZIP outside the template directory')
    target.parent.mkdir(parents=True, exist_ok=True)
    names = (*FILES, 'MANIFEST.json')
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in sorted(names):
            info = zipfile.ZipInfo('kcoder-match/' + relative, (2026, 11, 19, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (root / relative).read_bytes())
    with zipfile.ZipFile(target) as archive:
        require(archive.testzip() is None, 'ZIP integrity failed')
        require(len(archive.namelist()) == len(names), 'ZIP entry count mismatch')
        for relative in names:
            require(archive.read('kcoder-match/' + relative) == (root / relative).read_bytes(), 'ZIP byte mismatch')
    print('ZIP:', target)
    print('ZIP SHA256:', sha(target))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--write-manifest', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--zip-output', type=Path)
    args = parser.parse_args()
    if args.write_manifest:
        write_manifest(args.root)
    verify(args.root)
    print(f'PASS: {len(FILES)} files + manifest; UTF-8, restricted Skill format, scope, links and hashes checked')
    if args.self_test:
        print(f'PASS: {self_test(args.root)} negative tests')
    if args.zip_output:
        export_zip(args.root.resolve(), args.zip_output.resolve())
    print('NOT TESTED: PowerShell execution; KCoder native parsing/loading/activation; Windows/Android runtime')
