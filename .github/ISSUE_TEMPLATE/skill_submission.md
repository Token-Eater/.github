---
name: Skill Submission
about: Submit a new skill to the marketplace (alternative to PR)
title: '[SKILL] '
labels: skill-submission
assignees: ''
---

## Skill Information

**Name**:
**Category**: productivity | development | data | documentation | devops | ai-ml | security | web | knowledge | examples
**Version**: (e.g., 1.0.0)
**Author**:

## Description

Brief description of what the skill does (2-3 sentences).

## Usage Example

```bash
# Show how to use the skill
```

## Skill Location

**Option A - Repository Link:**
- Repository: (e.g., https://github.com/username/my-skill)
- Path to SKILL.md: (e.g., ./SKILL.md)

**Option B - Inline Submission:**
Paste the full SKILL.md content below:

```markdown
---
name: skill-name
description: Brief description
version: 1.0.0
author: Your Name
category: productivity
tags:
  - tag1
  - tag2
---

[Rest of skill content]
```

## Testing Checklist

- [ ] Tested locally in Claude Code
- [ ] Validated with skill-creator toolkit (or manually)
- [ ] No hardcoded secrets or credentials
- [ ] Documentation includes usage examples
- [ ] YAML frontmatter is valid
- [ ] Version number follows semantic versioning

## Dependencies

List any external dependencies (tools, packages, APIs, etc.):

-

## Additional Notes

Any other information that would be helpful for reviewers.

---

**Note**: This is an alternative to submitting via Pull Request. We encourage PRs when possible, but you can use this issue template if you're not familiar with the PR process. See [CONTRIBUTING.md](../.github/CONTRIBUTING.md) for more details.
