---
name: sprint
description: Translates ticket IDs into git branches, PR titles, and description templates automatically.
license: MIT
metadata:
  author: skillet
  version: "1.0"
permissions:
  allow:
    - Bash(git *)
    - Bash(gh pr *)
---

# Sprint — Ticket to PR Automation

## Trigger

Load this skill when any of the following occurs:
- User asks to "start a ticket"
- User provides a ticket ID or title
- User asks to "create a branch" or "create a PR"
- User says "pick up ticket X"

---

## 1. Branch Creation

From a ticket, generate branch name:

```
<type>/<ticket-id>-<short-description>
```

Examples:
- `feat/PROJ-123-user-login`
- `fix/PROJ-456-fix-broken-link`
- `chore/PROJ-789-update-deps`

### Type mapping

| Ticket Type | Branch Type |
|-------------|-------------|
| Feature, Story, Epic | `feat` |
| Bug, Defect | `fix` |
| Task, Chore | `chore` |
| Hotfix | `hotfix` |

## 2. PR Title

Same as branch name (conventional commit format):

```
feat(PROJ-123): Add user login
```

## 3. PR Description Template

```markdown
### Ticket Link
https://jira.example.com/browse/PROJ-123

### Description
<!-- What does this PR do? Why is it needed? -->

### Steps to Test
<!-- How to verify this works -->

### Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes

### GIFs
<!-- Optional: screenshots or demo -->
```

## 4. Usage

When user says "Start ticket PROJ-123: Add user login":

1. Extract ticket ID: `PROJ-123`
2. Extract title: `Add user login`
3. Determine type: `feat` (assuming feature)
4. Create branch: `feat/PROJ-123-user-login`
5. Output ready-to-use commands:
   ```
   git checkout -b feat/PROJ-123-user-login
   # Make changes
   git add .
   git commit -m "feat(PROJ-123): Add user login"
   git push -u origin feat/PROJ-123-user-login
   ```

## 5. GitHub CLI Integration

If `gh` is available, auto-create PR after first commit:

```bash
gh pr create --title "feat(PROJ-123): Add user login" --body "$(cat <<EOF
### Ticket Link
https://jira.example.com/browse/PROJ-123

### Description
Add user login functionality.

### Steps to Test
1. Navigate to login page
2. Enter credentials
3. Verify redirect after login
EOF
)"
```

## 6. What Never To Do

- Create branch without ticket ID
- Use non-conventional commit format in PR title
- Skip the ticket link in PR description
- Force push the target branch