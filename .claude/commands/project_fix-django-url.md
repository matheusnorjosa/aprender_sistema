---
allowed-tools: Bash(git add:*), Bash(git commit:*), Bash(python manage.py:*)
description: Investigate and fix Django URL reversing issues
---

When encountering NoReverseMatch or missing named routes:
1) Inspect urls.py inclusion patterns and app namespaces.
2) Check view names and `name=` in path()/re_path().
3) Grep for template `{% url %}` or `reverse()` usages involved.
4) Provide a patch and a small regression test.
5) Summarize the change.
(think)
