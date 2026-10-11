"""Build standalone HTML from validated, locally exported evidence."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tokenforge.reporting import export_candidates, load_bundle, render_report

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', help='Recorded run ID (default: latest)')
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument('--offline', action='store_true', help='Local exports only (default)')
    mode.add_argument('--refresh-atlas', action='store_true', help='Explicitly refresh the export')
    args = ap.parse_args()
    if args.refresh_atlas:
        from dotenv import load_dotenv
        load_dotenv(ROOT / '.env')
        run_id = args.run or sorted((ROOT / 'results').glob('r-*.json'))[-1].stem
        export_candidates(run_id)
    bundle = load_bundle(args.run)
    html = render_report(bundle)
    out = ROOT / 'docs'
    out.mkdir(exist_ok=True)
    (out / 'index.html').write_text(html)
    (out / 'report_body.html').write_text(html[html.index('<title>'):html.rfind('</html>')])
    print(f"Built {bundle['run_id']}: {len(bundle['candidates'])} candidates, offline replay")

if __name__ == '__main__':
    main()
