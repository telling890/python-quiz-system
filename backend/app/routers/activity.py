# -*- coding: utf-8 -*-
"""打卡统计接口：把判题记录按天聚合，给统计页的「学习热力图」用。

为什么不在前端算：前端只拿得到最近 50 条提交（`/submissions?limit=`），
而热力图要看一整年，只能在服务端按用户聚合。

日期按客户端传来的时区偏移算——北京时间凌晨 1 点做的题，按 UTC 会算到前一天，
热力图上就会看到「昨天有记录、今天空着」，很别扭。
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from ..db import get_db
from ..errors import ok
from ..models import Submission
from ..security import current_user

router = APIRouter(tags=["stats"])

MAX_DAYS = 366
DEFAULT_DAYS = 182
# 时区偏移的合法范围：-12:00 ~ +14:00（分钟）
MIN_TZ = -720
MAX_TZ = 840


def local_date(iso, offset_minutes):
    """把 UTC 时间串换算成用户本地日期；格式不对返回 None。"""
    try:
        stamp = datetime.fromisoformat(str(iso))
    except (TypeError, ValueError, AttributeError):
        return None
    if stamp.tzinfo is None:                    # 老数据可能没带时区，按 UTC 处理
        stamp = stamp.replace(tzinfo=timezone.utc)
    return (stamp + timedelta(minutes=offset_minutes)).date()


def today_of(offset_minutes):
    return (datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)).date()


def current_streak(counts, today):
    """当前连续打卡天数。

    今天还没做题、但昨天做了，连续记录先算「活着」（和 GitHub 的判定一致），
    免得早上打开统计页就看到「连续归零」。
    """
    if counts.get(today, 0) > 0:
        cursor = today
    elif counts.get(today - timedelta(days=1), 0) > 0:
        cursor = today - timedelta(days=1)
    else:
        return 0
    days = 0
    while counts.get(cursor, 0) > 0:
        days += 1
        cursor -= timedelta(days=1)
    return days


def best_streak(counts):
    """窗口内最长连续打卡，返回 (天数, 结束日期)。"""
    best = 0
    best_end = None
    run = 0
    previous = None
    for day in sorted(counts):
        run = run + 1 if previous is not None and day - previous == timedelta(days=1) else 1
        if run > best:
            best, best_end = run, day
        previous = day
    return best, best_end


@router.get("/activity")
def activity(days: int = Query(default=DEFAULT_DAYS, ge=7, le=MAX_DAYS),
             tz: int = Query(default=0, ge=MIN_TZ, le=MAX_TZ,
                             description="客户端时区偏移（分钟），东八区传 480"),
             user=Depends(current_user), db=Depends(get_db)):
    """最近 N 天的每日判题次数 + 连续打卡天数。"""
    today = today_of(tz)
    start = today - timedelta(days=days - 1)
    # created_at 是 ISO 字符串，同格式下可以按前缀比较；多查一天防时区边界
    cutoff = (start - timedelta(days=1)).isoformat()

    rows = (db.query(Submission.created_at)
            .filter(Submission.user_id == user.id,
                    Submission.created_at >= cutoff)
            .all())

    counts = {}
    for (created_at,) in rows:
        day = local_date(created_at, tz)
        if day is None or day < start or day > today:
            continue
        counts[day] = counts.get(day, 0) + 1

    points = [{"date": (start + timedelta(days=i)).isoformat(),
               "count": counts.get(start + timedelta(days=i), 0)}
              for i in range(days)]

    best, best_end = best_streak(counts)
    return ok({
        "days": points,
        "today": today.isoformat(),
        "today_count": counts.get(today, 0),
        "total": sum(counts.values()),
        "active_days": len(counts),
        "streak": current_streak(counts, today),
        "best_streak": best,
        "best_streak_end": best_end.isoformat() if best_end else "",
        "timezone_minutes": tz,
    })
