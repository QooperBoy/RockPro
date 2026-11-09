from pathlib import Path
p=Path('Integracja/rockpro_cad/addin/LayoutForm.cs');s=p.read_text(encoding='utf-8');s=s.replace('layoutRevision=Convert.ToInt64(r["revision"]);','layoutRevision=Convert.ToInt64(r["revision"]);Text="RockPro CAD | Układ urządzeń — wersja "+layoutRevision;');p.write_text(s,encoding='utf-8')
