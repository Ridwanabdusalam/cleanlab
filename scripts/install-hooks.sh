#!/bin/bash

# Exit on error
set -e

echo "Installing Git hooks..."

# Create the hooks directory if it doesn't exist
mkdir -p .git/hooks

# Install pre-commit hook
cat > .git/hooks/pre-commit << 'EOL'
#!/bin/bash

# Run pre-commit checks
pre-commit run --all-files

# Capture the exit code
EXIT_CODE=$?

# If any checks failed, exit with non-zero status
if [ $EXIT_CODE -ne 0 ]; then
  echo "\nPre-commit checks failed. Please fix the issues and try again.\n"
  exit $EXIT_CODE
fi

# If all checks passed, exit with success
exit 0
EOL

# Make the pre-commit hook executable
chmod +x .git/hooks/pre-commit

# Install commit-msg hook for conventional commits
cat > .git/hooks/commit-msg << 'EOL'
#!/bin/bash

# Get the commit message file path
COMMIT_MSG_FILE=$1

# Read the commit message
COMMIT_MSG=$(cat "$COMMIT_MSG_FILE")

# Check if the commit message matches the conventional commit format
if ! echo "$COMMIT_MSG" | grep -qE '^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z]+\))?: .+' ; then
  echo "\nError: Commit message does not follow the conventional commit format.\n"
  echo "Please use the following format:\n"
  echo "  <type>(<scope>): <description>\n"
  echo "  [optional body]\n"
  echo "  [optional footer(s)]\n"
  echo "Types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert\n"
  echo "Example:\n"
  echo "  feat(auth): add login functionality\n"
  echo "  This commit adds the login functionality with email and password authentication.\n"
  echo "  Closes #123\n"
  exit 1
fi

exit 0
EOL

# Make the commit-msg hook executable
chmod +x .git/hooks/commit-msg

echo "Git hooks installed successfully!"
echo "The following hooks have been installed:"
echo "- pre-commit: Runs pre-commit checks before allowing a commit"
echo "- commit-msg: Validates commit messages against conventional commit format"
