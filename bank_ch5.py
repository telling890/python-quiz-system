# -*- coding: utf-8 -*-
"""第 5 章 字符串 · 实验内容 1-17（《Python 程序设计实验指导与习题解答》5.1 实验指导）

题干按教材原文整理，参考答案在教材给出的解法上做了纠错与规范化
（教材第 2、4、8、14 题的示范代码本身存在逻辑问题，解析里已注明）。

字段说明见 qbank.py。
"""

CHAPTER = "第5章 字符串"


def _c(stdin, expect):
    return {"stdin": stdin, "expect": expect}


QUESTIONS = [
    {
        "id": "5-01",
        "chapter": CHAPTER,
        "no": 1,
        "title": "敏感词过滤",
        "topic": "replace / 子串判断",
        "level": 1,
        "desc": (
            "设计一个敏感词过滤程序：输入一行内容，把其中的敏感词「数据安全」替换成「****」后输出。\n"
            "如果内容里没有敏感词，原样输出。"
        ),
        "hint": "先用 in 判断敏感词是否存在，再用 replace(old, new) 全量替换；replace 返回新串，要重新赋值。",
        "ref": """text = input()
sensitive = "数据安全"
if sensitive in text:
    text = text.replace(sensitive, "****")
print(text)
""",
        "cases": [
            _c("我们重视数据安全", "我们重视****"),
            _c("hello world", "hello world"),
            _c("数据安全就是数据安全", "****就是****"),
        ],
        "explain": (
            "replace(old, new) 默认替换全部出现，第三个参数 max 可以限制替换次数。\n"
            "教材代码先把原串保存到 input_str、结果放到 output_str，是为了保留原文；直接对 text 重新赋值更简洁。\n"
            "注意：敏感词是中文，占两个字节宽度，但替换后长度会变化，不要用长度做判断。"
        ),
    },
    {
        "id": "5-02",
        "chapter": CHAPTER,
        "no": 2,
        "title": "学生姓名与分数表格",
        "topic": "循环输入 / expandtabs",
        "level": 1,
        "desc": (
            "循环提示用户输入学生姓名和分数，每行按「姓名 分数」输入（空格隔开）。\n"
            "输入 q 或 Q 时结束，然后把记录以表格形式输出：先输出表头「姓名  分数」，再逐行输出，两列对齐。"
        ),
        "hint": (
            "while True + input() 循环；split() 拆分后先判断退出与字段个数，再取下标；\n"
            "用 \"\\t\".expandtabs(20) 让制表符补齐到 20 列，长短姓名都能对齐。"
        ),
        "ref": """records = []
while True:
    text = input().strip()
    if text.lower() == "q":
        break
    parts = text.split()
    if len(parts) != 2:
        print("格式错误，请输入：姓名 分数")
        continue
    records.append((parts[0], parts[1]))

print("姓名\\t分数".expandtabs(20))
for name, score in records:
    print("{}\\t{}".format(name, score).expandtabs(20))
""",
        "cases": [
            _c("shu 90\nqing 59\nxin 9\nq\n", "姓名\t分数\nshu\t90\nqing\t59\nxin\t9"),
            _c("Li 100\nQ\n", "姓名\t分数\nLi\t100"),
            _c("shu 90\nshu\nq\n", "格式错误，请输入：姓名 分数\n姓名\t分数\nshu\t90"),
        ],
        "explain": (
            "教材示范写的是 while input_str != 'q' or input_str.upper() != 'Q'：两个条件用 or 连接，永远为真，"
            "输入 q 也退不出去——应该用 and，或者直接判断 text.lower() == 'q'。\n"
            "另一个坑是先写 name, score = text.split() 再判断长度，字段不足时会抛 ValueError（见判题结果里的提示）。\n"
            "expandtabs(20) 把 \\t 补齐到 20 列的整数倍；不写参数时默认是 8 列。"
        ),
    },
    {
        "id": "5-03",
        "chapter": CHAPTER,
        "no": 3,
        "title": "判断回文字符串",
        "topic": "切片 [::-1]",
        "level": 1,
        "desc": (
            "回文串是指从左往右读和从右往左读都相同的字符串。\n"
            "输入一个字符串，判断它是否回文：是则输出「原串 是回文串」，否则输出「原串 不是回文串」。"
        ),
        "hint": "切片 [::-1] 反转字符串，再与原串比较；注意比较区分大小写。",
        "ref": """a = input()
b = a[::-1]
if a == b:
    print("{} 是回文串".format(a))
else:
    print("{} 不是回文串".format(a))
""",
        "cases": [
            _c("huuh", "huuh 是回文串"),
            _c("hubcccchub", "hubcccchub 不是回文串"),
            _c("aba", "aba 是回文串"),
        ],
        "explain": (
            "seq[::-1] 表示从头到尾、步长 -1，等价于反转。\n"
            "本题不忽略大小写和空格：\"Ab\" 与 \"bA\" 不是回文，\"a b a\" 也不是——如果要求忽略，"
            "需要先 a.lower().replace(\" \", \"\") 归一化再比较。"
        ),
    },
    {
        "id": "5-04",
        "chapter": CHAPTER,
        "no": 4,
        "title": "删除第一个字符串中的共有字符",
        "topic": "双重 for / replace / 字符过滤",
        "level": 2,
        "desc": (
            "输入两个字符串（每行一个），从第一个字符串中删除所有出现在第二个字符串里的字符，输出处理结果。\n"
            "例如输入 abcdea 和 ab，输出 cde。"
        ),
        "hint": (
            "思路一（教材）：双重 for 比较字符，相同就 str1 = str1.replace(char, \"\")；\n"
            "思路二（更快）：把第二个串转成集合，遍历第一个串只保留不在集合里的字符。"
        ),
        "ref": """str1 = input()
str2 = input()
keep = set(str2)
result = ""
for ch in str1:
    if ch not in keep:
        result += ch
print(result)
""",
        "cases": [
            _c("abcdea\nab", "cde"),
            _c("hello\nxyz", "hello"),
            _c("aabbcc\nab", "cc"),
        ],
        "explain": (
            "教材用 replace 在双重循环里删除：能出结果，但复杂度是 O(n*m)，而且每次都生成新字符串。\n"
            "用集合 set(str2) 判断 in，查询是 O(1)，整体 O(n)，数据量大时差距明显。\n"
            "注意「删除所有出现位置」与「只删一次」的区别：replace(ch, \"\") 不设 max 就是全删。"
        ),
    },
    {
        "id": "5-05",
        "chapter": CHAPTER,
        "no": 5,
        "title": "查找字符的索引",
        "topic": "索引遍历 / 字符串索引",
        "level": 1,
        "desc": (
            "给定字符串 \"Xiamen University\"，找出字母 U 在其中的索引，输出：字母U的索引是<索引>。\n"
            "（本题字符串固定，不需要输入）"
        ),
        "hint": "用 len() 取长度、for 或 while 遍历下标；也可以用 string.find('U')。",
        "ref": """a_string = "Xiamen University"
i = 0
while i < len(a_string):
    if a_string[i] == "U":
        print("字母U的索引是{}".format(i))
    i += 1
""",
        "cases": [
            _c("", "字母U的索引是7"),
        ],
        "explain": (
            "索引从 0 开始：X(0) i(1) a(2) m(3) e(4) n(5) 空格(6) U(7)，所以 U 在 7。\n"
            "教材示范用 for n in range(length) 加 continue/else 的写法，也可以用 enumerate：\n"
            "    for i, ch in enumerate(a_string):\n"
            "        if ch == \"U\":\n"
            "            print(\"字母U的索引是{}\".format(i))\n"
            "更直接的是 a_string.find(\"U\")。"
        ),
    },
    {
        "id": "5-06",
        "chapter": CHAPTER,
        "no": 6,
        "title": "两个字符串的字符是否完全相同",
        "topic": "字典计数 / 频次比较",
        "level": 2,
        "desc": (
            "输入两个字符串（每行一个），判断它们包含的字符是否完全相同：\n"
            "即字符种类相同，且每个字符出现的次数也相同。\n"
            "相同输出：两个字符串包含的字符完全相同\n"
            "否则输出：两个字符串包含的字符不同"
        ),
        "hint": "分别统计两个字符串的字符频次（字典），再比较两个字典是否相等；也可以 sorted() 后比较。",
        "ref": """a = input()
b = input()

dic_a = {}
dic_b = {}
for char in a:
    dic_a[char] = dic_a.get(char, 0) + 1
for char in b:
    dic_b[char] = dic_b.get(char, 0) + 1

if dic_a == dic_b:
    print("两个字符串包含的字符完全相同")
else:
    print("两个字符串包含的字符不同")
""",
        "cases": [
            _c("abc\ncba", "两个字符串包含的字符完全相同"),
            _c("aab\nabb", "两个字符串包含的字符不同"),
            _c("abc\nabcd", "两个字符串包含的字符不同"),
        ],
        "explain": (
            "字典比较的是键值对集合，与插入顺序无关，所以 abc 与 cba 判为相同。\n"
            "aab 的频次是 {a:2,b:1}，abb 是 {a:1,b:2}，频次不同 → 不同。\n"
            "等价写法：sorted(a) == sorted(b)，或者 collections.Counter(a) == Counter(b)。"
        ),
    },
    {
        "id": "5-07",
        "chapter": CHAPTER,
        "no": 7,
        "title": "整数加法计算器",
        "topic": "split 拆分 / int 转换",
        "level": 1,
        "desc": (
            "实现一个整数加法计算器：输入形如「3+2」的表达式，输出「3+2=5」。\n"
            "假设输入的两个操作数都是正整数，中间用加号连接。"
        ),
        "hint": "用 split('+') 把表达式拆成两个字符串，int() 转成整数相加，再格式化成 a+b=c。",
        "ref": """expr = input()
parts = expr.split("+")
n1 = int(parts[0])
n2 = int(parts[1])
print("{}+{}={}".format(n1, n2, n1 + n2))
""",
        "cases": [
            _c("3+2", "3+2=5"),
            _c("10+25", "10+25=35"),
            _c("100+1", "100+1=101"),
        ],
        "explain": (
            "input() 拿到的是字符串，必须 int() 转换后再加，否则 \"3\"+\"2\" 会拼成 \"32\"。\n"
            "split(\"+\") 返回列表；这里假设只有一个加号，所以直接取 parts[0]、parts[1]。\n"
            "如果要支持多个加号，用 sum(int(x) for x in expr.split(\"+\"))。\n"
            "想支持减号、乘号，可以先判断符号再分派运算。"
        ),
    },
    {
        "id": "5-08",
        "chapter": CHAPTER,
        "no": 8,
        "title": "用户名合法性校验",
        "topic": "字符范围 / all-any 判断",
        "level": 3,
        "desc": (
            "输入用户名，判断是否合法。规则：\n"
            "1. 只能由英文字母和数字组成；\n"
            "2. 必须同时包含字母和数字；\n"
            "3. 第一个字符必须是大写英文字母。\n"
            "合法输出「合法」，否则输出「不合法」。\n"
            "例：abc、123、abc123 都不合法；Abc123def 合法。"
        ),
        "hint": (
            "按顺序判断：首字符是否 A-Z → 是否只含字母数字（逐字符范围判断）→ 是否既有字母又有数字。\n"
            "「既有…又有…」可以用 any() 配合 isalpha()/isdigit()。"
        ),
        "ref": """username = input()

if not username:
    print("不合法")
elif not ("A" <= username[0] <= "Z"):
    print("不合法")
elif not all(("0" <= c <= "9") or ("A" <= c <= "Z") or ("a" <= c <= "z") for c in username):
    print("不合法")
elif not (any(c.isalpha() for c in username) and any(c.isdigit() for c in username)):
    print("不合法")
else:
    print("合法")
""",
        "cases": [
            _c("Abc123def", "合法"),
            _c("abc123", "不合法"),
            _c("123", "不合法"),
            _c("Abcdef", "不合法"),
            _c("A1", "合法"),
        ],
        "explain": (
            "教材示范的 if username.isalpha() or username.isdigit(): print('不合法') 是在排查「全是字母或全是数字」，"
            "但这样就把「只含字母」和「只含数字」判为不合法，方向是对的；问题出在后面的循环里：\n"
            "它每发现一个非法字符就打印一次「不合法」再 break，而合法时只打印一次「合法」——用 for-else 才不会重复打印。\n"
            "本题用 all() 一次判断所有字符是否合法，再用 any() 判断字母、数字是否都出现过，逻辑更直观。\n"
            "注意空字符串必须先判断，否则 username[0] 会抛 IndexError。"
        ),
    },
    {
        "id": "5-09",
        "chapter": CHAPTER,
        "no": 9,
        "title": "用索引循环模拟切片",
        "topic": "while 循环 / 步长",
        "level": 2,
        "desc": (
            "不使用字符串切片语法，用索引循环实现 a[1::2] 的效果：\n"
            "输入一个字符串，从下标 1 开始、每次前进 2，把取到的字符依次输出（拼接成一个字符串）。"
        ),
        "hint": "while 循环维护下标 i，初值 1，每次 i += 2，条件 i < len(s)；把 s[i] 拼到结果串。",
        "ref": """s = input()
i = 1
result = ""
while i < len(s):
    result += s[i]
    i += 2
print(result)
""",
        "cases": [
            _c("string", "tig"),
            _c("abcdef", "bdf"),
            _c("ab", "b"),
        ],
        "explain": (
            "a[1::2] 的含义是「起点 1、终点到末尾、步长 2」，取下标 1、3、5…\n"
            "string 的下标：s(0) t(1) r(2) i(3) n(4) g(5) → 取 t、i、g，输出 tig。\n"
            "教材示范里先 while 打印再 print() 换行，最后还调了一次 aString[1::2] 做对照——正式作业里只需实现一种。\n"
            "注意循环条件写成 i < len(s)，写成 i <= len(s) 会越界。"
        ),
    },
    {
        "id": "5-10",
        "chapter": CHAPTER,
        "no": 10,
        "title": "小写字母转大写",
        "topic": "for 遍历 / upper / ord-chr",
        "level": 1,
        "desc": (
            "输入一个字符串，把所有小写英文字母转换成对应的大写字母，其他字符保持不变。\n"
            "要求逐字符处理并拼接新字符串（教材给了 upper() 和 ord()/chr() 两种写法，任选其一）。\n"
            "例：输入 Abc123def456，输出 ABC123DEF456。"
        ),
        "hint": (
            "遍历字符串，用 \"a\" <= ch <= \"z\" 判断小写字母；\n"
            "方法一：ch.upper()；方法二：chr(ord(ch) - 97 + 65)。"
        ),
        "ref": """astring = input()
bstring = ""
for char in astring:
    if "a" <= char <= "z":
        bstring += char.upper()
    else:
        bstring += char
print(bstring)
""",
        "cases": [
            _c("Abc123def456", "ABC123DEF456"),
            _c("hello 世界", "HELLO 世界"),
            _c("a1 z!", "A1 Z!"),
        ],
        "explain": (
            "字符比较按 Unicode 编码，'a'~'z' 是连续的一段，所以范围判断能筛出小写字母。\n"
            "ord('a')=97、ord('A')=65，差值 32；chr(ord(ch)-32) 也能得到大写字母。\n"
            "常见坑：把下界写成 \"a \"（末尾带空格），字符 'a' 就落不进范围，整串都不会被转换。\n"
            "字符串不可变，bstring += ... 每次都生成新对象；长文本应改用列表收集再 \"\".join()。"
        ),
    },
    {
        "id": "5-11",
        "chapter": CHAPTER,
        "no": 11,
        "title": "实现 find 的功能",
        "topic": "子串查找 / 循环",
        "level": 2,
        "desc": (
            "不用 str.find()，自己实现子串查找：\n"
            "输入两个字符串 a、b（每行一个），输出 b 在 a 中第一次出现的起始索引；找不到输出 -1。"
        ),
        "hint": (
            "枚举 a 的每个起点 i，判断 a[i:i+len(b)] 是否等于 b，相等就输出 i 并 break；\n"
            "循环结束还没找到（用 for-else）则输出 -1。"
        ),
        "ref": """a = input()
b = input()

found = -1
for i in range(len(a) - len(b) + 1):
    if a[i:i + len(b)] == b:
        found = i
        break
print(found)
""",
        "cases": [
            _c("Hello World\nWorld", "6"),
            _c("abcabc\nca", "2"),
            _c("abc\nzz", "-1"),
        ],
        "explain": (
            "range 的上界是 len(a) - len(b) + 1：起点再往后，剩下的长度就不够放下 b 了，能少做无用比较。\n"
            "没有做字符串切片的话，也可以逐个字符比较内层循环（教材示范就是先比首字符再比整段）。\n"
            "for-else 的 else 只在「没有 break」时执行，用来处理找不到的情况很自然。\n"
            "Python 内置的 a.find(b) 行为一致：找不到返回 -1。"
        ),
    },
    {
        "id": "5-12",
        "chapter": CHAPTER,
        "no": 12,
        "title": "输出字符串的正反向索引表",
        "topic": "索引 / 负索引 / enumerate",
        "level": 2,
        "desc": (
            "输入一个字符串，逐行输出每个字符的正向索引和反向索引，每行三个部分（用一个空格分隔）：\n"
            "字符 正向索引 反向索引\n"
            "例如输入 abc，输出三行：\n"
            "a 0 -3\n"
            "b 1 -2\n"
            "c 2 -1"
        ),
        "hint": (
            "正向索引是 0~len-1，反向索引等于「正向索引 - len」；\n"
            "用 enumerate(s) 同时拿到下标和字符，再格式化输出。"
        ),
        "ref": """s = input()
n = len(s)
for i, ch in enumerate(s):
    print("{} {} {}".format(ch, i, i - n))
""",
        "cases": [
            _c("abc", "a 0 -3\nb 1 -2\nc 2 -1"),
            _c("Hi", "H 0 -2\ni 1 -1"),
            _c("x", "x 0 -1"),
        ],
        "explain": (
            "Python 支持负索引：s[-1] 是最后一个字符，s[-n] 是第一个。\n"
            "所以下标 i 的反向索引就是 i - len(s)：长度 3 时，0→-3、1→-2、2→-1。\n"
            "教材原题的输出是带边框的索引示意图（用 +、-、| 拼框），这里规范成三列文本，"
            "考察点仍是正向/反向索引的对应关系。"
        ),
    },
    {
        "id": "5-13",
        "chapter": CHAPTER,
        "no": 13,
        "title": "获取两个字符串的公共字符",
        "topic": "in 判断 / 顺序遍历",
        "level": 1,
        "desc": (
            "输入两个字符串（每行一个），按第一个字符串中的顺序，输出同时出现在第二个字符串中的字符。\n"
            "例如字符串1为 abc123、字符串2为 mna3，输出 a3。\n"
            "注意不去重：第一个串里重复的公共字符要重复输出。"
        ),
        "hint": "遍历第一个字符串，用 in 判断字符是否出现在第二个字符串里，是就拼到结果串。",
        "ref": """a = input()
b = input()
c = ""
for char in a:
    if char in b:
        c += char
print(c)
""",
        "cases": [
            _c("abc123\nmna3", "a3"),
            _c("hello\nlo", "llo"),
            _c("abc\nxyz", ""),
        ],
        "explain": (
            "in 用于字符串时做子串包含判断，单字符时就是「是否出现过」。\n"
            "保留原顺序、也不去重，所以不能用 set(a) & set(b)（它会丢顺序并去重）。\n"
            "若想提速，可以先把 b 转成 set：if char in set_b，查询从 O(m) 降到 O(1)。"
        ),
    },
    {
        "id": "5-14",
        "chapter": CHAPTER,
        "no": 14,
        "title": "单词大写用法校验",
        "topic": "upper / lower / title",
        "level": 2,
        "desc": (
            "给定一个单词，判断它的大写用法是否正确。正确的三种情况：\n"
            "1. 全部字母大写，如 USA；\n"
            "2. 全部字母小写，如 hello；\n"
            "3. 只有首字母大写、其余小写，如 China。\n"
            "符合任一情况输出「用法正确」，否则输出「用法错误」。"
        ),
        "hint": "利用三个方法与原串比较：s.upper() == s、s.lower() == s、s.title() == s，任一成立即可。",
        "ref": """word = input()
if word.upper() == word or word.lower() == word or word.title() == word:
    print("用法正确")
else:
    print("用法错误")
""",
        "cases": [
            _c("USA", "用法正确"),
            _c("hello", "用法正确"),
            _c("China", "用法正确"),
            _c("chIna", "用法错误"),
            _c("ChIna", "用法错误"),
        ],
        "explain": (
            "upper() 全转大写、lower() 全转小写、title() 每个单词首字母大写、其余小写，"
            "把结果和原串比较就能判断「原本是什么写法」。\n"
            "三个条件用 or 连接，任一成立即是合法用法。\n"
            "注意 title() 会把 don't 变成 Don'T，本题目的是判断单次写法，规则简单，不考虑这种情况。"
        ),
    },
    {
        "id": "5-15",
        "chapter": CHAPTER,
        "no": 15,
        "title": "统计数字和字母个数",
        "topic": "isdecimal / isalpha",
        "level": 1,
        "desc": (
            "输入一行内容，统计其中十进制数字字符的个数和字母字符的个数，按格式输出：\n"
            "字符串<原文>中，有<数字个数>个数字，有<字母个数>个字母"
        ),
        "hint": "遍历字符：isdecimal() 为真数字计数 +1，isalpha() 为真字母计数 +1，其它字符忽略。",
        "ref": """text = input()
digit_count = 0
alpha_count = 0
for char in text:
    if char.isdecimal():
        digit_count += 1
    elif char.isalpha():
        alpha_count += 1
print("字符串{}中，有{}个数字，有{}个字母".format(text, digit_count, alpha_count))
""",
        "cases": [
            _c("abc123", "字符串abc123中，有3个数字，有3个字母"),
            _c("中文abc12", "字符串中文abc12中，有2个数字，有5个字母"),
            _c("!@#", "字符串!@#中，有0个数字，有0个字母"),
        ],
        "explain": (
            "isdecimal() 只认十进制数字 0-9；isdigit() 还认上标数字 ²，isnumeric() 连汉字「一」也算数字，"
            "所以统计十进制数字要用 isdecimal()。\n"
            "isalpha() 把汉字也当作字母，因此「中文」被计成 2 个字母；只统计英文字母要改用范围判断。\n"
            "用 elif 而不是两个独立 if：一个字符不可能既是数字又是字母。"
        ),
    },
    {
        "id": "5-16",
        "chapter": CHAPTER,
        "no": 16,
        "title": "字符串去重并排序",
        "topic": "set / list / sort / join",
        "level": 1,
        "desc": (
            "输入一个字符串，去掉重复字符，把剩下的字符按升序排列后输出。\n"
            "例如输入 abcmnmbcdacbhk，输出 abcdhkmn。"
        ),
        "hint": "set(s) 去重 → list() 转列表 → sort() 升序 → \"\".join() 连接。注意 sort() 原地修改、返回 None。",
        "ref": """str1 = input()
set1 = set(str1)
list1 = list(set1)
list1.sort()
str2 = "".join(list1)
print(str2)
""",
        "cases": [
            _c("abcmnmbcdacbhk", "abcdhkmn"),
            _c("hello", "ehlo"),
            _c("cba", "abc"),
        ],
        "explain": (
            "set 无序，所以去重后必须排序，结果才稳定可比。\n"
            "sort() 原地排序并返回 None；写 list1 = list1.sort() 会让 list1 变成 None，join 时报 TypeError。\n"
            "一行写法：\"\".join(sorted(set(str1)))。"
        ),
    },
    {
        "id": "5-17",
        "chapter": CHAPTER,
        "no": 17,
        "title": "判断同构字符串",
        "topic": "双向映射 / 字典",
        "level": 3,
        "desc": (
            "若字符串 s 中的字符可以被逐一替换得到 t，且替换过程中字符的位置顺序保持不变、"
            "不同字符不能映射到同一个字符（但可以映射到自己），则称 s 与 t 同构。\n"
            "输入 s 和 t（每行一个），同构输出「同构」，否则输出「不同构」。\n"
            "例：egg 与 add 同构；foo 与 bar 不同构。"
        ),
        "hint": (
            "为 s→t 和 t→s 各建一个字典，逐位检查映射是否冲突；\n"
            "两个方向都要检查，否则 aab 与 ccc 会被误判为同构。"
        ),
        "ref": """s = input()
t = input()

if len(s) != len(t):
    print("不同构")
else:
    s_to_t = {}
    t_to_s = {}
    ok = True
    for x, y in zip(s, t):
        if x in s_to_t and s_to_t[x] != y:
            ok = False
            break
        if y in t_to_s and t_to_s[y] != x:
            ok = False
            break
        s_to_t[x] = y
        t_to_s[y] = x
    print("同构" if ok else "不同构")
""",
        "cases": [
            _c("egg\nadd", "同构"),
            _c("foo\nbar", "不同构"),
            _c("paper\ntitle", "同构"),
            _c("aab\nccc", "不同构"),
        ],
        "explain": (
            "关键是「双向」：只记 s→t 的话，aab 与 ccc 会通过（a→c，b→c），但 c 同时对应 a 和 b，不合法。\n"
            "教材示范把每个字符首次出现的序号编码成数组（egg→[1,2,2]、add→[1,2,2]），再比较两个数组是否相等，"
            "是等价的思路，也更省内存。\n"
            "长度不同直接判不同构，省去后面所有判断。"
        ),
    },
]
