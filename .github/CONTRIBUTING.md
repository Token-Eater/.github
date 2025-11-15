# Contributing to Skills Marketplace

Thank you for your interest in contributing to the Skills Marketplace! This document provides guidelines for submitting skills, reporting issues, and contributing to the project.

## Ways to Contribute

- 🎯 **Submit skills** - Share your Claude Code skills with the community
- 🐛 **Report bugs** - Help us identify and fix issues
- 💡 **Suggest features** - Propose improvements to the marketplace
- 📝 **Improve documentation** - Help make our docs clearer
- ⭐ **Star the repo** - Show your support!

## Submitting Skills

### Prerequisites

Before submitting a skill, ensure it meets our quality standards:

- ✅ Valid YAML frontmatter in SKILL.md
- ✅ Clear description and purpose
- ✅ Usage examples and documentation
- ✅ Tested locally in Claude Code
- ✅ Follows semantic versioning
- ✅ No hardcoded secrets or credentials
- ✅ Appropriate category and tags

### Skill Submission Process

#### 1. Create Your Skill

Follow the [Creating Skills Guide](../docs/creating-skills.md) to build your skill:

```bash
# Use the skill-creator toolkit (recommended)
python3 ~/.claude/skills/skill-creator/scripts/init_skill.py your-skill-name

# Or create manually following the structure
mkdir -p skills/your-skill-name
```

#### 2. Test Locally

Install and test your skill before submitting:

```bash
# Add marketplace locally
/plugin marketplace add ./skills-marketplace

# Install your skill
/plugin install your-skill-name

# Test thoroughly in Claude Code
```

#### 3. Validate Your Skill

Use the validation tools to check your skill:

```bash
# Validate structure and frontmatter
python3 ~/.claude/skills/skill-creator/scripts/quick_validate.py skills/your-skill-name

# Check for common issues
# - YAML frontmatter format
# - Required fields present
# - No frontmatter in subdirectory files
```

#### 4. Fork and Submit

1. **Fork** this repository to your GitHub account
2. **Clone** your fork locally
3. **Create a branch** for your skill:
   ```bash
   git checkout -b skill/your-skill-name
   ```
4. **Add your skill** to the `skills/` directory
5. **Update marketplace-preview.json** (new skills start in preview):
   ```json
   {
     "name": "your-skill-name",
     "description": "Brief description",
     "version": "1.0.0",
     "author": "Your Name",
     "category": "productivity",
     "tags": ["tag1", "tag2"],
     "source": "./skills/your-skill-name"
   }
   ```
6. **Commit your changes**:
   ```bash
   git add skills/your-skill-name/
   git add .claude-plugin/marketplace-preview.json
   git commit -m "feat: Add your-skill-name skill"
   ```
7. **Push** to your fork:
   ```bash
   git push origin skill/your-skill-name
   ```
8. **Open a Pull Request** to this repository

#### 5. Pull Request Guidelines

Your PR description should include:

- **Skill name and purpose** - What does it do?
- **Category** - Which category does it belong to?
- **Usage example** - Show how to use the skill
- **Testing** - How did you test it?
- **Dependencies** - Any external tools or packages required?

**PR Template:**
```markdown
## Skill Submission: [Skill Name]

**Description:** Brief description of what the skill does

**Category:** productivity | development | data | documentation | devops | ai-ml | security | web | knowledge | examples

**Usage Example:**
```bash
# Show how to use the skill
```

**Testing:**
- [ ] Tested locally in Claude Code
- [ ] Validated with skill-creator toolkit
- [ ] Checked for secrets/credentials
- [ ] Documentation complete

**Dependencies:**
- List any external dependencies (tools, packages, APIs)

**Additional Notes:**
Any other relevant information
```

#### 6. Review Process

After submitting your PR:

1. **Automated checks** will validate your skill structure
2. **Maintainers** will review your submission
3. **Community feedback** may be requested
4. **Revisions** may be needed based on feedback

Once approved:
- Your skill will be added to **marketplace-preview.json** (beta catalog)
- After testing period and positive feedback, it may be promoted to **marketplace.json** (stable catalog)

## Reporting Issues

Found a bug or have a suggestion? Please open an issue:

### Bug Reports

Use the [Bug Report template](https://github.com/token-eater/skills-marketplace/issues/new?template=bug_report.md):

- Describe the issue clearly
- Include steps to reproduce
- Provide environment details (OS, Claude Code version, etc.)
- Include error messages or screenshots

### Feature Requests

Use the [Feature Request template](https://github.com/token-eater/skills-marketplace/issues/new?template=feature_request.md):

- Describe the feature you'd like
- Explain the use case and benefits
- Suggest implementation if you have ideas

## Code of Conduct

This project adheres to a [Code of Conduct](./CODE_OF_CONDUCT.md). By participating, you agree to uphold this code. Please report unacceptable behavior to the project maintainers.

## Development Guidelines

### Skill Structure

All skills must follow this structure:

```
skills/
└── skill-name/
    ├── SKILL.md           # Main skill definition (required)
    ├── scripts/           # Optional: Helper scripts
    ├── references/        # Optional: Reference docs
    └── assets/            # Optional: Images, templates
```

### SKILL.md Format

```markdown
---
name: skill-name
description: Brief description of the skill
version: 1.0.0
author: Your Name
category: productivity
tags:
  - tag1
  - tag2
---

# Skill Name

[Detailed documentation here]

## Usage

[Usage examples]

## Examples

[Code examples]
```

### Versioning

Use [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0 → 2.0.0): Breaking changes
- **MINOR** (1.0.0 → 1.1.0): New features, backward compatible
- **PATCH** (1.0.0 → 1.0.1): Bug fixes, backward compatible

### Categories

Choose the appropriate category for your skill:

- `productivity` - Task management, workflows, automation
- `development` - Git, testing, code quality, deployment
- `data` - Data processing, visualization, reporting
- `documentation` - Markdown, diagrams, API docs
- `devops` - CI/CD, containers, infrastructure
- `ai-ml` - AI/ML integration, training, evaluation
- `security` - Security scanning, verification, compliance
- `web` - Web scraping, APIs, frontend tools
- `knowledge` - Research, memory, note-taking
- `examples` - Templates and learning resources

### Tags

Add relevant tags to improve discoverability:

- Be specific and descriptive
- Use lowercase
- Separate words with hyphens (e.g., `version-control`, `api-testing`)
- Limit to 3-5 most relevant tags

## Maintaining Your Skills

After your skill is accepted:

### Updates

Submit updates via Pull Request:

1. Update the skill in your fork
2. Increment version number appropriately
3. Update both SKILL.md frontmatter and marketplace JSON
4. Open PR with description of changes

### Issues

Respond to issues related to your skill:

- Monitor issues labeled with your skill name
- Provide helpful responses and fixes
- Update documentation if questions are common

### Deprecation

If you can no longer maintain a skill:

1. Open an issue to notify maintainers
2. Mark skill as "looking for maintainer"
3. Help transition to new maintainer if one is found

## License

By contributing to this project, you agree that your contributions will be licensed under the same license as the project (MIT License).

## Questions?

- 💬 [Open a discussion](https://github.com/token-eater/skills-marketplace/discussions)
- 📧 Contact maintainers via GitHub issues
- 📖 Read the [documentation](../docs/)

Thank you for contributing to the Skills Marketplace! 🎉
