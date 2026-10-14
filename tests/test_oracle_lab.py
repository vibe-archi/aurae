"""Exercise the shipped Markdown starter in disposable, ignored fixtures only."""
import copy
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills/aurae/assets/oracle-lab/starter.md"
SCRATCH = ROOT / ".scratchpad/oracle-lab-tests"
SCRIPT_ID = "ORACLE-example-csv-rows-a19d40"
MANUAL_ID = "ORACLE-example-signout-b70e32"


class OracleLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        markdown = SOURCE.read_text(encoding="utf-8")
        cls.files = dict(re.findall(
            r"<!-- oracle-lab-file: ([^\n]+) -->\n```[^\n]+\n(.*?)\n```",
            markdown, re.S))
        if len(cls.files) != 8:
            raise AssertionError("Expected all eight marked starter files.")
        SCRATCH.mkdir(parents=True, exist_ok=True)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="run-", dir=SCRATCH)
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name).resolve()
        self.catalog = self.project / "oracle-tests"
        for relative, content in self.files.items():
            path = self.catalog / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        source = self.catalog / "harnesses/lab/server.py"
        self.module = {"__name__": "oracle_lab_test", "__file__": str(source)}
        exec(compile(source.read_text(encoding="utf-8"), str(source), "exec"), self.module)
        self.scenario = self.catalog / "scenarios/examples/csv"
        self.expected = json.loads((self.scenario / "expected.json").read_text(encoding="utf-8"))

    def run_lines(self, lines, exit_code=0):
        code = "import sys\n" + "\n".join(f"print({line!r}, flush=True)" for line in lines)
        code += f"\nsys.exit({exit_code})\n"
        (self.scenario / "run.py").write_text(code, encoding="utf-8")
        context = {"path": str(self.project), "git": False, "branch": None, "commit": None, "dirty": None}
        # Protocol tests need a real subprocess, not repeated Git probes of the host repository.
        with patch.dict(self.module, {"project_info": lambda _: copy.deepcopy(context)}):
            demo = self.module["Demo"](self.project)
            self.assertEqual(demo.results, {})
            demo.start([SCRIPT_ID])
            deadline = time.monotonic() + 12
            while demo.snapshot()["job"]["status"] == "running" and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertNotEqual(demo.snapshot()["job"]["status"], "running")
        return demo.results[SCRIPT_ID], demo

    def result_line(self, actual=None):
        return json.dumps({"type": "result", "actual": self.expected if actual is None else actual})

    def test_healthy_pass_mismatch_and_blocked_remain_distinct(self):
        cases = [
            ([json.dumps({"type": "log", "message": "Working"}), self.result_line()], "pass"),
            ([self.result_line({"wrong": True})], "fail"),
            ([json.dumps({"type": "blocked", "message": "Fixture unavailable"})], "blocked"),
        ]
        for lines, expected_status in cases:
            with self.subTest(expected_status=expected_status):
                result, demo = self.run_lines(lines)
                self.assertEqual(result["status"], expected_status)
                self.assertEqual(result["output"], lines)
                self.assertEqual(result["exit_code"], 0)
                self.assertIn("finished_at", result)
                report = json.loads((demo.output / "report.json").read_text(encoding="utf-8"))
                self.assertNotIn("token", report)
                self.assertEqual(report["results"][SCRIPT_ID]["status"], expected_status)

    def test_malformed_events_cannot_retain_a_prior_pass(self):
        bad_events = [
            '{"type":"result","actual":',
            '{"type":"result","actual":true,"actual":false}',
            '{"type":"result","actual":NaN}',
            '{"type":"blocked",',
            '{"type":"log","message":',
            'unstructured diagnostic text',
            '["not", "an event"]',
            '{"type":"unknown","message":"ignored?"}',
            '{"type":"log","message":42}',
            '{"type":"blocked","message":""}',
        ]
        for bad in bad_events:
            for lines in ([self.result_line(), bad], [bad, self.result_line()]):
                with self.subTest(bad=bad, bad_first=lines[0] == bad):
                    result, _ = self.run_lines(lines)
                    self.assertEqual(result["status"], "error")
                    self.assertIn(bad, result["output"])
                    self.assertNotIn("actual", result)
                    self.assertTrue(result["message"])

    def test_duplicate_or_mixed_terminal_events_are_errors(self):
        blocked = json.dumps({"type": "blocked", "message": "Missing prerequisite"})
        invalid = json.dumps({"type": "result"})
        cases = [
            [self.result_line(), self.result_line()],
            [self.result_line(), self.result_line({"wrong": True})],
            [self.result_line(), blocked], [blocked, self.result_line()],
            [blocked, blocked], [invalid],
        ]
        for lines in cases:
            with self.subTest(lines=lines):
                result, _ = self.run_lines(lines)
                self.assertEqual(result["status"], "error")
                self.assertNotIn("actual", result)

    def test_no_result_and_nonzero_exit_never_pass(self):
        for lines, exit_code in [([], 0), ([self.result_line()], 4),
                                 ([json.dumps({"type": "blocked", "message": "Missing"})], 4)]:
            with self.subTest(lines=lines, exit_code=exit_code):
                result, _ = self.run_lines(lines, exit_code)
                self.assertEqual(result["status"], "error")
                self.assertEqual(result["exit_code"], exit_code)
                self.assertNotIn("actual", result)

    def test_each_execution_and_manual_feedback_capture_current_context(self):
        initial = {"path": str(self.project), "git": True, "branch": "old", "commit": "a" * 40, "dirty": False}
        latest = dict(initial, branch="current", commit="b" * 40)
        with patch.dict(self.module, {"project_info": lambda _: copy.deepcopy(initial)}):
            demo = self.module["Demo"](self.project)
        demo.results[SCRIPT_ID] = {"status": "queued", "logs": [], "output": []}
        with patch.dict(self.module, {"project_info": lambda _: copy.deepcopy(latest)}):
            demo.execute(SCRIPT_ID)
        self.assertEqual(demo.results[SCRIPT_ID]["status"], "pass")
        self.assertEqual(demo.results[SCRIPT_ID]["project"], latest)
        self.assertEqual(demo.project, latest)
        manual = dict(latest, branch="manual", dirty=True)
        with patch.dict(self.module, {"project_info": lambda _: copy.deepcopy(manual)}):
            demo.manual({"id": MANUAL_ID, "status": "pass", "checked": [0, 1]})
        self.assertEqual(demo.project, manual)
        self.assertEqual(demo.results[MANUAL_ID]["project"], manual)
        self.assertEqual(demo.results[MANUAL_ID]["source"], "human")
        demo.project["branch"] = "later"
        self.assertEqual(demo.results[MANUAL_ID]["project"]["branch"], "manual")

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for browser-logic regressions")
    def test_browser_context_notices_counts_and_rendered_results(self):
        # Run the real browser logic with inert DOM/network boundaries, without a server.
        harness = self.project / "browser-check.cjs"
        harness.write_text(r'''
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const elements = new Map(), requests = [];
function element(id) {
  if (!elements.has(id)) elements.set(id, {dataset:{}, innerHTML:'', hidden:false, scrollTop:0,
    scrollHeight:100, clientHeight:100, addEventListener(){}, querySelectorAll(){return [];},
    contains(){return false;}, focus(){}, classList:{contains(){return false;},remove(){},add(){},toggle(){}}});
  return elements.get(id);
}
const sandbox = {document:{getElementById:element,activeElement:null,querySelector(){return null;},
  querySelectorAll(){return [];}}, fetch:async path => {requests.push(path); return new Promise(()=>{});},
  setInterval(){},setTimeout(){},clearTimeout(){},requestAnimationFrame(){},console};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);
const run = code => vm.runInContext(code, sandbox);
run(`
globalThis.clean = {path:'/project',git:true,repository_root:'/project',branch:'feature',commit:'${'a'.repeat(40)}',dirty:false,checked_at:'2026-10-14T09:00:00Z'};
globalThis.script = {id:'script',title:'Script',category:'Tests',mode:'script',description:'A test',criterion:'Matches',baseline:'expected.json',manifest:'oracle.json'};
globalThis.manual = {id:'manual',title:'Manual',category:'Tests',mode:'manual',description:'A walkthrough',criterion:'Observed',prerequisites:'Local app',steps:[{action:'Open',expected:'Visible'}]};
globalThis.saved = {status:'pass',source:'script',project:{...clean},started_at:'2026-10-14T09:01:00Z',finished_at:'2026-10-14T09:02:00Z',output:[],logs:[],actual:{ok:true},expected:{ok:true}};
state = {project:{...clean},tests:[script,manual],results:{script:{...saved}},job:{id:'run-1',ids:['script'],status:'complete',started_at:saved.started_at},session:'s'};
focused='script';
`);
assert.equal(run('codeContextNotice(clean,{...clean,checked_at:"later"})'), null);
assert.equal(run('codeContextNotice(clean,{...clean,commit:"a".repeat(9)+"b".repeat(31)}).label'), 'Earlier code');
for (const [key,value] of Object.entries({path:'/other',repository_root:'/other',branch:'main',commit:'b'.repeat(40),dirty:true,git:false})) {
  sandbox.change = {[key]:value};
  assert.equal(run('codeContextNotice(clean,{...clean,...change}).label'), 'Earlier code');
}
assert.equal(run('codeContextNotice({...clean,dirty:true},{...clean,dirty:true}).label'), 'Code context unverified');
assert.equal(run('codeContextNotice({...clean,git:false},{...clean,git:false}).label'), 'Code context unverified');
assert.equal(run('codeContextNotice({...clean,dirty:null},{...clean,dirty:null}).label'), 'Code context unverified');
assert.equal(run('codeContextNotice(null,clean).label'), 'Code context unverified');
assert.equal(run('codeContextNotice({...clean,path:undefined},clean).label'), 'Code context unverified');
assert.equal(run('resultContext("script").label'), 'Last run');
run('renderDetail()');
assert.ok(!element('test-detail').innerHTML.includes('Earlier code'));
run('state.project.commit="b".repeat(40); renderDetail()');
let html = element('test-detail').innerHTML;
assert.ok(html.includes('Earlier code'));
assert.ok(html.includes('Passed — output matches')); // Historical outcome is not rewritten.
assert.ok(html.indexOf('Code context differs') < html.indexOf('<details'));
assert.ok(html.includes('a'.repeat(40)) && html.includes('b'.repeat(40)));
run('state.project.commit="c".repeat(40); renderDetail()');
assert.ok(element('test-detail').innerHTML.includes('c'.repeat(40))); // Same warning, refreshed detail.
run('state.results.script.catalog_changed=true; renderDetail()');
assert.ok(element('test-detail').innerHTML.includes('earlier test definition'));
assert.ok(element('test-detail').innerHTML.includes('Code context differs'));
run('delete state.results.script.catalog_changed; terminalViews.add("script"); renderDetail()');
html = element('test-detail').innerHTML;
assert.ok(html.includes('Hide terminal') && html.includes('id="execution-results"'));
assert.ok(html.indexOf('id="execution-terminal"') < html.indexOf('id="execution-results"'));
run('state.results.manual={...saved,source:"human",checked:[0],notes:"Verified"}; focused="manual"; renderDetail()');
html = element('test-detail').innerHTML;
assert.ok(html.includes('Earlier code') && html.includes('Manual walkthrough'));
assert.ok(html.includes('User-reported result') && html.includes('a'.repeat(40)));
run(`state.results={fresh:{...saved,project:{...state.project}},oldPass:{...saved},oldFail:{...saved,status:'fail'}};`);
assert.equal(run('runSummary(["fresh","oldPass","oldFail"])'), '1 passed · 2 earlier/unverified (1 passed · 1 failed)');
run(`state.results={script:{...saved,project:{...clean,dirty:true}}}; state.project={...clean,dirty:true}; focused='script'; renderDetail();`);
html = element('test-detail').innerHTML;
assert.ok(html.includes('Code context unverified'));
assert.ok(html.includes('Passed — output matches'));
assert.equal(run('runSummary(["script"])'), '1 earlier/unverified (1 passed)');
assert.ok(run('codeContextMarkup({...clean,path:"<script>alert(1)</script>"},clean)').includes('&lt;script&gt;'));
assert.equal(run('resultContext("unrun")'), null);
run('state.results.script={status:"queued"};');
assert.equal(run('resultContext("script").notices.length'), 0);
assert.deepEqual(requests, ['/api/state']); // Loading and rendering never invoke a test.
console.log('Browser context and rendering regressions passed.');
''', encoding="utf-8")
        result = subprocess.run([shutil.which("node"), str(harness),
                                 str(self.catalog / "harnesses/lab/web/app.js")],
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("regressions passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
