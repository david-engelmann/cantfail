# cantfail

The tautology detector. It mutates the code under a test and the test's own assertions, and any test no mutation can turn red is named decorative.

## What this is

Agent written suites flood repos with tests that cannot fail for a real reason, including tests that assert a mock returns what the mock was told to return. Cantfail applies a fixed panel of small, fast mutations per test file and reports the tests that stayed green under every applicable mutant. A decorative test is named in plain language on the pull request, next to the mutant that walked through it. The boundary with its siblings is one sentence. Cantfail asks whether a test can fail, canaryfield asks whether the harness catches planted defects, suitediet asks which tests earn their runtime.

## Status

Local seed is done and the seed commit sits on the local main branch. Remote seed is pending a token access fix and writes returned 403 when verified on 2026-10-31. Setup is in progress locally on a branch and nothing has been pushed yet.

The contract lives in CONTRACT.md. Setup obligations S1 to S4 are met. Slice 1 obligations C1 to C8 are met. Slice 2 obligations D1 to D6 are met. Slice 3 obligations E1 to E7 are met on this branch when the local gate passes and the gate is python with pytest alone. Slice 4 obligations F1 to F6 are met on this branch when the local gate passes. Slice 5 obligations G1 to G6 are met on this branch when the local gate passes.

Slice 1 is built. It carries the static mock assertion fast path and the fixed mutation panel and the text and JSON reports, with a synthetic demo project and its generated report under examples.

Slice 2 is built on top of slice 1. Verdicts are now recorded per test function and the file level verdict is a rollup derived from the function verdicts under the rule stated in the contract. The JSON report carries a top level schema field with the value cantfail-report/2 and both reports carry the per function verdicts. The static scan also flags a mock that was configured inside a helper or a fixture in the same file and bound to the test under another name. One pattern was considered and rejected in this slice and the contract records the rejection and its reason. The demo reports under examples are regenerated in the new format and the demo verdicts are unchanged at file level.

Slice 3 is built on top of slice 2. Test methods inside classes are now judged on their own beside the top level functions, named by their class and their method, and the file verdict rolls them up under the same rule as functions. The whole file judgement remains only for a test file with no selectable test items at all. The report schema is cantfail-report/3 because the functions list now carries method entries beside function entries, and the demo reports under examples are regenerated in the new format with every demo verdict unchanged.

Slice 4 is built on top of slice 3. The collection naming settings of the analysed project are now read from the one config source pytest would use for it, and item selection honours its function and class naming while discovery honours its file naming, so a project that renames its tests in its pytest settings is judged on the items it actually has. The report names any non default settings in force and the schema stays at cantfail-report/3, and a project with no settings source regenerates reports byte identical to the earlier slices.

Slice 5 is built on top of slice 4. The static scan now reads a test file under the same collection naming settings as the selector, so a static finding is reported only for an assertion inside a test function as the function naming setting in force defines it, and a function the project settings deselect earns no finding just as it earns no verdict item. Selection and verdicts are unchanged by this slice and the schema stays at cantfail-report/3, and the demo reports still regenerate byte identical. Round 4 closed on 2026-11-01 after slice 5 was audited and reviewed on two axes and attacked by a red team, with every material finding fixed under FIX-20 and FIX-21 before the owner of this line approved the round.

Round 1 closed on 2026-10-31. Slice 2 was built, then audited and reviewed on two axes and attacked by a red team, and every material finding was fixed in the contract fix obligations FIX-1 to FIX-7 before the owner of this line approved the round. Round 2 closed on 2026-10-31 the same way, with slice 3 audited and reviewed on two axes and attacked by a red team and every material finding fixed under FIX-8 to FIX-13 before the owner of this line approved the round. Closed rounds are 4 of 100. Round 3 closed on 2026-11-01 the same way, with slice 4 audited and reviewed on two axes and attacked by a red team and every material finding fixed under FIX-14 to FIX-19 before the owner of this line approved the round.

AGENTS.md is pending because the canonical template has not been supplied by the main chat. Pinned formats none. Part of the impatient programming portfolio, in the Gate Truth arc.

## Licence

MIT. See LICENSE.
