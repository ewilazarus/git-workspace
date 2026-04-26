#!/usr/bin/env bash
# Bootstrap a throwaway git-workspace playground for the VHS demo.
# Idempotent: wipes any previous state and rebuilds from scratch.
#
# Outputs (sourced or executed):
#   GW_DEMO_PLAYGROUND   absolute path to the playground workspace root
#   GW_DEMO_SHIM         directory prepended to PATH containing a `git-workspace` shim
#                        that runs the dev build from the source tree
set -euo pipefail

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$DEMO_DIR/../.." && pwd)"
PLAYGROUND="$HOME/git-workspace-demo"
TEMPLATE="$DEMO_DIR/workspace"

echo "[setup] repo root:  $REPO_ROOT"
echo "[setup] playground: $PLAYGROUND"

# Wipe previous state.
rm -rf "$PLAYGROUND"
mkdir -p "$PLAYGROUND"

# Shim so `git workspace ...` invokes the dev build from the source tree.
SHIM_DIR="$PLAYGROUND/.shim"
mkdir -p "$SHIM_DIR"
cat > "$SHIM_DIR/git-workspace" <<EOF
#!/usr/bin/env bash
exec uv run --quiet --project "$REPO_ROOT" git-workspace "\$@"
EOF
chmod +x "$SHIM_DIR/git-workspace"

# Make the shim available for the rest of this script.
export PATH="$SHIM_DIR:$PATH"

# Initialize the workspace.
cd "$PLAYGROUND"
git-workspace init >/dev/null

# Replace the default `.workspace/` contents with our demo template.
rm -rf "$PLAYGROUND/.workspace/bin" "$PLAYGROUND/.workspace/assets"
cp "$TEMPLATE/manifest.toml" "$PLAYGROUND/.workspace/manifest.toml"
cp -R "$TEMPLATE/bin" "$PLAYGROUND/.workspace/bin"
cp -R "$TEMPLATE/assets" "$PLAYGROUND/.workspace/assets"

chmod +x "$PLAYGROUND/.workspace/bin"/*

# Orphaned bin script — left over from a renamed hook. `git workspace doctor`
# will flag it and `--fix --yes` will clean it up.
cat > "$PLAYGROUND/.workspace/bin/old_install" <<'EOF'
#!/bin/sh
echo "legacy install script — no longer referenced by any hook"
EOF
chmod +x "$PLAYGROUND/.workspace/bin/old_install"

# Seed a tiny project so fingerprint files exist and `git status` has something
# meaningful to show inside a worktree.
mkdir -p "$PLAYGROUND/.workspace/seed"
cat > "$PLAYGROUND/.workspace/seed/README.md" <<'EOF'
# demo project

A tiny project used by the git-workspace VHS demo.
EOF
cat > "$PLAYGROUND/.workspace/seed/package.json" <<'EOF'
{
  "name": "git-workspace-demo",
  "version": "0.0.1",
  "private": true
}
EOF

# Bootstrap the main worktree (detached so the demo's first hook firing is
# the visible one on `up feat/demo`).
git-workspace up main -d >/dev/null

# Place the seed files inside the main worktree and commit them so subsequent
# branches inherit a non-empty tree.
cp "$PLAYGROUND/.workspace/seed/README.md" "$PLAYGROUND/main/README.md"
cp "$PLAYGROUND/.workspace/seed/package.json" "$PLAYGROUND/main/package.json"
(
  cd "$PLAYGROUND/main"
  git add README.md package.json
  git -c user.email=demo@example.com -c user.name="git-workspace demo" \
      commit -q -m "initial project"
)

# Export for the tape (when sourced).
export GW_DEMO_PLAYGROUND="$PLAYGROUND"
export GW_DEMO_SHIM="$SHIM_DIR"

echo "[setup] ready."
