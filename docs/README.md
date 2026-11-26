# 项目文档索引

本目录存放项目的全套文档，Word / PPT 原件与 PDF 版并存（PDF 可直接在 GitHub 预览）。

| 文档 | Word/PPT | PDF | 说明 |
| --- | --- | --- | --- |
| 需求说明书 | [1-需求说明书.docx](1-需求说明书.docx) | [PDF](pdf/1-需求说明书.pdf) | 15 条功能需求、非功能需求、数据设计、验收标准、需求追踪矩阵 |
| 设计文档 | [2-设计文档.docx](2-设计文档.docx) | [PDF](pdf/2-设计文档.pdf) | 分层架构、模块设计、判题引擎、组卷引擎、数据结构、部署 |
| 测试报告 | [3-测试报告.docx](3-测试报告.docx) | [PDF](pdf/3-测试报告.pdf) | 题库自检、组卷自检、交互/边界/打包测试与缺陷记录 |
| 答辩演示 | [4-答辩演示.pptx](4-答辩演示.pptx) | [PDF](pdf/4-答辩演示.pdf) | 25 页答辩稿（v1.2 增补纯静态版、学习热力图、考点覆盖各一页） |
| 项目汇报 | [5-项目汇报.docx](5-项目汇报.docx) | [PDF](pdf/5-项目汇报.pdf) | 项目概况、建设内容、技术亮点、质量保障、展望 |

## 比赛提交材料（针对一门薄弱课程的学习软件）

| 文档 | Word | PDF | 对应比赛要求 |
| --- | --- | --- | --- |
| 课程学习分析 | [6-课程学习分析.docx](6-课程学习分析.docx) | [PDF](pdf/6-课程学习分析.pdf) | (2) 课程学习分析 |
| 学习策略分析 | [7-学习策略分析.docx](7-学习策略分析.docx) | [PDF](pdf/7-学习策略分析.pdf) | (3) 学习策略分析文档 |
| 解说视频脚本 | [8-解说视频脚本.docx](8-解说视频脚本.docx) | [PDF](pdf/8-解说视频脚本.pdf) | (4) 软件解说视频（分镜 + 逐字稿 + 字幕） |
| 提交清单与作品说明 | [9-提交清单与作品说明.docx](9-提交清单与作品说明.docx) | [PDF](pdf/9-提交清单与作品说明.pdf) | 六项材料对照、三分钟评审路径、自查清单 |

> 这四份由 `python docs\build_submission.py` 生成，排版工具与 1~5 号文档共用（`build_docs.py`），
> 字体、页边距、表格样式完全一致；题库数字（题数 / 用例数）同样是实时统计。
> 源码包用 `python _pack_submission.py` 生成（默认排除 node_modules / pylibs / dist / .git）。

## 生成脚本

文档不是手写排版的，而是脚本生成，改完数据重新跑即可：

```bat
python docs\build_docs.py         :: 需求 / 设计 / 测试 三份 docx
python docs\build_report.py       :: 项目汇报 docx（含截图）
python docs\build_ppt.py          :: 答辩 PPT
python docs\build_submission.py   :: 课程学习分析 / 学习策略 / 视频脚本 / 提交清单
python _pack_submission.py        :: 比赛提交用的源码 zip
```

导出 PDF：用任意 LibreOffice / WPS 打开后另存为 PDF，或命令行批量转换：

```bat
soffice --headless --convert-to pdf --outdir docs\pdf docs\1-需求说明书.docx
```

> 说明：脚本里的题目数、用例数直接从 `qbank.py` 统计，所以改题库后重新生成文档，
> 数字会自动更新，不会出现文档和代码对不上的情况。
