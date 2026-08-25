# Common Rationalizations (and Red Flags)

Use this when someone (including you) is talking themselves out of a deprecation.

| Rationalization | Reality |
|---|---|
| "It still works" | Working code without a maintainer accumulates security debt. |
| "Someone might need it" | Rebuilding is cheaper than keeping "just in case". |
| "Migration too expensive" | Compare to 2-3 years of maintenance. Usually cheaper to migrate. |
| "We'll deprecate after the new thing is done" | Deprecation starts at design time. Plan now. |
| "Users migrate on their own" | They won't. Do it yourself (Churn Rule). |
| "We can maintain both" | Double the tests, docs, onboarding, and bugs. |

## Red Flags — stop and fix before proceeding

- Deprecated system without a replacement ready
- Deprecation notice without migration tooling
- Soft deprecation running for years with no progress
- Zombie code without an owner
- New features added to a deprecated system
- Removing code without verifying zero consumers
- "Works for now" with no plan
