import argparse,base64
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('json_file',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();v=base64.b64encode(a.json_file.read_bytes()).decode('ascii')
if a.output:a.output.write_text(v,encoding='ascii');print(a.output)
else:print(v)
