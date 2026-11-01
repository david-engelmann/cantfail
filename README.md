# cantfail

The tautology detector. It mutates the code under a test and the test's own assertions, and any test no mutation can turn red is named decorative.

## What this is

Agent written suites flood repos with tests that cannot fail for a real reason, including tests that assert a mock returns what the mock was told to return. Cantfail applies a fixed panel of small, fast mutations per test file and reports the tests that stayed green under every applicable mutant. A decorative test is named in plain language on the pull request, next to the mutant that walked through it. The boundary with its siblings is one sentence. Cantfail asks whether a test can fail, canaryfield asks whether the harness catches planted defects, suitediet asks which tests earn their runtime.

## Status

Local seed is done and the seed commit sits on the local main branch. Remote seed is pending a token access fix and writes returned 403 when verified on 2026-10-31. Setup is in progress locally on a branch and nothing has been pushed yet.

The contract lives in CONTRACT.md. Setup obligations S1 to S4 are met. Slice 1 obligations C1 to C8 are met. Slice 2 obligations D1 to D6 are met on this branch when the local gate passes and the gate is python with pytest alone.

Slice 1 is built. It carries the static mock assertion fast path and the fixed mutation panel and the text and JSON reports, with a synthetic demo project and its generated report under examples.

Slice 2 is built on top of slice 1. Verdicts are now recorded per test function and the file level verdict is a rollup derived from the function verdicts under the rule stated in the contract. The JSON report carries a top level schema field with the value cantfail-report/2 and both reports carry the per function verdicts. The static scan also flags a mock that was configured inside a helper or a fixture in the same file and bound to the test under another name. One pattern was considered and rejected in this slice and the contract records the rejection and its reason. The demo reports under examples are regenerated in the new format and the demo verdicts are unchanged at file level.

Round 1 closed on 2026-10-31. Slice 2 was built, then audited and reviewed on two axes and attacked by a red team, and every material finding was fixed in the contract fix obligations FIX-1 to FIX-7 before the owner of this line approved the round. Closed rounds are 1 of 100.

AGENTS.md is pending because the canonical template has not been supplied by the main chat. Pinned formats none. Part of the impatient programming portfolio, in the Gate Truth arc.

## Licence

MIT. See LICENSE.
