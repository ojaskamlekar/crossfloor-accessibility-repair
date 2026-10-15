import json
import sys

import pytest

from cfar.review_generators import diagnostic_example


@pytest.mark.parametrize("command,flags",[("solve-cp-sat",[]),("solve-greedy",[]),("solve-greedy",["--improve"]),("solve-reuse-lifetime",[])])
def test_solver_command_returns_once_and_does_not_fall_through_to_oracle(tmp_path,monkeypatch,capsys,command,flags):
    if command=="solve-cp-sat":pytest.importorskip("ortools")
    from cfar import cli
    source=tmp_path/"input.json";source.write_text(json.dumps(diagnostic_example()))
    output=tmp_path/"out"
    def forbidden(*args,**kwargs):raise AssertionError("non-oracle CLI command fell through")
    monkeypatch.setattr(cli,"exact_oracle",forbidden)
    monkeypatch.setattr(sys,"argv",["cfar",command,str(source),*flags,"--output",str(output)])
    cli.main()
    printed=capsys.readouterr().out.strip().splitlines()
    assert len(printed)==1
    result=json.loads((output/"result.json").read_text())
    manifest=json.loads((output/"manifest.json").read_text())
    assert manifest["solver_status"]==result["status"]
    if command=="solve-greedy"and not flags:
        # This hand-derived feasible case is a legitimate construction dead end.
        assert result["status"]=="heuristic_failed"
    else:
        assert result["status"]in{"optimal","feasible"}
