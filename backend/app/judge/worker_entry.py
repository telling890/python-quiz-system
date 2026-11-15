# -*- coding: utf-8 -*-
"""独立判题 worker：当 API 和判题要分进程 / 分容器部署时用这个入口。

    py -3.10 -m app.judge.worker

API 进程里默认也会起同样数量的判题线程（QUIZ_JUDGE_WORKERS），
两者可以同时存在：提交是「数据库认领」的，不会被重复执行。
"""

import logging
import time

from ..config import get_settings
from ..db import init_db
from .worker import get_service


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = get_settings()
    init_db(seed=settings.seed_on_start)
    service = get_service()
    service.start()
    logging.getLogger("quiz.worker").info("独立判题 worker 已启动：%s 线程", service.workers)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        service.stop()


if __name__ == "__main__":
    main()
