#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
from pathlib import Path

SCHEMA="cybernetic-influence.simudyne-replacement-case.v1"

def main(argv=None):
    argv = argv or sys.argv[1:]
    if len(argv) != 1:
        print("usage: validate_case_spec.py case_spec.json", file=sys.stderr)
        return 2
    data=json.loads(Path(argv[0]).read_text())
    errors=[]
    if data.get("schema")!=SCHEMA:
        errors.append("wrong schema")
    participants=data.get("participants")
    if not isinstance(participants,list) or len(participants)!=12:
        errors.append("participants must contain exactly 12 entries")
    else:
        ids=[p.get("id") for p in participants if isinstance(p,dict)]
        if len(ids)!=12 or len(set(ids))!=12 or any(not isinstance(x,str) or not x for x in ids):
            errors.append("participant ids must be 12 unique nonempty strings")
    if data.get("rounds")!=3:
        errors.append("rounds must equal 3")
    rule=data.get("coalition_rule",{})
    if rule!={"minimum_support":6,"minimum_support_plus_conditional":9,"maximum_oppose":1}:
        errors.append("coalition rule differs from frozen trial rule")
    conditions=data.get("conditions")
    expected={"baseline","responsive_capacity_pressure","capacity_pressure_plus_stabilization"}
    if not isinstance(conditions,list) or {c.get("id") for c in conditions if isinstance(c,dict)}!=expected:
        errors.append("condition set differs from frozen trial")
    if data.get("required_repetitions_per_condition",0)<2:
        errors.append("at least two repetitions per condition are required")
    forbidden=set(data.get("replacement_negative_control",{}).get("forbidden_import_prefixes",[]))
    if not {
      "cybernetic_influence.active_runtime",
      "cybernetic_influence.causal_core",
      "cybernetic_influence.general_simulation",
      "cybernetic_influence.authoring",
    } <= forbidden:
        errors.append("negative-control import list is incomplete")
    if errors:
        for e in errors:
            print("ERROR:",e)
        return 1
    print("valid Simudyne replacement case:", argv[0])
    return 0

if __name__=="__main__":
    raise SystemExit(main())
