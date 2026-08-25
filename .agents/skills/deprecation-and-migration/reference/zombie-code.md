# Zombie Code Detection

Zombie code = no owner, but still has active consumers. Signs:

- No commits in 6+ months on otherwise-active code
- No assigned CODEOWNERS
- Failing tests that nobody fixes
- Dependencies with CVEs left ignored
- Docs referencing removed systems

**Response:** assign an owner OR commit to a concrete migration plan. No middle ground.

## Finding zombies in AS v2

```bash
# Code with no recent commits
git log --all --before="6 months ago" --name-only | sort -u

# Files with no tests
find v2/backend/apps -name "*.py" | grep -v test | grep -v __pycache__

# Uninstalled but still imported
grep -rn "from apps.removed_app" v2/backend/
```
