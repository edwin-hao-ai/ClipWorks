#!/usr/bin/env bash
# ClipWorks 磁盘清理（默认 dry-run，--yes 才真正删除）
#
#   bash scripts/cleanup_disk.sh           # 只看会删什么，不动任何数据
#   bash scripts/cleanup_disk.sh --yes     # 执行：测试污染项目 + 孤立素材 + dangling 镜像
#   bash scripts/cleanup_disk.sh --yes --dev-cache   # 额外清 frontend/.next 与 data/e2e_audit
#
# 清理内容：
#   1) DB 中 pytest/e2e 污染项目（按标题模式匹配，KEEP_IDS 除外）+ 其素材目录
#   2) 孤立素材目录（项目已删、data/assets/<id> 残留）
#   3) Docker dangling 镜像与旧构建缓存（保留最近 2GB）
#   4) 可选：frontend/.next、data/e2e_audit 截图
set -euo pipefail
cd "$(dirname "$0")/.."

YES=0
DEV_CACHE=0
for arg in "$@"; do
  case "$arg" in
    --yes) YES=1 ;;
    --dev-cache) DEV_CACHE=1 ;;
    *) echo "未知参数: $arg（用法：--yes [--dev-cache]）"; exit 1 ;;
  esac
done

# 保留的夹具项目（标题恰好撞上测试模式，但实际是人工验证用的富数据项目）
KEEP_IDS="'fc04330d-8cc1-4dce-98d5-f431eb38aae5'"

PSQL="docker compose exec -T postgres psql -U clipworks -d clipworks -tAc"

PURGE_WHERE="(
  title IN ('Render Poll Project','Asset Upload Project','Update Composition Project',
            'Private Project','Seeded Project','New Title','Plan Project','Approve Project',
            'No Plan Project','Reject Project','Format Change Project','Unsupported Chat Project')
  OR title LIKE 'E2E %' OR title LIKE 'Test %' OR title LIKE '%Verify%' OR title LIKE 'tmp%'
) AND id NOT IN ($KEEP_IDS)"

echo '=== 1) 测试污染项目（DB）==='
$PSQL "SELECT count(*) || ' 个项目待清理' FROM projects WHERE $PURGE_WHERE;"
PURGE_IDS=$($PSQL "SELECT id FROM projects WHERE $PURGE_WHERE;")

echo '=== 2) 孤立素材目录（项目已删、目录残留）==='
LIVE_IDS=$($PSQL "SELECT id FROM projects;")
ORPHAN_DIRS=()
for d in data/assets/*/; do
  id=$(basename "$d")
  if ! grep -qx "$id" <<< "$LIVE_IDS" && ! grep -qx "$id" <<< "$PURGE_IDS"; then
    ORPHAN_DIRS+=("$d")
  fi
done
if [ "${#ORPHAN_DIRS[@]}" -gt 0 ]; then
  echo "${#ORPHAN_DIRS[@]} 个孤立目录，共 $(du -sch "${ORPHAN_DIRS[@]}" | tail -1 | cut -f1)"
else
  echo "0 个孤立目录"
fi

ASSET_BYTES=0
for id in $PURGE_IDS; do
  if [ -d "data/assets/$id" ]; then
    ASSET_BYTES=$((ASSET_BYTES + $(du -sk "data/assets/$id" | cut -f1)))
  fi
done
echo "待清理项目素材目录: $((ASSET_BYTES / 1024)) MB"

echo '=== 3) Docker ==='
docker system df

if [ "$YES" -ne 1 ]; then
  echo
  echo '（dry-run，未删除任何数据。加 --yes 执行。）'
  exit 0
fi

echo
echo '>>> 执行清理...'
# 按外键依赖顺序删除（clips -> tracks -> render_jobs/media_assets/scripts -> compositions -> projects）
$PSQL "
DELETE FROM clips WHERE track_id IN (
  SELECT t.id FROM tracks t JOIN compositions c ON t.composition_id = c.id
  WHERE c.project_id IN (SELECT id FROM projects WHERE $PURGE_WHERE));
DELETE FROM tracks WHERE composition_id IN (
  SELECT id FROM compositions WHERE project_id IN (SELECT id FROM projects WHERE $PURGE_WHERE));
DELETE FROM render_jobs  WHERE project_id IN (SELECT id FROM projects WHERE $PURGE_WHERE);
DELETE FROM media_assets WHERE project_id IN (SELECT id FROM projects WHERE $PURGE_WHERE);
DELETE FROM scripts      WHERE project_id IN (SELECT id FROM projects WHERE $PURGE_WHERE);
DELETE FROM compositions WHERE project_id IN (SELECT id FROM projects WHERE $PURGE_WHERE);
DELETE FROM projects     WHERE $PURGE_WHERE;
" > /dev/null
# VACUUM 不能在事务块内执行，单独一条命令
$PSQL "VACUUM;" > /dev/null
echo "DB 污染项目已清理"

for id in $PURGE_IDS; do rm -rf "data/assets/$id"; done
[ "${#ORPHAN_DIRS[@]}" -gt 0 ] && rm -rf "${ORPHAN_DIRS[@]}"
echo "素材目录已清理"

docker image prune -f > /dev/null
docker builder prune -f --keep-storage 2GB > /dev/null 2>&1 || true
echo "dangling 镜像与旧构建缓存已清理"

if [ "$DEV_CACHE" -eq 1 ]; then
  rm -rf frontend/.next data/e2e_audit
  echo "frontend/.next 与 data/e2e_audit 已清理（下次访问会自动重建 .next）"
fi

echo
echo '>>> 清理后：'
du -sh data/assets
$PSQL "SELECT '剩余项目: ' || count(*) FROM projects;"
docker system df
