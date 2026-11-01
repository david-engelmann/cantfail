# cantfail

The tautology detector. It mutates the code under a test and the test's own assertions, and any test no mutation can turn red is named decorative.

## What this is

Agent written suites flood repos with tests that cannot fail for a real reason, including tests that assert a mock returns what the mock was told to return. Cantfail applies a fixed panel of small, fast mutations per test file and reports the tests that stayed green under every applicable mutant. A decorative test is named in plain language on the pull request, next to the mutant that walked through it. The boundary with its siblings is one sentence. Cantfail asks whether a test can fail, canaryfield asks whether the harness catches planted defects, suitediet asks which tests earn their runtime.

## Status

Seeded in October 2026. The build has not started. Part of the impatient programming portfolio, in the Gate Truth arc.

## Licence

MIT. See LICENSE.
