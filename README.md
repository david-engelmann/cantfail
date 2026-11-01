# cantfail

The tautology detector. It mutates the code under a test and the test's own assertions, and any test no mutation can turn red is named decorative.

## What this is

Agent written suites flood repos with tests that cannot fail for a real reason, including tests that assert a mock returns what the mock was told to return. Cantfail applies a fixed panel of small, fast mutations per test file and reports the tests that stayed green under every applicable mutant. A decorative test is named in plain language on the pull request, next to the mutant that walked through it. The boundary with its siblings is one sentence. Cantfail asks whether a test can fail, canaryfield asks whether the harness catches planted defects, suitediet asks which tests earn their runtime.

## Status

Local seed is done and the seed commit sits on the local main branch. Remote seed is pending a token access fix and writes returned 403 when verified on 2026-10-31. Setup is in progress locally on a branch and nothing has been pushed yet.

The contract lives in CONTRACT.md. Setup obligations S1 to S4 are met. Slice 1 obligations C1 to C8 are met on this branch when the local gate passes and the gate is python with pytest alone.

Slice 1 is built. It carries the static mock assertion fast path and the fixed mutation panel and the text and JSON reports, with a synthetic demo project and its generated report under examples. Closed rounds are 0 of 100.

AGENTS.md is pending because the canonical template has not been supplied by the main chat. Pinned formats none. Part of the impatient programming portfolio, in the Gate Truth arc.

## Licence

MIT. See LICENSE.
