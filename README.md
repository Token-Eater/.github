# Token-Eater Default Community Health Files

This is a special `.github` repository that provides **default community health files** for all repositories in the Token-Eater organization.

## How It Works

Files in this repository's `.github/` directory automatically apply to any Token-Eater repository that doesn't have its own version of those files.

### Automatic Inheritance

When a repository doesn't have these files, GitHub will automatically use the versions from this repository:

- **CONTRIBUTING.md** - Contribution guidelines
- **CODE_OF_CONDUCT.md** - Community standards
- **ISSUE_TEMPLATE/** - Issue templates for bugs, features, etc.
- **FUNDING.yml** - Sponsorship configuration

### Override Behavior

Individual repositories can override these defaults by adding their own versions of these files.

## Files Included

- `.github/CONTRIBUTING.md` - Detailed contribution workflow
- `.github/CODE_OF_CONDUCT.md` - Contributor Covenant v2.0
- `.github/FUNDING.yml` - GitHub Sponsors configuration template
- `.github/ISSUE_TEMPLATE/bug_report.md` - Bug report template
- `.github/ISSUE_TEMPLATE/feature_request.md` - Feature request template
- `.github/ISSUE_TEMPLATE/skill_submission.md` - Skill submission template (marketplace-specific)
- `.github/setup-github-files.sh` - Automated setup script for new repos
- `.github/README.md` - Guide for using these templates

## For Repository Maintainers

### Using Default Files

Simply create a new repository without these files, and they'll be inherited automatically from this repository.

### Customizing for a Specific Repo

To customize for a specific repository:

1. Copy the file(s) you want to customize from this repository
2. Add them to your repository's `.github/` directory
3. Modify as needed
4. Commit and push

Your custom version will take precedence over the default.

### Automated Setup

Use the setup script to copy and customize these files:

```bash
# In your repository
curl -O https://raw.githubusercontent.com/Token-Eater/.github/main/.github/setup-github-files.sh
chmod +x setup-github-files.sh
./setup-github-files.sh
```

## Updating Defaults

To update the default files for all repositories:

1. Clone this repository
2. Modify files in `.github/`
3. Commit and push
4. Changes automatically apply to repositories without custom versions

## Resources

- [GitHub Community Health Files](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)
- [Contributor Covenant](https://www.contributor-covenant.org/)

---

**Note:** This repository applies to all Token-Eater repositories. Individual repos can override by adding their own versions.
