# Ops Backup Guide (Postgres version mismatch)

Error seen:
\`\`\`
server version: 17.6; pg_dump version: 14.13
\`\`\`

## Option A — Homebrew (macOS)
\`\`\`bash
brew install postgresql@17
echo 'export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"' >> ~/.zshrc
exec $SHELL -l
pg_dump --version  # should show 17.x
\`\`\`

## Option B — Docker
\`\`\`bash
docker run --rm -e PGPASSWORD="$PGPASSWORD" -v $(pwd):/dump postgres:17   pg_dump -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -F c -f /dump/pre-upgrade.dump -d postgres
\`\`\`

## Test restore
\`\`\`bash
pg_restore --list pre-upgrade.dump | head
\`\`\`
