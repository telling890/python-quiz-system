# 项目文档索引

本目录存放项目的全套文档，Word / PPT 原件与 PDF 版并存（PDF 可直接在 GitHub 预览）。

| 文档 | Word/PPT | PDF | 说明 |
| --- | --- | --- | --- |
| 需求说明书 | [1-需求说明书.docx](1-需求说明书.docx) | [PDF](pdf/1-需求说明书.pdf) | 15 条功能需求、非功能需求、数据设计、验收标准、需求追踪矩阵 |
| 设计文档 | [2-设计文档.docx](2-设计文档.docx) | [PDF](pdf/2-设计文档.pdf) | 分层架构、模块设计、判题引擎、组卷引擎、数据结构、部署 |
| 测试报告 | [3-测试报告.docx](3-测试报告.docx) | [PDF](pdf/3-测试报告.pdf) | 题库自检、组卷自检、交互/边界/打包测试与缺陷记录 |
| 答辩演示 | [4-答辩演示.pptx](4-答辩演示.pptx) | [PDF](pdf/4-答辩演示.pdf) | 18 页答辩稿 |
| 项目汇报 | [5-项目汇报.docx](5-项目汇报.docx) | [PDF](pdf/5-项目汇报.pdf) | 项目概况、建设内容、技术亮点、质量保障、展望 |

## 生成脚本

文档不是手写排版的，而是脚本生成，改完数据重新跑即可：

```bat
python docs\build_docs.py     :: 需求 / 设计 / 测试 三份 docx
python docs\build_report.py   :: 项目汇报 docx（含截图）
python docs\build_ppt.py      :: 答辩 PPT
```

导出 PDF：用任意 LibreOffice / WPS 打开后另存为 PDF，或命令行批量转换：

```bat
soffice --headless --convert-to pdf --outdir docs\pdf docs\1-需求说明书.docx
```

> 说明：脚本里的题目数、用例数直接从 `qbank.py` 统计，所以改题库后重新生成文档，
> 数字会自动更新，不会出现文档和代码对不上的情况。
