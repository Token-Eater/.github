#!/usr/bin/env bash
# Setup GitHub community health files in a repository
#
# Usage:
#   ./setup-github-files.sh [source-repo-path]
#
# If source-repo-path is not provided, uses skills-marketplace as default

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default source (skills-marketplace)
SOURCE_REPO="${1:-/Users/kieransteele/git/containers/projects/skills-marketplace}"

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Error: Not in a git repository${NC}"
    echo "Please run this script from the root of your repository"
    exit 1
fi

# Check if source exists
if [ ! -d "$SOURCE_REPO/.github" ]; then
    echo -e "${RED}Error: Source .github directory not found${NC}"
    echo "Expected: $SOURCE_REPO/.github"
    exit 1
fi

echo -e "${GREEN}Setting up GitHub community health files...${NC}"
echo ""

# Create .github directory if it doesn't exist
mkdir -p .github/ISSUE_TEMPLATE

# Function to copy file with confirmation
copy_file() {
    local src="$1"
    local dest="$2"
    local name="$(basename "$src")"

    if [ -f "$dest" ]; then
        echo -e "${YELLOW}⚠️  $name already exists${NC}"
        read -p "Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "   Skipped $name"
            return
        fi
    fi

    cp "$src" "$dest"
    echo -e "${GREEN}✅ Copied $name${NC}"
}

# Copy main files
echo "Copying main community health files..."
copy_file "$SOURCE_REPO/.github/CONTRIBUTING.md" ".github/CONTRIBUTING.md"
copy_file "$SOURCE_REPO/.github/CODE_OF_CONDUCT.md" ".github/CODE_OF_CONDUCT.md"
copy_file "$SOURCE_REPO/.github/FUNDING.yml" ".github/FUNDING.yml"

echo ""
echo "Copying issue templates..."
copy_file "$SOURCE_REPO/.github/ISSUE_TEMPLATE/bug_report.md" ".github/ISSUE_TEMPLATE/bug_report.md"
copy_file "$SOURCE_REPO/.github/ISSUE_TEMPLATE/feature_request.md" ".github/ISSUE_TEMPLATE/feature_request.md"

# Ask about skill-specific template
echo ""
read -p "Include skill submission template (for marketplace repos)? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    copy_file "$SOURCE_REPO/.github/ISSUE_TEMPLATE/skill_submission.md" ".github/ISSUE_TEMPLATE/skill_submission.md"
else
    echo "   Skipped skill_submission.md"
fi

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Edit .github/CONTRIBUTING.md - Update repository URLs and guidelines"
echo "2. Edit .github/FUNDING.yml - Add your sponsorship links (uncomment and fill in)"
echo "3. Review .github/CODE_OF_CONDUCT.md - Usually no changes needed"
echo "4. Review .github/ISSUE_TEMPLATE/* - Customize as needed"
echo ""
echo -e "${YELLOW}Remember to customize repository-specific information!${NC}"
echo ""
echo "Find and replace suggestions:"
echo '  - "token-eater/skills-marketplace" → "token-eater/your-repo"'
echo '  - Update author names and contact info'
echo ""
echo "To commit these changes:"
echo "  git add .github/"
echo '  git commit -m "Add GitHub community health files"'
