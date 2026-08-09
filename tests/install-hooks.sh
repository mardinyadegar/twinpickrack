#!/usr/bin/env bash
# Installs the repo's tracked git hooks (.githooks/) into .git/hooks/.
# .git/hooks/ isn't versioned by git, so every fresh clone needs to run
# this once:
#
#   ./tests/install-hooks.sh
set -euo pipefail
repo_root="$(git rev-parse --show-toplevel)"
src="$repo_root/.githooks"
dest="$repo_root/.git/hooks"

for hook in "$src"/*; do
  name="$(basename "$hook")"
  cp "$hook" "$dest/$name"
  chmod +x "$dest/$name"
  echo "Installed $name -> .git/hooks/$name"
done
