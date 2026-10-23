# 参与开发

这个项目是一个课程作业性质的桌面刷题程序，欢迎提问题、提改进建议。

## 环境

- Windows 10 / 11
- Python 3.8+（开发和 CI 都覆盖 3.8 与 3.11）
- 运行程序本身**不需要任何第三方库**，只用标准库 + Tkinter

## 本地跑起来

```bat
python main.py
```

## 改了题库之后

题库按章节拆成独立模块（`bank_ch3.py` / `bank_ch4.py` / `bank_ch5.py` / `bank_extra.py` / `bank_algo.py`），
由 `qbank.py` 汇总。新增题目时：

1. 在对应 `bank_*.py` 里加一个字典，字段参考现有题目：
   `id / chapter / no / title / topic / level / desc / hint / ref / cases / explain`（拓展题可加 `source`）
2. 用例里 `stdin` 是喂给 `input()` 的内容，`stdout` 是期望输出；
   需要保留行首空格的图形题（金字塔、菱形）在用例里加 `"raw": True`
3. 跑自检，确保你的参考答案能通过自己写的用例：

```bat
python selftest.py
```

## 提交前必做

```bat
python selftest.py     :: 题库自检：参考答案跑自己的用例
python _test_exam.py   :: 组卷系统自检：随机性、覆盖、评分、限时
```

CI 会在推送时自动跑这两个脚本（Python 3.8 和 3.11 两套），并额外验证一次打包。

## 重新打包 exe

```bat
python -m pip install --target pylibs -r requirements-build.txt
python build.py
```

产物在 `dist\Python刷题系统\`，同时会生成 `dist\Python刷题系统-便携版.zip`。

> **不要改回 `--onefile`**：单文件模式启动要解压到 `%TEMP%`，部分机器上会直接失败
> （`INTERNAL ERROR: cannot create temporary directory!`）。目录版没有这个问题。

## 代码风格

- 4 空格缩进，UTF-8，LF 换行（`.editorconfig` 已配好）
- 注释和界面文案用中文
- 不引入第三方运行期依赖；新增开发期依赖请写进 `requirements-build.txt`

## 提交信息

用 `类型: 说明` 的格式，例如：

```
feat: 统计页加历次组卷得分趋势图
fix: 判题超时后按钮状态未恢复
docs: 补充目录页码
```
