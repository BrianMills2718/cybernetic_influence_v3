import json
import tempfile
from pathlib import Path
import importlib.util

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("validator",HERE/"validate_case_spec.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

case=json.loads((HERE/"case_spec.json").read_text())
with tempfile.TemporaryDirectory() as td:
    p=Path(td)/"case.json"
    p.write_text(json.dumps(case))
    assert m.main([str(p)])==0
    bad=json.loads(json.dumps(case))
    bad["rounds"]=4
    p.write_text(json.dumps(bad))
    assert m.main([str(p)])==1
print("test_validate_case_spec: ok")
