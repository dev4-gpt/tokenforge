"""Content-addressed evidence packages; AWS is optional and never part of timing."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from .reporting import ROOT, load_bundle, render_report


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, default=str) + '\n').encode()


def prepare_package(output: Path, run_id=None, root=ROOT):
    bundle = load_bundle(run_id, root)
    files = {'bundle.json': encoded(bundle), 'report.html': render_report(bundle, root).encode()}
    manifest = {
        'version': 1, 'run_id': bundle['run_id'],
        'kernel_sha256': bundle['kernel_sha256'],
        'files': [{'name': name, 'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)}
                  for name, body in sorted(files.items())],
        'scope': 'Validated recorded evidence. No new cloud benchmark or AWS deployment claim.',
    }
    manifest['package_id'] = hashlib.sha256(encoded(manifest)).hexdigest()
    directory = Path(output) / bundle['run_id'] / manifest['package_id']
    directory.mkdir(parents=True, exist_ok=True)
    for name, body in files.items():
        (directory / name).write_bytes(body)
    (directory / 'manifest.json').write_bytes(encoded(manifest))
    return directory, manifest


def upload_package(client, directory, manifest, bucket, prefix='tokenforge/evidence'):
    if not bucket or not re.fullmatch(r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*', prefix):
        raise ValueError('Bucket and a relative evidence prefix are required')
    unsigned = {k: v for k, v in manifest.items() if k != 'package_id'}
    if hashlib.sha256(encoded(unsigned)).hexdigest() != manifest['package_id']:
        raise ValueError('Manifest package hash mismatch')
    if not re.fullmatch(r'r-[\w-]+', manifest['run_id']):
        raise ValueError('Invalid run ID')
    # Check every byte before writing any object. Only these two public evidence files are allowed.
    if {item['name'] for item in manifest['files']} != {'bundle.json', 'report.html'}:
        raise ValueError('Unexpected evidence files')
    objects = []
    for item in manifest['files']:
        body = (Path(directory) / item['name']).read_bytes()
        if len(body) != item['bytes'] or hashlib.sha256(body).hexdigest() != item['sha256']:
            raise ValueError('Evidence changed after packaging')
        objects.append((item['name'], body))
    # Manifest is the completion marker, written only after all evidence objects succeed.
    objects.append(('manifest.json', encoded(manifest)))
    key_prefix = f"{prefix}/{manifest['run_id']}/{manifest['package_id']}"
    for name, body in objects:
        digest = hashlib.sha256(body).hexdigest()
        key = f'{key_prefix}/{name}'
        try:
            client.put_object(Bucket=bucket, Key=key, Body=body,
                              ContentType='text/html; charset=utf-8' if name.endswith('.html') else 'application/json',
                              Metadata={'sha256': digest}, IfNoneMatch='*')
        except Exception as exc:
            if getattr(exc, 'response', {}).get('Error', {}).get('Code') != 'PreconditionFailed':
                raise
            existing = client.head_object(Bucket=bucket, Key=key)
            if existing.get('Metadata', {}).get('sha256') != digest or existing.get('ContentLength') != len(body):
                raise ValueError('Existing S3 object does not match this package') from exc
    return f'{key_prefix}/report.html'


def report_link(client, bucket, key, expires=3600):
    if not 60 <= expires <= 604800:
        raise ValueError('Link expiry must be between 60 seconds and seven days')
    return client.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': key}, ExpiresIn=expires)
