"""Fresh saved-export flange and pair proof. Default validates inputs only."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Integracja'))
from rockpro_cad.core_case.mount_capture import validate_export,capture_mount_pair
from rockpro_cad.parts.native import file_sha256

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('asset','export-receipt','source-binding','output-dir'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--expected-asset-sha256',required=True)
    p.add_argument('--native',action='store_true')
    args=p.parse_args(argv)
    receipt=json.loads(args.export_receipt.read_text(encoding='utf-8'))
    binding=json.loads(args.source_binding.read_text(encoding='utf-8'))
    validate_export(receipt,binding,args.expected_asset_sha256)
    if file_sha256(args.asset)!=args.expected_asset_sha256:raise ValueError('Asset hash mismatch')
    output=args.output_dir.resolve()
    if output.exists() or not output.is_relative_to((ROOT/'artifacts').resolve()):
        raise ValueError('Output must be a new directory under checkout artifacts')
    if not args.native:
        print('INPUT_VALIDATION PASS; native execution NOT RUN');return 0
    result=capture_mount_pair(args.asset,receipt,binding,
        expected_asset_sha256=args.expected_asset_sha256,output_dir=output)
    print(json.dumps(dict(passed=result['passed'],output=str(output),scope=result['scope'])))
    return 0

if __name__=='__main__':raise SystemExit(main())
