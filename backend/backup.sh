#!/usr/bin/env bash
# SQLite 在线备份：不会锁库，WAL 模式下也能拿到一致快照。
#
# 用法：./backup.sh            -> 备份到 ./backups/app-YYYYmmdd-HHMMSS.db.gz
#       BACKUP_DIR=/mnt/x ./backup.sh
#
# 建议加进 crontab（每天 3:07）：
#   7 3 * * * /srv/quiz/deploy/backup.sh >> /var/log/quiz-backup.log 2>&1
#
# 恢复：gunzip 出 .db，docker compose cp 回容器，然后重启 app：
#   docker compose cp backups/app-xxxx.db app:/data/app.db
#   docker compose restart app

set -euo pipefail

cd "$(dirname "$0")"
OUT="${BACKUP_DIR:-./backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$OUT"

# 在容器里用 Python 的 sqlite3.backup() 做快照，避免直接 cp 正在写的文件
docker compose exec -T app python - <<'PY'
import sqlite3

src = sqlite3.connect("/data/app.db")
dst = sqlite3.connect("/tmp/snapshot.db")
with dst:
    src.backup(dst)
dst.close()
src.close()
print("snapshot ok")
PY

docker compose cp app:/tmp/snapshot.db "$OUT/app-$STAMP.db"
docker compose exec -T app rm -f /tmp/snapshot.db
gzip -f "$OUT/app-$STAMP.db"

# 顺手清掉过期备份
find "$OUT" -name 'app-*.db.gz' -mtime "+$KEEP_DAYS" -delete 2>/dev/null || true

echo "备份完成：$OUT/app-$STAMP.db.gz"
