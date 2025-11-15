# GitHub Repository Templates

This directory contains standard repository governance files that can be reused across multiple repositories.

## Files in This Directory

### CONTRIBUTING.md

**Purpose:** Guidelines for contributing to the project

**Customize for your repo:**
- Update repository URLs (`token-eater/repo-name`)
- Adjust contribution workflow if needed
- Modify quality standards for your use case
- Update contact information

### CODE_OF_CONDUCT.md

**Purpose:** Community standards and behavioral expectations

**Generally:** No customization needed (uses Contributor Covenant standard)

**Optional customization:**
- Update enforcement contact information
- Add project-specific community guidelines

### FUNDING.yml

**Purpose:** Configure GitHub Sponsors and funding links

**Customize for your repo:**
```yaml
# Uncomment and add your usernames
github: your-github-username
patreon: your-patreon-username
custom: ["https://your-donation-link.com"]
```

### ISSUE_TEMPLATE/

**Purpose:** Standardized issue submission forms

**Files:**
- `bug_report.md` - Bug reporting template
- `feature_request.md` - Feature suggestion template
- `skill_submission.md` - Skill submission template (marketplace-specific)

**Customize for your repo:**
- Modify fields as needed
- Add/remove templates
- Update labels and assignees

## Using These Templates in Other Repos

### Method 1: Manual Copy (Recommended for Learning)

```bash
# Navigate to your target repository
cd /path/to/your-repo

# Copy the entire .github directory
cp -r /path/to/skills-marketplace/.github ./.github

# Customize for your repo
# Edit files to update:
# - Repository URLs
# - Author names
# - Specific workflows
# - Contact information
```

### Method 2: Selective Copy

Copy only specific files you need:

```bash
# Copy just CONTRIBUTING.md
cp /path/to/skills-marketplace/.github/CONTRIBUTING.md ./.github/

# Copy just CODE_OF_CONDUCT.md
cp /path/to/skills-marketplace/.github/CODE_OF_CONDUCT.md ./.github/

# Copy issue templates
cp -r /path/to/skills-marketplace/.github/ISSUE_TEMPLATE ./.github/
```

### Method 3: Automated Setup Script

Use the provided script to set up .github files:

```bash
# Copy the setup script
cp /path/to/skills-marketplace/.github/setup-github-files.sh /usr/local/bin/

# Make executable
chmod +x /usr/local/bin/setup-github-files.sh

# Run in your target repo
cd /path/to/your-repo
setup-github-files.sh
```

See `setup-github-files.sh` for the automation script.

## GitHub Repository Template Feature

For frequently creating new repos with these files:

### Create a Template Repository

1. **Make this repo a template:**
   - Go to repository Settings
   - Check "Template repository"

2. **Create new repos from template:**
   - Click "Use this template" button
   - New repo includes all .github files

3. **Customize after creation:**
   - Update repository-specific information
   - Modify as needed for the new project

### Alternative: Use GitHub's Built-in Templates

Create a `.github` repository in your organization:

1. **Create special repo:**
   ```bash
   # In your organization or user account
   gh repo create .github --public
   ```

2. **Add template files:**
   ```bash
   cd .github
   mkdir -p .github
   # Copy files from this marketplace
   cp -r /path/to/skills-marketplace/.github/* .github/
   git add .
   git commit -m "Add default community health files"
   git push
   ```

3. **Automatic inheritance:**
   - All repos in your org/account inherit these files
   - No manual copying needed
   - Update once, applies everywhere

## Customization Checklist

When using these templates in a new repo:

### CONTRIBUTING.md
- [ ] Update repository URLs (find/replace `token-eater/skills-marketplace`)
- [ ] Adjust contribution workflow if different
- [ ] Update contact information
- [ ] Modify quality standards if needed
- [ ] Remove skill-specific sections if not applicable

### CODE_OF_CONDUCT.md
- [ ] Update enforcement contact (if not using GitHub issues)
- [ ] Review and accept as-is (usually no changes needed)

### FUNDING.yml
- [ ] Add your GitHub Sponsors username
- [ ] Add your Patreon username
- [ ] Add custom donation links
- [ ] Remove commented sections you don't use

### ISSUE_TEMPLATE/
- [ ] Review each template
- [ ] Modify labels and categories
- [ ] Update fields as needed
- [ ] Remove templates you don't need (e.g., `skill_submission.md` for non-marketplace repos)
- [ ] Add project-specific templates

### README.md (this file)
- [ ] Delete this file from target repo (it's for reference only)

## File Locations

These files work anywhere in `.github/`:

```
your-repo/
├── .github/
│   ├── CONTRIBUTING.md          ← Contribution guidelines
│   ├── CODE_OF_CONDUCT.md       ← Community standards
│   ├── FUNDING.yml              ← Sponsorship links
│   ├── ISSUE_TEMPLATE/          ← Issue forms
│   │   ├── bug_report.md
│   │   ├── feature_request.md
│   │   └── skill_submission.md
│   └── workflows/               ← GitHub Actions (optional)
└── README.md
```

## Best Practices

### For All Repositories

- ✅ Always include CONTRIBUTING.md
- ✅ Always include CODE_OF_CONDUCT.md
- ✅ Use issue templates for consistency
- ✅ Configure FUNDING.yml if accepting donations

### For Open Source Projects

- ✅ Add LICENSE file (choose appropriate license)
- ✅ Clear contribution guidelines
- ✅ Welcoming code of conduct
- ✅ Well-organized issue templates

### For Organizations

- ✅ Create `.github` special repository for defaults
- ✅ Standardize across all org repos
- ✅ Update centrally when policies change

## Advanced: GitHub Actions

Add CI/CD workflows to `.github/workflows/`:

```bash
# Example: Add validation workflow
cat > .github/workflows/validate.yml <<'EOF'
name: Validate

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Validate JSON
        run: |
          find . -name "*.json" -exec jq empty {} \;
EOF
```

## Resources

- [GitHub Community Health Files](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)
- [GitHub Issue Templates](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests)
- [Contributor Covenant](https://www.contributor-covenant.org/)
- [GitHub Repository Templates](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-template-repository)

## Support

Questions about these templates?

- 💬 [GitHub Discussions](https://github.com/token-eater/skills-marketplace/discussions)
- 📖 [Documentation](../docs/)

---

**Pro Tip:** Use the `.github` special repository feature for organization-wide defaults, and repository-specific `.github/` directories for project-specific customizations.
