#!/bin/bash
# ============================================================
#  一键推送脚本（实时同步 GitHub）  -  Git Bash 版
#  用法：
#    ./push.sh                -> 自动 add + commit(默认消息) + push
#    ./push.sh "修复登录bug"   -> 指定提交说明
#    ./push.sh --force "说明"  -> 强制推送，覆盖远端历史（替换远端项目时用）
#  说明：国内网络默认走本地代理 127.0.0.1:7897（Clash 混合端口），
#       如无代理可删除下面三行或改成直连。
# ============================================================
export HTTPS_PROXY=http://127.0.0.1:7897
export HTTP_PROXY=http://127.0.0.1:7897
export ALL_PROXY=http://127.0.0.1:7897
cd "$(dirname "$0")"

FORCE=""
case "$1" in
  --force|-f) FORCE="--force"; shift ;;
esac

MSG="${1:-auto push $(date '+%Y-%m-%d %H:%M')}"
git add -A
git commit -m "$MSG" || echo "[提示] 没有需要提交的更改。"
git push origin main $FORCE
echo
echo "===== 推送完成 ====="
