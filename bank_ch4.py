# -*- coding: utf-8 -*-
"""第 4 章 序列 · 实验内容（4.1 实验指导）

教材把实验内容分成两块：
  （一）操作部分：1 列表、2 元组、3 字典、4 列表与字典嵌套、5 集合（共 36 个小操作）
  （二）编程部分：8 道编程题

小操作本身没有输入输出，这里按考点合并成可判题的题目：
固定初始数据、规定输出格式，学习者写完整片段即可提交。
"""

CHAPTER = "第4章 序列"


def _c(stdin, expect):
    return {"stdin": stdin, "expect": expect}


QUESTIONS = [
    {
        "id": "4-01",
        "chapter": CHAPTER,
        "no": 1,
        "title": "列表增删改查综合",
        "topic": "列表方法 / insert / extend / index",
        "level": 2,
        "desc": (
            "从 names = [\"Xiaoming\", \"Panpan\", \"Dongdong\"] 出发，依次完成：\n"
            "1. 在 Dongdong 前面插入 \"Yueyue\"；\n"
            "2. 把 Dongdong 改成中文名 \"东东\"；\n"
            "3. 在 Panpan 后面插入子列表 [\"Mingming\", \"Xiaoyun\"]；\n"
            "4. 输出 Panpan 在列表中的索引；\n"
            "5. 把 [1, 2, 3, 4, 5] 合并到 names 末尾；\n"
            "最后输出 names 的完整内容和 Panpan 的索引（先列表后索引，各一行）。"
        ),
        "hint": "insert(i, x) 按下标插入；改元素直接赋值 names[i] = ...；末尾合并用 extend 或 +=；index 查下标。",
        "ref": """names = ["Xiaoming", "Panpan", "Dongdong"]

names.insert(2, "Yueyue")
names[3] = "东东"
names.insert(2, ["Mingming", "Xiaoyun"])
panpan_index = names.index("Panpan")
names.extend([1, 2, 3, 4, 5])

print(names)
print(panpan_index)
""",
        "cases": [
            _c("",
               "['Xiaoming', 'Panpan', ['Mingming', 'Xiaoyun'], 'Yueyue', '东东', 1, 2, 3, 4, 5]\n1"),
        ],
        "explain": "insert 会在指定下标前插入，原位置及之后的元素整体后移；所以插 Yueyue 时下标是 2（Dongdong 的原位置）。\n"
                   "插完 Yueyue 后 Dongdong 的下标变成 3，改中文名要用新下标。\n"
                   "extend 把可迭代对象的元素逐个追加；如果写 names.append([1,2,3,4,5]) 会变成嵌套列表。",
    },
    {
        "id": "4-02",
        "chapter": CHAPTER,
        "no": 2,
        "title": "列表切片三种取法",
        "topic": "切片 / 步长 / 负索引",
        "level": 1,
        "desc": (
            "从 nums = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] 出发，分三行输出：\n"
            "1. 下标 3 到 6 的元素（含两端）；\n"
            "2. 下标 2 到 8 之间、步长为 2 的元素；\n"
            "3. 最后 4 个元素。\n"
            "每行直接打印对应的列表。"
        ),
        "hint": "切片语法 seq[start:stop:step]，stop 不含在内；最后 n 个用 seq[-n:]。",
        "ref": """nums = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
print(nums[3:7])
print(nums[2:9:2])
print(nums[-4:])
""",
        "cases": [_c("", "[3, 4, 5, 6]\n[2, 4, 6, 8]\n[6, 7, 8, 9]")],
        "explain": "切片的 stop 是开区间：要取到下标 6，得写 nums[3:7]。\n"
                   "步长 2 时 nums[2:9:2] 取 2、4、6、8；写成 nums[2:8:2] 结果一样，因为 8 本来就取不到下一个。\n"
                   "负索引 nums[-4:] 表示从倒数第 4 个取到末尾。",
    },
    {
        "id": "4-03",
        "chapter": CHAPTER,
        "no": 3,
        "title": "遍历列表并按索引修改",
        "topic": "enumerate / 原地修改",
        "level": 2,
        "desc": (
            "从 names = [\"Xiaoming\", \"Panpan\", \"Yueyue\", \"Dongdong\"] 出发：\n"
            "1. 遍历输出每个元素的索引和元素，格式：<索引> <元素>（共 4 行）；\n"
            "2. 遍历时把索引为偶数的元素改成 -1；\n"
            "最后输出修改后的列表。"
        ),
        "hint": "用 enumerate 同时拿到索引和元素；改列表要按下标赋值 names[i] = -1。",
        "ref": """names = ["Xiaoming", "Panpan", "Yueyue", "Dongdong"]

for i, name in enumerate(names):
    print(i, name)

for i in range(len(names)):
    if i % 2 == 0:
        names[i] = -1

print(names)
""",
        "cases": [_c("", "0 Xiaoming\n1 Panpan\n2 Yueyue\n3 Dongdong\n[-1, 'Panpan', -1, 'Dongdong']")],
        "explain": "enumerate 同时给出下标和元素，比 range(len(...)) 再取元素更直观。\n"
                   "遍历时修改列表要小心：for name in names 拿到的是元素副本，改 name 不影响列表；必须用下标。\n"
                   "同理，边遍历边删除（remove/del）会导致漏项，通常改为倒序或先记下标再删。",
    },
    {
        "id": "4-04",
        "chapter": CHAPTER,
        "no": 4,
        "title": "元组的基本查询",
        "topic": "元组 / count / index / len",
        "level": 1,
        "desc": (
            "已知 grades = (87, 100, 96, 77, 69, 83, 91, 77, 63, 85)，依次输出：\n"
            "1. 第 2 个元素；\n"
            "2. 第 1 个到第 5 个元素（切片，输出元组）；\n"
            "3. 77 出现的次数；\n"
            "4. 100 分的索引；\n"
            "5. 元组的长度。\n"
            "每个结果占一行。"
        ),
        "hint": "元组用下标和切片取值（下标从 0 开始）；count 统计次数、index 找下标、len 求长度。",
        "ref": """grades = (87, 100, 96, 77, 69, 83, 91, 77, 63, 85)
print(grades[1])
print(grades[0:5])
print(grades.count(77))
print(grades.index(100))
print(len(grades))
""",
        "cases": [_c("", "100\n(87, 100, 96, 77, 69)\n2\n1\n10")],
        "explain": "「第 2 个元素」是 grades[1]（下标从 0 开始），这是最常见的差一错误。\n"
                   "切片 grades[0:5] 取前 5 个，类型仍是元组，打印时带圆括号。\n"
                   "元组不可修改，所以没有 append、remove 这些方法，只能查。",
    },
    {
        "id": "4-05",
        "chapter": CHAPTER,
        "no": 5,
        "title": "元组与列表互转、元组合并",
        "topic": "list / tuple / 类型转换",
        "level": 1,
        "desc": (
            "已知 grades = (87, 100, 96, 77, 69, 83, 91, 77, 63, 85)、grades_other = (34, 67)：\n"
            "1. 用 list() 把 grades 转成列表 list_grades，输出它的最后 1 个元素；\n"
            "2. 用 tuple() 把 list_grades 转回元组 tup_grades，输出它的长度；\n"
            "3. 合并 grades 与 grades_other，输出合并后的最后 2 个元素（元组）。"
        ),
        "hint": "list(tuple) 与 tuple(list) 互转；元组相加得到新元组；取最后 n 个用 [-n:]。",
        "ref": """grades = (87, 100, 96, 77, 69, 83, 91, 77, 63, 85)
grades_other = (34, 67)

list_grades = list(grades)
print(list_grades[-1])

tup_grades = tuple(list_grades)
print(len(tup_grades))

merged = grades + grades_other
print(merged[-2:])
""",
        "cases": [_c("", "85\n10\n(34, 67)")],
        "explain": "list() 和 tuple() 互转会生成新对象，原对象不变。\n"
                   "tuple + tuple 得到新元组；写成 grades + list 会抛 TypeError，类型必须一致。\n"
                   "合并后长度 12，最后两个就是 grades_other 的两个元素。",
    },
    {
        "id": "4-06",
        "chapter": CHAPTER,
        "no": 6,
        "title": "字典的遍历、增删与安全取值",
        "topic": "字典 / keys / get / pop",
        "level": 2,
        "desc": (
            "已知 dic = {\"k1\": \"v1\", \"k2\": \"v2\", \"k3\": \"v3\"}，按顺序完成并输出：\n"
            "1. 输出所有键（用空格连接）；\n"
            "2. 输出所有值（用空格连接）；\n"
            "3. 遍历输出每个键值对，格式：<键> <值>（3 行）；\n"
            "4. 增加 \"k4\": \"v4\" 后输出整个字典；\n"
            "5. 删除 \"k1\" 后输出整个字典；\n"
            "6. 删除 \"k5\"（不存在），输出删除结果（不报错，得到 None）；\n"
            "7. 输出 \"k2\" 对应的值；\n"
            "8. 输出 \"k6\" 对应的值（不存在时返回 None）。"
        ),
        "hint": "keys()/values()/items() 分别取键、值、键值对；删除用 pop(key, 默认值) 最安全。",
        "ref": """dic = {"k1": "v1", "k2": "v2", "k3": "v3"}

print(" ".join(dic.keys()))
print(" ".join(dic.values()))
for k, v in dic.items():
    print(k, v)

dic["k4"] = "v4"
print(dic)

del dic["k1"]
print(dic)

print(dic.pop("k5", None))
print(dic.get("k2"))
print(dic.get("k6"))
""",
        "cases": [
            _c("",
               "k1 k2 k3\n"
               "v1 v2 v3\n"
               "k1 v1\n"
               "k2 v2\n"
               "k3 v3\n"
               "{'k1': 'v1', 'k2': 'v2', 'k3': 'v3', 'k4': 'v4'}\n"
               "{'k2': 'v2', 'k3': 'v3', 'k4': 'v4'}\n"
               "None\n"
               "v2\n"
               "None"),
        ],
        "explain": "Python 3.7 起字典保持插入顺序，所以键值输出顺序是稳定的。\n"
                   "del dic['k5'] 会抛 KeyError；pop('k5', None) 或 get('k6') 在键不存在时返回 None，"
                   "这就是「不报错」的写法。\n"
                   "注意 get 只能取值、不能删除；pop 取走并删除。",
    },
    {
        "id": "4-07",
        "chapter": CHAPTER,
        "no": 7,
        "title": "嵌套结构中的元素修改",
        "topic": "嵌套列表 / 字典 / 下标定位",
        "level": 3,
        "desc": (
            "已知 a_list = [\"n\", [\"abc\", 30, {\"k1\": [\"bb\", \"5\", \"1\"]}], 67, \"mn\"]：\n"
            "1. 把嵌套列表里的 \"bb\" 改成大写 \"BB\"；\n"
            "2. 把嵌套列表里的字符串 \"5\" 改成数字 100；\n"
            "最后输出整个 a_list。"
        ),
        "hint": "一层层下标定位：a_list[1] 是子列表，[2] 是字典，['k1'] 是字符串列表，再按下标改。",
        "ref": """a_list = ["n", ["abc", 30, {"k1": ["bb", "5", "1"]}], 67, "mn"]

a_list[1][2]["k1"][0] = "BB"
a_list[1][2]["k1"][1] = 100

print(a_list)
""",
        "cases": [_c("", "['n', ['abc', 30, {'k1': ['BB', 100, '1']}], 67, 'mn']")],
        "explain": "嵌套结构只能「逐层剥开」：先取到最内层的列表，再按下标赋值。\n"
                   "如果只写 a_list[1][2]['k1'][0].upper()，结果不会写回原列表——字符串不可变，必须重新赋值。\n"
                   "第二问要把 \"5\" 改成 100（int），注意不是字符串 \"100\"。",
    },
    {
        "id": "4-08",
        "chapter": CHAPTER,
        "no": 8,
        "title": "集合运算（领导与教授）",
        "topic": "集合 / 交并差 / 对称差",
        "level": 2,
        "desc": (
            "某高校中，学院领导包括张老师、王老师、程老师；教授包括张老师、王老师、刘老师、马老师。\n"
            "按顺序输出（集合结果按升序排列、用空格连接）：\n"
            "1. 既是学院领导又是教授的人；\n"
            "2. 是教授但不是学院领导的人；\n"
            "3. 是学院领导但不是教授的人；\n"
            "4. 刘老师是否是学院领导（True/False）；\n"
            "5. 只担任一职的人；\n"
            "6. 学院领导和教授共有几人。"
        ),
        "hint": "交集 &、差集 -、对称差 ^；集合无序，输出前用 sorted() 排序才能得到稳定结果。",
        "ref": """leaders = {"张老师", "王老师", "程老师"}
professors = {"张老师", "王老师", "刘老师", "马老师"}

print(" ".join(sorted(leaders & professors)))
print(" ".join(sorted(professors - leaders)))
print(" ".join(sorted(leaders - professors)))
print("刘老师" in leaders)
print(" ".join(sorted(leaders ^ professors)))
print(len(leaders | professors))
""",
        "cases": [
            _c("", "张老师 王老师\n刘老师 马老师\n程老师\nFalse\n刘老师 程老师 马老师\n5"),
        ],
        "explain": "& 交集、| 并集、- 差集、^ 对称差（只属于其中一个集合）。\n"
                   "集合本身无序，直接打印顺序不确定，所以统一 sorted() 后再输出，判题才稳定。\n"
                   "共有几人用并集的长度：3 + 4 - 2 = 5。\n"
                   "注意 sorted 对中文是按 Unicode 码位排序：刘(5218) < 程(7A0B) < 马(9A6C)。",
    },
    {
        "id": "4-09",
        "chapter": CHAPTER,
        "no": 9,
        "title": "学生信息列表遍历",
        "topic": "字典列表 / 遍历",
        "level": 1,
        "desc": (
            "设计 3 个字典，每个保存一个学生的 name 和 id，把它们放进列表 students，遍历输出每个学生的信息。\n"
            "数据：张三/1001、李四/1002、王五/1003。\n"
            "输出格式：<姓名> <学号>（每行一个）"
        ),
        "hint": "先建三个字典，再放进列表；遍历列表，用 s[\"name\"]、s[\"id\"] 取值。",
        "ref": """students = [
    {"name": "张三", "id": 1001},
    {"name": "李四", "id": 1002},
    {"name": "王五", "id": 1003},
]

for s in students:
    print(s["name"], s["id"])
""",
        "cases": [_c("", "张三 1001\n李四 1002\n王五 1003")],
        "explain": "列表里存字典是「记录集合」最常见的组织方式，每条记录的字段固定。\n"
                   "遍历时 s 是字典，取值用 s[\"name\"]；也可以用 s.get() 设默认值。\n"
                   "如果字段很多，可以用 for k, v in s.items() 遍历字段。",
    },
    {
        "id": "4-10",
        "chapter": CHAPTER,
        "no": 10,
        "title": "月份转季度",
        "topic": "列表索引 / if-elif",
        "level": 1,
        "desc": (
            "输入一个月份（1-12 的整数），输出它对应的季度：第一季度、第二季度、第三季度或第四季度。\n"
            "月份不在 1-12 范围内时输出：月份不合法"
        ),
        "hint": "可以 if-elif 按区间判断，也可以用列表存 12 个月份对应的季度再按下标取。",
        "ref": """month = int(input())
if month < 1 or month > 12:
    print("月份不合法")
else:
    print(["第一季度", "第二季度", "第三季度", "第四季度"][(month - 1) // 3])
""",
        "cases": [_c("3", "第一季度"), _c("5", "第二季度"), _c("12", "第四季度"), _c("13", "月份不合法")],
        "explain": "(month - 1) // 3 把 1-3 映射成 0、4-6 映射成 1……正好是季度的下标。\n"
                   "列表索引法比 if-elif 链更短，也更容易扩展（比如按月份查天数）。\n"
                   "注意先判断范围，否则 13 会算出下标 4 并抛 IndexError。",
    },
    {
        "id": "4-11",
        "chapter": CHAPTER,
        "no": 11,
        "title": "用户名密码登录（各 3 次机会）",
        "topic": "循环 / 字典 / 交互流程",
        "level": 3,
        "desc": (
            "用户信息事先存在字典里：admin/123456、tom/888888。\n"
            "先输入用户名，不存在输出「用户名不存在」并重新输入，最多 3 次；\n"
            "用户名正确后再输入密码，错误输出「密码错误」并重新输入，最多 3 次；\n"
            "登录成功输出「登录成功」；任一环节 3 次都失败输出「登录失败」。"
        ),
        "hint": "用两个 for-else：外层试用户名、内层试密码；成功就 break，整轮结束时用 else 输出失败。",
        "ref": """users = {"admin": "123456", "tom": "888888"}

for i in range(3):
    user = input()
    if user in users:
        break
    print("用户名不存在")
else:
    print("登录失败")
    raise SystemExit

for j in range(3):
    pwd = input()
    if pwd == users[user]:
        print("登录成功")
        break
    print("密码错误")
else:
    print("登录失败")
""",
        "cases": [
            _c("admin\n123456\n", "登录成功"),
            _c("root\ntom\n888888\n", "用户名不存在\n登录成功"),
            _c("root\nxx\nyy\n", "用户名不存在\n用户名不存在\n用户名不存在\n登录失败"),
            _c("admin\n111\n222\n123456\n", "密码错误\n密码错误\n登录成功"),
        ],
        "explain": "两层 for-else 分别处理「三次用户名都不对」和「三次密码都不对」。\n"
                   "用户名通过后，循环变量 user 仍然有效，内层可以直接用 users[user] 取密码。\n"
                   "真实系统要存密码哈希、限制频率；这里只练流程控制。",
    },
    {
        "id": "4-12",
        "chapter": CHAPTER,
        "no": 12,
        "title": "找出相加等于 9 的元素组合",
        "topic": "嵌套循环 / 组合",
        "level": 2,
        "desc": (
            "已知 nums = [3, 6, 10, 14, 2, 7]，找出所有「两个元素相加等于 9」的组合并输出。\n"
            "输出格式：(a, b)，每行一组，保持元素在列表中的先后顺序。"
        ),
        "hint": "双重循环 i 从头、j 从 i+1 开始，避免重复和自配对；和等于 9 就打印。",
        "ref": """nums = [3, 6, 10, 14, 2, 7]

for i in range(len(nums)):
    for j in range(i + 1, len(nums)):
        if nums[i] + nums[j] == 9:
            print("({}, {})".format(nums[i], nums[j]))
""",
        "cases": [_c("", "(3, 6)\n(2, 7)")],
        "explain": "内层从 i+1 开始，保证每个组合只出现一次、顺序按列表原序。\n"
                   "如果内层从 0 开始，会得到 (3,6) 和 (6,3) 两个重复结果。\n"
                   "等价写法：for a, b in itertools.combinations(nums, 2)。",
    },
    {
        "id": "4-13",
        "chapter": CHAPTER,
        "no": 13,
        "title": "统计单词出现次数",
        "topic": "字典计数 / split",
        "level": 2,
        "desc": (
            "输入一个英文句子，统计每个单词出现的次数。\n"
            "按单词第一次出现的顺序输出，每行格式：<单词> <次数>"
        ),
        "hint": "split() 切词后用字典计数：counts[word] = counts.get(word, 0) + 1；再遍历字典输出。",
        "ref": """sentence = input()
counts = {}
for word in sentence.split():
    counts[word] = counts.get(word, 0) + 1

for word, n in counts.items():
    print(word, n)
""",
        "cases": [
            _c("the cat the dog the", "the 3\ncat 1\ndog 1"),
            _c("a b a", "a 2\nb 1"),
        ],
        "explain": "get(word, 0) 让第一次出现的单词从 0 开始计数，省掉 if 判断。\n"
                   "Python 3.7+ 字典保持插入顺序，所以按首次出现顺序输出是稳定的。\n"
                   "若要按次数排序，用 sorted(counts.items(), key=lambda kv: -kv[1])。",
    },
    {
        "id": "4-14",
        "chapter": CHAPTER,
        "no": 14,
        "title": "大学信息字典遍历",
        "topic": "嵌套字典 / items",
        "level": 2,
        "desc": (
            "创建字典 universities，以 3 所大学名称为键，值为包含 province（所属省份）和 type（类型）的字典：\n"
            "厦门大学/福建/综合，清华大学/北京/理工，北京大学/北京/综合。\n"
            "遍历 universities，输出每所大学的信息，格式：<大学> <省份> <类型>"
        ),
        "hint": "values 是字典，遍历时用 for name, info in universities.items() 再取 info[\"province\"]、info[\"type\"]。",
        "ref": """universities = {
    "厦门大学": {"province": "福建", "type": "综合"},
    "清华大学": {"province": "北京", "type": "理工"},
    "北京大学": {"province": "北京", "type": "综合"},
}

for name, info in universities.items():
    print(name, info["province"], info["type"])
""",
        "cases": [_c("", "厦门大学 福建 综合\n清华大学 北京 理工\n北京大学 北京 综合")],
        "explain": "字典套字典用来表达「实体 + 属性」，是最常见的数据建模方式。\n"
                   "items() 同时给出键和值；只写 for name in universities 拿到的是键。\n"
                   "输出顺序由插入顺序决定，所以建字典时顺序要按题目要求。",
    },
    {
        "id": "4-15",
        "chapter": CHAPTER,
        "no": 15,
        "title": "分页显示数据",
        "topic": "列表生成 / 切片分页",
        "level": 3,
        "desc": (
            "用 for 循环创建 201 条数据，每条格式为：xiaoming<N> xiaoming<N>@china.com pwd<N>，N 从 1 到 201。\n"
            "然后提示用户输入页码（每页显示 10 条），输出该页的数据。\n"
            "页码超出范围时输出：页码超出范围"
        ),
        "hint": "列表推导式生成数据；第 p 页的数据是 data[(p-1)*10 : p*10]；先算总页数 (len+9)//10 再判断合法性。",
        "ref": """data = []
for i in range(1, 202):
    data.append("xiaoming{} xiaoming{}@china.com pwd{}".format(i, i, i))

page = int(input())
total_page = (len(data) + 9) // 10

if page < 1 or page > total_page:
    print("页码超出范围")
else:
    start = (page - 1) * 10
    for item in data[start:start + 10]:
        print(item)
""",
        "cases": [
            _c("21", "xiaoming201 xiaoming201@china.com pwd201"),
            _c("999", "页码超出范围"),
            _c("1", "xiaoming1 xiaoming1@china.com pwd1\n"
                    "xiaoming2 xiaoming2@china.com pwd2\n"
                    "xiaoming3 xiaoming3@china.com pwd3\n"
                    "xiaoming4 xiaoming4@china.com pwd4\n"
                    "xiaoming5 xiaoming5@china.com pwd5\n"
                    "xiaoming6 xiaoming6@china.com pwd6\n"
                    "xiaoming7 xiaoming7@china.com pwd7\n"
                    "xiaoming8 xiaoming8@china.com pwd8\n"
                    "xiaoming9 xiaoming9@china.com pwd9\n"
                    "xiaoming10 xiaoming10@china.com pwd10"),
        ],
        "explain": "分页公式：第 p 页从 (p-1)*10 开始，取 10 条；用切片天然处理了「最后一页不足 10 条」。\n"
                   "总页数用 (总数 + 9) // 10 向上取整，201 条 → 21 页。\n"
                   "如果先切片再判断页码，越界时不会报错但结果为空，反而不容易发现输入问题。",
    },
    {
        "id": "4-16",
        "chapter": CHAPTER,
        "no": 16,
        "title": "歌手大赛最终得分",
        "topic": "列表 / 去极值 / 平均值",
        "level": 2,
        "desc": (
            "输入一行评委打分（0-10 分，空格分隔，至少 3 个分数），去掉一个最高分和一个最低分，"
            "计算其余分数的平均值，输出保留 2 位小数。"
        ),
        "hint": "分数转成列表后 remove 一个 max 和一个 min（或用排序后取中间），再求和除以个数。",
        "ref": """scores = [float(x) for x in input().split()]

scores.remove(max(scores))
scores.remove(min(scores))
avg = sum(scores) / len(scores)
print("{:.2f}".format(avg))
""",
        "cases": [
            _c("9 8 9.5 10 7 8.5", "8.75"),
            _c("10 10 10", "10.00"),
            _c("1 2 3 4", "2.50"),
        ],
        "explain": "remove 只删第一个匹配值：有多个并列最高分时也只去掉一个，符合「去掉一个最高分」的语义。\n"
                   "也可以排序后 scores = sorted(scores)[1:-1]，效果相同但会重新排列。\n"
                   "输出用 {:.2f} 保留两位；sum/len 在列表为空时会出错，所以题目要求至少 3 个分数。",
    },
    {
        "id": "4-17",
        "chapter": CHAPTER,
        "no": 17,
        "title": "银行排队模拟",
        "topic": "队列 / 列表操作 / 命令解析",
        "level": 3,
        "desc": (
            "用列表模拟银行排队，循环读取命令直到 QUIT：\n"
            "ADD <编号>  把编号加入队尾；\n"
            "NEXT        队首客户办理业务，输出「正在办理：<编号>」，队列为空时输出「没有排队用户」；\n"
            "LIST        输出「排队中：<编号1> <编号2> …」，队列为空输出「排队中：」；\n"
            "QUIT        结束，输出「未办理：<编号1> <编号2> …」，没有剩余则输出「没有未办理用户」。"
        ),
        "hint": "列表 append 入队、pop(0) 出队；命令用 split() 拆成 [cmd, arg]；注意空队列的提示。",
        "ref": """queue = []

while True:
    line = input().strip()
    if not line:
        continue
    parts = line.split()
    cmd = parts[0].upper()

    if cmd == "ADD":
        queue.append(parts[1])
    elif cmd == "NEXT":
        if queue:
            print("正在办理：{}".format(queue.pop(0)))
        else:
            print("没有排队用户")
    elif cmd == "LIST":
        print("排队中：" + " ".join(queue))
    elif cmd == "QUIT":
        if queue:
            print("未办理：" + " ".join(queue))
        else:
            print("没有未办理用户")
        break
""",
        "cases": [
            _c("ADD 001\nADD 002\nLIST\nNEXT\nLIST\nQUIT\n",
               "排队中：001 002\n正在办理：001\n排队中：002\n未办理：002"),
            _c("NEXT\nQUIT\n", "没有排队用户\n没有未办理用户"),
            _c("QUIT\n", "没有未办理用户"),
        ],
        "explain": "队列是「先进先出」：append 入队、pop(0) 出队；用 pop() 就变成栈（后进先出）了。\n"
                   "命令解析用 split()，ADD 后面带参数，取 parts[1]；其他命令忽略多余参数。\n"
                   "空队列要单独处理，否则 pop(0) 会抛 IndexError、join 会输出空行。",
    },
]
