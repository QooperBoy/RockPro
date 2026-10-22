"""Whole-latch A/B showcase, API-only. Never starts IronCAD or activates windows.

--compile-only checks the hidden panel helper without CAD. --native requires an
exact existing ROT context before creating files. The original is read through
a byte-identical read-only hidden copy. Output is a regular ten-panel case with
eight existing corners and four opaque latch halves, not the complete Epson.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'Integracja'))
from rockpro_cad.core_case.latch_native import build_panel_bridge, execute_latch_showcase


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--compile-only', action='store_true')
    mode.add_argument('--native', action='store_true')
    parser.add_argument('--context', type=Path, help='Exact saved ICS already open in ROT')
    parser.add_argument('--source', type=Path)
    parser.add_argument('--corner-receipt', type=Path)
    parser.add_argument('--corner-assets', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to((ROOT/'artifacts').resolve()):
        parser.error('Output must be a NEW directory inside checkout artifacts/')
    if args.compile_only:
        print('COMPILE PASS '+str(build_panel_bridge(output)))
        return
    for name in ('context', 'source', 'corner_receipt', 'corner_assets'):
        if getattr(args, name) is None:
            parser.error('--'+name.replace('_', '-')+' is required with --native')
    receipt = json.loads(args.corner_receipt.read_text(encoding='utf-8'))
    assets = json.loads(args.corner_assets.read_text(encoding='utf-8'))
    result = execute_latch_showcase(context=args.context, source=args.source,
        corner_receipt=receipt, corner_assets=assets, output=output)
    print('NATIVE A/B PASS; own documents closed')
    for case in result['cases']:
        print(case['output_path'])


if __name__ == '__main__':
    main()
