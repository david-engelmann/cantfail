# Contract

Cantfail asks whether a test can fail. Canaryfield asks whether the harness catches planted defects and suitediet asks which tests earn their runtime. Cantfail stays inside the first question only.

A test that stays green under a fixed panel of mutations is a candidate for review. A surviving mutant is evidence about that panel and about the analysed project only. It is never proof that a test can fail for no reason and it is never proof that a test can never fail at all.

## Setup obligations

Obligation S1 covers the seed. The repository carries the seed README and the MIT licence from its first commit and later work lands on branches rather than on the seed commit. This is covered by inspection of the repository history and by the status section of the README.

Obligation S2 covers the local gate. The repository test suite runs with python and pytest alone and needs no network access and no paid service. This is covered by tests in the tests folder and by the continuous integration workflow running the same command.

Obligation S3 covers honest status. The README status section records the remote seed state and the contract state without claiming work that has not landed. This is covered by inspection against this contract.

Obligation S4 covers synthetic fixtures. Every fixture and example in this repository is synthetic and carries no real trace and no private detail. This is covered by inspection of the examples folder and the tests folder.

## Slice 1 obligations

Obligation C1 covers static mock detection. The static scan flags a test that assigns a value to the return value of a mock and later asserts equality with that same value. The scan also flags an assertion that compares an expression with itself and an assertion on the constant true value. Each finding carries a file path and a line number. This is covered by tests in tests/test_static_scan.py.

Obligation C2 covers the fixed mutation panel. The panel applies return removal by returning no value and comparison inversion and numeric constant movement by one in both directions and boolean constant negation. The panel is fixed for slice 1 and every mutant records its kind and its source line. This is covered by tests in tests/test_mutations.py.

Obligation C3 covers safe execution. Mutants run one at a time in a scratch copy of the analysed project and the analysed files are never written. The analysed files are byte identical after a run. This is covered by tests in tests/test_runner.py.

Obligation C4 covers the baseline. A test file whose unmutated run already fails is reported as a baseline failure and is never reported as decorative. This is covered by tests in tests/test_runner.py.

Obligation C5 covers per test file verdicts. A test file that stays green under every applicable mutant is reported as a decorative candidate and the report names its test functions and lists every mutant that walked through. A test file that turns red under at least one mutant is reported as able to fail under this panel. This is covered by tests in tests/test_runner.py.

Obligation C6 covers the report shape. The analysis produces a human readable text report and a JSON report with the same findings. Both reports carry the static findings and the per file verdicts and the surviving mutants. This is covered by tests in tests/test_report.py and tests/test_cli.py.

Obligation C7 covers conservative wording. Reports describe decorative results as candidates and survivors as mutants that walked through the panel. Reports never claim that a surviving mutant proves a test is worthless and never claim that a killed mutant proves a test is strong. This is covered by tests in tests/test_report.py.

Obligation C8 covers discovery. The runner pairs a test file with the source module of the same stem when one exists and otherwise pairs it with every non test source module in the project. Each run of a single test file under a single mutant has a timeout. This is covered by tests in tests/test_runner.py.

## Slice 2 obligations

Obligation D1 covers per test function verdicts. Every top level test function in a test file is judged on its own. The runner runs the fixed panel against that function alone by selecting its node in the scratch copy and records one verdict for the function. The verdict is one of four values. A function that turns red under at least one mutant is reported as able to fail. A function that stays green under every applicable mutant is reported as a decorative candidate. A function whose unmutated run already fails is reported as a baseline failure. A function with no applicable mutant is reported as having no applicable mutants. A run that times out never counts toward a decorative verdict. Class based tests are named only when they are plain functions in slice 1 and per function verdicts in this slice cover top level test functions. This is covered by tests in tests/test_functions.py.

Obligation D2 covers the file level rollup. The file level verdict is derived from the function verdicts and never from a separate whole file mutant run. A file is a decorative candidate only when every judged function in it is a decorative candidate and at least one function was judged. A function counts as judged when its baseline passed and at least one mutant applied to it. A file with at least one judged function that can fail is reported as able to fail. A file where no function was judged and at least one function failed its baseline is reported as a baseline failure. A file where no function was judged and no function failed its baseline is reported as having no applicable mutants. This is covered by tests in tests/test_functions.py.

Obligation D3 covers the report format version. The JSON report carries a top level field named schema and its value is cantfail-report/2. The text report and the JSON report both carry the per function verdicts with the same facts. The file level entry keeps its surviving mutants as the mutants that no judged function turned red. This is covered by tests in tests/test_report.py and tests/test_cli.py.

Obligation D4 covers honest runtime. The fixed panel does not grow in this slice. One scratch copy is made per mutant and every judged function runs inside that copy before the copy is removed. The baseline for each function runs in one shared scratch copy per test file. This is covered by inspection of the runner and by the local gate staying fast enough to run in the demo.

Obligation D5 covers one new static pattern. The static scan also flags an assertion that compares a call result with the exact literal a mock was configured with inside a helper or a fixture defined in the same file. The helper form covers a test that binds a name to a call of the helper. The fixture form covers a test that takes the fixture name as a parameter. The binding only forms when the helper or fixture returns the very mock it configured and the configured value is unambiguous. An assertion against a different literal is not flagged and a helper that returns an unconfigured object is not flagged. This is covered by tests in tests/test_static_scan.py.

Obligation D6 covers the pattern that was considered and rejected. An assertion that a mock was called was considered as a new pattern and rejected for this slice. A call assertion next to a configured return value does not on its own prove the test cannot fail for a real reason because the call itself may be the behaviour under test. No finding kind is emitted for call assertions in this slice. This is recorded here so the rejection is part of the contract and not a silent gap.

## Round 1 review fixes

The Round 1 audit and red team found ways the slice 2 claims could mislead. The obligations below amend D1 and D2 and D5 where they conflict, and each one is covered by tests in tests/test_round1_fixes.py unless it says otherwise.

Obligation FIX-1 covers duplicate names. A test function name defined more than once at module level is judged once, under the single name pytest can run. The earlier definition never executes and is never reported as judged on its own.

Obligation FIX-2 covers rollup precedence. A file is never reported as a decorative candidate while any function in it failed its baseline. When no judged function can fail and at least one function failed its baseline the file is reported as a baseline failure, even when every judged function is a decorative candidate.

Obligation FIX-3 covers class based tests. A file that carries class based test methods is judged at whole file level by the slice 1 behaviour, with the per function verdicts for its top level functions reported alongside. Such a file is never silently skipped and never reported as having no applicable mutants merely because its tests are methods. The file level entry records that it was judged whole file.

Obligation FIX-4 covers timeouts as their own verdict. A function whose baseline run times out, and a judged function that turns red under no mutant and has at least one timed out mutant run, are reported as inconclusive. Inconclusive is a fifth verdict value added by this amendment. A timed out mutant is never listed among the surviving mutants in either report, because a timeout is unknown and not a walk through.

Obligation FIX-5 covers method aware helper and fixture matching. The D5 pattern matches the configured call itself, named by the mock and the attribute chain that was configured. An assertion on a different method of the same mock is not flagged. A helper that configures several methods on one mock flags each configured call. One call configured with two distinct literals inside one helper stays unflagged for that call alone, and the rest of the mock still counts.

Obligation FIX-6 covers binding scope. Helper and fixture bindings live inside the function that creates them. A binding formed in one test function never flags an assertion in another function, and assigning a bound name to anything else clears the binding from that point on.

Obligation FIX-7 covers the rejected pattern test. The D6 rejection is pinned by a test showing that call assertions emit no finding. Obligation D4 stays inspection only by its own wording and that is now stated as a deliberate mapping rather than an oversight. One further recorded fact is that verdicts are assigned by execution, so a function that calls another test function inherits its killing power, and the baseline flag on a file verdict means at least one function passed its baseline in the rollup path and the whole file baseline in the whole file path.

## Status of this contract

Setup obligations S1 to S4 are met on this branch. Slice 1 obligations C1 to C8 are met on this branch when the local gate passes. Slice 2 obligations D1 to D6 as amended by the Round 1 review fixes FIX-1 to FIX-7 are met on this branch when the local gate passes. Any obligation that stops being met must be recorded in the README status section in the same change that breaks it.
