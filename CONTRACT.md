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

## Status of this contract

Setup obligations S1 to S4 are met on this branch. Slice 1 obligations C1 to C8 are met on this branch when the local gate passes. Any obligation that stops being met must be recorded in the README status section in the same change that breaks it.
