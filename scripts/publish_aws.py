"""Prepare locally by default; upload only to an explicitly supplied existing S3 bucket."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tokenforge.aws_evidence import prepare_package, upload_package, report_link


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run')
    parser.add_argument('--output', type=Path, default=ROOT / 'aws-export')
    parser.add_argument('--upload', action='store_true')
    parser.add_argument('--bucket')
    parser.add_argument('--region')
    parser.add_argument('--profile')
    parser.add_argument('--prefix', default='tokenforge/evidence')
    parser.add_argument('--share-link', action='store_true', help='Print a temporary report URL after uploading')
    parser.add_argument('--expires', type=int, default=3600)
    args = parser.parse_args()
    if args.upload and (not args.bucket or not args.region):
        parser.error('--upload requires an existing --bucket and --region')
    if args.share_link and not args.upload:
        parser.error('--share-link requires --upload')
    if not 60 <= args.expires <= 604800:
        parser.error('--expires must be between 60 and 604800 seconds')
    directory, manifest = prepare_package(args.output, args.run)
    print(f'Prepared validated evidence: {directory}')
    if not args.upload:
        print('Local preparation only. Nothing sent to AWS.')
        return
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        parser.error('AWS uploads require the optional boto3 package: python -m pip install boto3')
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    client = session.client('s3', config=Config(signature_version='s3v4', connect_timeout=5,
                                             read_timeout=30, retries={'max_attempts': 2}))
    key = upload_package(client, directory, manifest, args.bucket, args.prefix)
    print(f'Uploaded and finalized evidence: s3://{args.bucket}/{key}')
    if args.share_link:
        print(report_link(client, args.bucket, key, args.expires))


if __name__ == '__main__':
    main()
