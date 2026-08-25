# Worktree Caveats and Troubleshooting

## Caveats

- Worktrees share the same `.git` database.
- Can't have the same branch checked out in two worktrees.
- Uncommitted changes stay in their own worktree.
- Some IDEs need configuration to handle multiple roots.

## Troubleshooting

### Branch already checked out

```bash
# Error: 'branch' is already checked out at '/path'
# Solution: remove the other worktree first, or use a different branch
git worktree list  # find which worktree holds it
```

### Locked / stale worktree

```bash
# If a worktree was moved or deleted manually
git worktree prune
```
