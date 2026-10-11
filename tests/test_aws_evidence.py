import json

import pytest

from tokenforge.aws_evidence import prepare_package, upload_package, report_link


class Client:
    def __init__(self):
        self.puts = []

    def put_object(self, **kwargs):
        self.puts.append(kwargs)

    def generate_presigned_url(self, operation, **kwargs):
        assert operation == 'get_object'
        assert kwargs['ExpiresIn'] == 3600
        return 'temporary-url'


def test_package_is_stable_and_upload_is_scoped(tmp_path):
    directory, manifest = prepare_package(tmp_path, 'r-20261011-170439')
    again, other = prepare_package(tmp_path, 'r-20261011-170439')
    assert (directory, manifest) == (again, other)
    bundle = json.loads((directory / 'bundle.json').read_text())
    assert len(bundle['candidates']) == 48
    client = Client()
    key = upload_package(client, directory, manifest, 'test-bucket')
    assert [p['Key'].rsplit('/', 1)[1] for p in client.puts] == ['bundle.json', 'report.html', 'manifest.json']
    assert all(p['IfNoneMatch'] == '*' and 'ACL' not in p for p in client.puts)
    assert all(p['Key'].startswith('tokenforge/evidence/r-20261011-170439/') for p in client.puts)
    assert report_link(client, 'test-bucket', key) == 'temporary-url'


def test_tampering_prevents_any_cloud_write(tmp_path):
    directory, manifest = prepare_package(tmp_path)
    (directory / 'report.html').write_text('changed')
    client = Client()
    with pytest.raises(ValueError, match='changed after packaging'):
        upload_package(client, directory, manifest, 'test-bucket')
    assert client.puts == []


def test_partial_upload_never_writes_completion_marker(tmp_path):
    directory, manifest = prepare_package(tmp_path)

    class Failing(Client):
        def put_object(self, **kwargs):
            if kwargs['Key'].endswith('/report.html'):
                raise RuntimeError('upload failed')
            super().put_object(**kwargs)

    client = Failing()
    with pytest.raises(RuntimeError, match='upload failed'):
        upload_package(client, directory, manifest, 'test-bucket')
    assert len(client.puts) == 1


def test_expiry_is_bounded():
    with pytest.raises(ValueError, match='expiry'):
        report_link(Client(), 'test-bucket', 'report.html', 604801)


def test_existing_matching_objects_allow_idempotent_upload(tmp_path):
    directory, manifest = prepare_package(tmp_path)

    class ExistsError(Exception):
        response = {'Error': {'Code': 'PreconditionFailed'}}

    class Existing(Client):
        def put_object(self, **kwargs):
            self.current = kwargs
            raise ExistsError()

        def head_object(self, **kwargs):
            return {'Metadata': self.current['Metadata'], 'ContentLength': len(self.current['Body'])}

    assert upload_package(Existing(), directory, manifest, 'test-bucket').endswith('/report.html')


def test_modified_manifest_prevents_cloud_write(tmp_path):
    directory, manifest = prepare_package(tmp_path)
    manifest['kernel_sha256'] = 'changed'
    client = Client()
    with pytest.raises(ValueError, match='Manifest package hash'):
        upload_package(client, directory, manifest, 'test-bucket')
    assert client.puts == []
