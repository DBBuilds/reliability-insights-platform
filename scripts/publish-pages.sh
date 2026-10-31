#!/usr/bin/env bash
# Publish a built site into one folder of the gh-pages branch, or remove that folder, then push.
#   publish-pages.sh . frontend/dist        the main demo, at the site root (keeps pr-* folders)
#   publish-pages.sh pr-12 frontend/dist    a pull request preview
#   publish-pages.sh pr-12                  remove that preview
# Run from a checkout whose `origin` the caller can push to (CI: the default GITHUB_TOKEN).
set -euo pipefail
folder=$1 built=${2:-}
action=$([ -n "$built" ] && echo Publish || echo Remove)
work=$(mktemp -d)
trap 'git worktree remove --force "$work" 2>/dev/null || true' EXIT

if git fetch --quiet --depth 1 origin gh-pages 2>/dev/null; then
  git worktree add --quiet -B gh-pages "$work" FETCH_HEAD
else
  git worktree add --quiet --orphan -b gh-pages "$work"  # first publish
fi

if [ -z "$built" ]; then
  rm -rf "${work:?}/$folder"
elif [ "$folder" = . ]; then
  rsync -a --delete --exclude '/pr-*/' --exclude /.git "$built/" "$work/"
else
  mkdir -p "$work/$folder" && rsync -a --delete "$built/" "$work/$folder/"
fi
touch "$work/.nojekyll"  # serve files as built; skip GitHub's Jekyll step

git -C "$work" add --all
if git -C "$work" diff --cached --quiet; then
  echo "gh-pages: no changes for $folder"
  exit 0
fi
git -C "$work" -c user.name="github-actions[bot]" -c user.email="41898282+github-actions[bot]@users.noreply.github.com" \
  commit --quiet -m "$action $folder from $(git rev-parse --short HEAD)"
git -C "$work" push --quiet origin gh-pages
echo "gh-pages: $action $folder"
