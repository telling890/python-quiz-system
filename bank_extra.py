# -*- coding: utf-8 -*-
"""拓展练习 · 40 道经典编程题（网络题源）

选题参考公开题集 Python100Cases（GitHub: RichardFu123/Python100Cases，
腾讯云转载：https://cloud.tencent.com.cn/developer/article/1774665）以及常见的
Python 入门练习清单。题干按本系统的判题约定重写，参考答案与测试用例均为自行编写，
不是对原题解的直接复制；每题的 source 字段标注了对应的原题编号与名称。

与教材三章不重复，作为「学完教材后的加练」。
"""

CHAPTER = "拓展练习"

REPO = "https://github.com/RichardFu123/Python100Cases"


def _c(stdin, expect):
    return {"stdin": stdin, "expect": expect}


def _r(stdin, expect):
    return {"stdin": stdin, "expect": expect, "raw": True}


QUESTIONS = [
    # ------------------------------------------------------------ 控制结构
    {
        "id": "E-01",
        "chapter": CHAPTER,
        "no": 1,
        "title": "奖金分段提成",
        "topic": "if-elif / 分段计算",
        "level": 2,
        "source": "Python100Cases 实例002「个税计算」（简化版）",
        "desc": (
            "企业按利润分档提成：\n"
            "利润 ≤ 10 万：按 10% 提成；\n"
            "10 万 < 利润 ≤ 20 万：10 万以内部分仍按 10%，超出部分按 7.5%；\n"
            "利润 > 20 万：前两档照算，超过 20 万的部分按 5%。\n"
            "输入利润（整数，单位元），输出应发奖金，保留 2 位小数。"
        ),
        "hint": "分三段用 if-elif；每段只累加「本段内」的那部分利润，别把整笔利润乘本段费率。",
        "ref": """p = float(input())
if p <= 100000:
    bonus = p * 0.1
elif p <= 200000:
    bonus = 100000 * 0.1 + (p - 100000) * 0.075
else:
    bonus = 100000 * 0.1 + 100000 * 0.075 + (p - 200000) * 0.05
print("{:.2f}".format(bonus))
""",
        "cases": [
            _c("50000", "5000.00"),
            _c("200000", "17500.00"),
            _c("300000", "22500.00"),
        ],
        "explain": "分段提成的关键是「逐段累加」：20 万利润 = 10 万×10% + 10 万×7.5% = 17500。\n"
                   "如果写成 200000*0.075 = 15000，就把前 10 万也算成了 7.5%，结果偏小。\n"
                   "输入用 float 更稳，避免整数除法丢掉小数部分。",
    },
    {
        "id": "E-02",
        "chapter": CHAPTER,
        "no": 2,
        "title": "这一天是当年的第几天",
        "topic": "列表求和 / 闰年",
        "level": 2,
        "source": "Python100Cases 实例004「这天第几天」",
        "desc": (
            "输入年月日（同一行，空格分隔），输出这一天是这一年的第几天。\n"
            "闰年规则：能被 4 整除且不能被 100 整除，或能被 400 整除；闰年 2 月为 29 天。"
        ),
        "hint": "用月份天数表，把当前月之前的月份天数加起来，再加上日；闰年时把 2 月改成 29。",
        "ref": """y, m, d = input().split()
y = int(y)
m = int(m)
d = int(d)

leap = (y % 4 == 0 and y % 100 != 0) or y % 400 == 0
days = [0, 31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

total = 0
for i in range(1, m):
    total += days[i]
print(total + d)
""",
        "cases": [
            _c("2024 3 1", "61"),
            _c("2023 3 1", "60"),
            _c("2024 12 31", "366"),
        ],
        "explain": "2024 是闰年，2 月 29 天，所以 3 月 1 日是 31+29+1 = 61 天；2023 年则是 60 天。\n"
                   "闰年判断四百年一闰：1900 不是闰年（能被 100 整除但不能被 400 整除），2000 是。\n"
                   "用 days 表的 0 号位占位，range(1, m) 直接累加前 m-1 个月，不容易差一。",
    },
    {
        "id": "E-03",
        "chapter": CHAPTER,
        "no": 3,
        "title": "三个数排序",
        "topic": "分支 / 排序",
        "level": 1,
        "source": "Python100Cases 实例005「三数排序」",
        "desc": "输入三个整数（同一行，空格分隔），按从小到大的顺序输出，数字之间用一个空格分隔。",
        "hint": "最省事是 sorted()；练分支的话可以三个数两两比较交换。",
        "ref": """nums = [int(x) for x in input().split()]
nums.sort()
print(" ".join(str(n) for n in nums))
""",
        "cases": [
            _c("3 1 2", "1 2 3"),
            _c("5 5 1", "1 5 5"),
            _c("9 8 7", "7 8 9"),
        ],
        "explain": "sort() 原地排序、返回 None，所以先排序再打印列表本身，不能写 nums = nums.sort()。\n"
                   "三个数排序的关键是两两比较，保证每轮把较大的数换到后面；用 sorted() 一步到位。\n"
                   "数字相同的情况（5 5 1）也要正确，比较时用 <= 或 >= 都行，不要跳过相等。",
    },
    {
        "id": "E-04",
        "chapter": CHAPTER,
        "no": 4,
        "title": "九九乘法表",
        "topic": "双重循环 / 格式化输出",
        "level": 1,
        "source": "Python100Cases 实例008「九九乘法表」",
        "desc": (
            "输出 9 行乘法口诀：第 i 行依次输出 i*1、i*2 …… i*i 的结果，\n"
            "每项格式为「a*b=积」，项与项之间用一个空格分隔。"
        ),
        "hint": "外层 i 从 1 到 9，内层 j 从 1 到 i；用列表收集本行再 join()，避免行末多空格。",
        "ref": """for i in range(1, 10):
    row = ["{}*{}={}".format(i, j, i * j) for j in range(1, i + 1)]
    print(" ".join(row))
""",
        "cases": [
            _c("",
               "1*1=1\n"
               "2*1=2 2*2=4\n"
               "3*1=3 3*2=6 3*3=9\n"
               "4*1=4 4*2=8 4*3=12 4*4=16\n"
               "5*1=5 5*2=10 5*3=15 5*4=20 5*5=25\n"
               "6*1=6 6*2=12 6*3=18 6*4=24 6*5=30 6*6=36\n"
               "7*1=7 7*2=14 7*3=21 7*4=28 7*5=35 7*6=42 7*7=49\n"
               "8*1=8 8*2=16 8*3=24 8*4=32 8*5=40 8*6=48 8*7=56 8*8=64\n"
               "9*1=9 9*2=18 9*3=27 9*4=36 9*5=45 9*6=54 9*7=63 9*8=72 9*9=81"),
        ],
        "explain": "内层循环的终点是 i，所以每行项目数逐行增加，这就是「九九」表的形状。\n"
                   "用 join 拼行比 print(end=' ') 更好：后者会在行末留下一个空格。\n"
                   "注意 3*4=12 这类两位数结果，用 {} 直接格式化即可，不需要对齐补空格（判题会忽略多余空白）。",
    },
    {
        "id": "E-05",
        "chapter": CHAPTER,
        "no": 5,
        "title": "100 到 200 之间的素数",
        "topic": "循环 / 素数判定",
        "level": 2,
        "source": "Python100Cases 实例012「100到200的素数」",
        "desc": (
            "输出 100 到 200 之间（含端点）的所有素数：\n"
            "第一行输出个数，第二行按从小到大输出这些素数，数字之间用一个空格分隔。"
        ),
        "hint": "写个 is_prime：从 2 试除到 √n；用列表收集结果，最后统一输出。",
        "ref": """primes = []
for n in range(100, 201):
    is_prime = True
    for d in range(2, int(n ** 0.5) + 1):
        if n % d == 0:
            is_prime = False
            break
    if is_prime:
        primes.append(n)
print(len(primes))
print(" ".join(str(p) for p in primes))
""",
        "cases": [
            _c("",
               "21\n"
               "101 103 107 109 113 127 131 137 139 149 151 157 163 167 173 179 181 191 193 197 199"),
        ],
        "explain": "100~200 共 21 个素数。用 int(n**0.5)+1 作上界即可，多试除几个数不影响正确性，只是慢一点。\n"
                   "for-else 写法更简洁：循环没有被 break 就说明是素数。\n"
                   "注意 2 是素数：本题范围从 100 开始，不涉及这个边界。",
    },
    {
        "id": "E-06",
        "chapter": CHAPTER,
        "no": 6,
        "title": "水仙花数",
        "topic": "循环 / 数位拆分",
        "level": 2,
        "source": "Python100Cases 实例013「所有水仙花数」",
        "desc": (
            "水仙花数指三位数中「各位数字的立方和等于它本身」的数，例如 153 = 1³+5³+3³。\n"
            "输出 100~999 之间所有水仙花数，数字之间用一个空格分隔。"
        ),
        "hint": "把数转成字符串取每一位，或百位 n//100、十位 n//10%10、个位 n%10。",
        "ref": """result = []
for n in range(100, 1000):
    s = str(n)
    total = sum(int(ch) ** 3 for ch in s)
    if total == n:
        result.append(str(n))
print(" ".join(result))
""",
        "cases": [_c("", "153 370 371 407")],
        "explain": "三位水仙花数只有 153、370、371、407 四个。\n"
                   "sum(int(ch)**3 for ch in str(n)) 是生成器表达式，比手写三位拆分更短且不易错。\n"
                   "注意「立方」而不是「平方」；四位数对应的是四次方（水仙花数的一般形式叫阿姆斯特朗数）。",
    },
    {
        "id": "E-07",
        "chapter": CHAPTER,
        "no": 7,
        "title": "猴子吃桃",
        "topic": "倒推 / 循环",
        "level": 2,
        "source": "Python100Cases 实例021「猴子偷桃」",
        "desc": (
            "猴子第一天摘了若干桃子，当天吃掉一半又多吃一个；之后每天吃掉前一天剩下的一半再多吃一个。\n"
            "到第 10 天早上只剩 1 个桃子。问第一天一共摘了多少个？输出这个数。"
        ),
        "hint": "倒着推：第 n 天剩 1 个，前一天的桃子数 = (今天 + 1) × 2，循环 9 次。",
        "ref": """peach = 1
for i in range(9):
    peach = (peach + 1) * 2
print(peach)
""",
        "cases": [_c("", "1534")],
        "explain": "正着算要试错，倒着推是唯一确定的：(剩 + 1) × 2 就是前一天的数量。\n"
                   "第 10 天早上剩 1 个，说明第 9 天吃完后剩 1 个，所以只倒推 9 次（第 1 天到第 9 天）。\n"
                   "写成 range(10) 会多推一天，结果翻倍再翻倍，就错了。",
    },
    {
        "id": "E-08",
        "chapter": CHAPTER,
        "no": 8,
        "title": "打印菱形",
        "topic": "双重循环 / 空格排版",
        "level": 2,
        "source": "Python100Cases 实例023「画菱形」",
        "desc": (
            "输入半高 n（2~9 的整数），输出由 * 组成的菱形，共 2n-1 行。\n"
            "以上半部分为例：第 i 行有 n-i 个前导空格、2i-1 个星号；下半部分对称递减。\n"
            "例如 n=3 输出 5 行。"
        ),
        "hint": "上半部分 i 从 1 到 n，下半部分 i 从 n-1 递减到 1；每行 = 空格×(n-i) + 星号×(2i-1)。",
        "ref": """n = int(input())
for i in range(1, n + 1):
    print(" " * (n - i) + "*" * (2 * i - 1))
for i in range(n - 1, 0, -1):
    print(" " * (n - i) + "*" * (2 * i - 1))
""",
        "cases": [
            _r("3", "  *\n ***\n*****\n ***\n  *"),
            _r("5", "    *\n   ***\n  *****\n *******\n*********\n *******\n  *****\n   ***\n    *"),
        ],
        "explain": "判题使用 raw 模式，行首空格必须完全正确，所以空格数算错一位就会失败。\n"
                   "下半部分不要从 n 开始（会重复中间最长的一行），要从 n-1 开始。\n"
                   "如果题目只要求上半部分（等腰三角形），删掉第二个循环即可。",
    },
    {
        "id": "E-09",
        "chapter": CHAPTER,
        "no": 9,
        "title": "分数序列前 20 项之和",
        "topic": "循环 / 浮点累加",
        "level": 2,
        "source": "Python100Cases 实例024「斐波那契数列II」",
        "desc": (
            "分数序列 2/1, 3/2, 5/3, 8/5, 13/8, 21/13… 的分子、分母都是斐波那契数。\n"
            "求这个数列前 20 项的和，输出保留 2 位小数。"
        ),
        "hint": "每项 = 分子/分母；下一项的分子 = 当前分子+分母，分母 = 当前分子。累加 20 次。",
        "ref": """a, b = 2, 1
total = 0.0
for i in range(20):
    total += a / b
    a, b = a + b, a
print("{:.2f}".format(total))
""",
        "cases": [_c("", "32.66")],
        "explain": "20 项的和约为 32.66，相邻两项的比值逼近黄金分割 1.618。\n"
                   "并行赋值 a, b = a+b, a 同时更新，写成分两步就会用错值。\n"
                   "除法要用 / 而不是 //；累加用浮点数，最后统一格式化到 2 位。",
    },
    {
        "id": "E-10",
        "chapter": CHAPTER,
        "no": 10,
        "title": "递归求阶乘",
        "topic": "递归 / 基线条件",
        "level": 2,
        "source": "Python100Cases 实例026「递归求阶乘」",
        "desc": "输入非负整数 n，用递归函数求 n!（规定 0! = 1），输出结果。",
        "hint": "基线条件 n <= 1 返回 1，否则返回 n * factorial(n-1)。",
        "ref": """def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print(factorial(int(input())))
""",
        "cases": [_c("5", "120"), _c("0", "1"), _c("1", "1")],
        "explain": "递归必须有基线条件（n<=1），否则会无限递归触发 RecursionError。\n"
                   "n=0 和 n=1 都由基线条件覆盖，返回 1，符合 0! = 1 的规定。\n"
                   "n 很小时递归没问题；n 大时（如 1000）会超过默认递归深度，应该改用循环。",
    },
    {
        "id": "E-11",
        "chapter": CHAPTER,
        "no": 11,
        "title": "递归逆序输出字符串",
        "topic": "递归 / 字符串切片",
        "level": 2,
        "source": "Python100Cases 实例027「递归输出」",
        "desc": "输入一个字符串，用递归方式把它逆序输出（先递归处理后面的字符，再输出当前字符）。",
        "hint": "递归处理 s[1:]，回来后再打印 s[0]，输出顺序自然就反过来了。",
        "ref": """def rev(s):
    if len(s) <= 1:
        print(s, end="")
        return
    rev(s[1:])
    print(s[0], end="")

rev(input())
print()
""",
        "cases": [_c("abc", "cba"), _c("hello", "olleh")],
        "explain": "递归的「回程」顺序等于逆序：最内层先打印最后一个字符，逐层返回时打印前面的字符。\n"
                   "打印用了 end='' 避免每个字符换行，最后单独 print() 补一个换行。\n"
                   "本题只为练递归，实际上一行 s[::-1] 就够了。",
    },
    {
        "id": "E-12",
        "chapter": CHAPTER,
        "no": 12,
        "title": "整数位数与逆序",
        "topic": "字符串 / 数位处理",
        "level": 1,
        "source": "Python100Cases 实例029「反向输出」",
        "desc": (
            "输入一个不多于 5 位的正整数，输出两行：\n"
            "第一行：<位数>位数（如 5位数）；\n"
            "第二行：把它逆序后的数字（如 54321）。"
        ),
        "hint": "转成字符串后，长度就是位数，[::-1] 就是逆序。",
        "ref": """n = input().strip()
print("{}位数".format(len(n)))
print(n[::-1])
""",
        "cases": [_c("12345", "5位数\n54321"), _c("7", "1位数\n7"), _c("1200", "4位数\n0021")],
        "explain": "1200 逆序后是 0021，所以必须按字符串处理，不能先 int()（会变成 21，位数也丢了）。\n"
                   "len() 统计的是字符个数，正好等于十进制位数。\n"
                   "若要输出「数字本身」的逆序（去掉前导 0），再 int() 转换即可。",
    },
    {
        "id": "E-13",
        "chapter": CHAPTER,
        "no": 13,
        "title": "根据首字母判断星期",
        "topic": "字典 / 分支",
        "level": 2,
        "source": "Python100Cases 实例031「字母识词」",
        "desc": (
            "输入星期的首字母（小写），输出对应的英文星期名（首字母大写）。\n"
            "首字母为 t 或 s 时，需要再输入第二个字母才能确定：\n"
            "t+u → Tuesday，t+h → Thursday；s+a → Saturday，s+u → Sunday。\n"
            "其它首字母：m→Monday，w→Wednesday，f→Friday。"
        ),
        "hint": "用字典存首字母到星期的映射；t、s 两项的值再嵌套一层字典，读第二个字母查。",
        "ref": """table = {
    "m": "Monday",
    "w": "Wednesday",
    "f": "Friday",
    "t": {"u": "Tuesday", "h": "Thursday"},
    "s": {"a": "Saturday", "u": "Sunday"},
}

first = input().strip().lower()
value = table[first]
if isinstance(value, dict):
    print(value[input().strip().lower()])
else:
    print(value)
""",
        "cases": [
            _c("m", "Monday"),
            _c("t\nu", "Tuesday"),
            _c("t\nh", "Thursday"),
            _c("s\na", "Saturday"),
            _c("s\nu", "Sunday"),
        ],
        "explain": "「首字母相同」的情况用一种嵌套结构表示：值可能是字符串，也可能是字典。\n"
                   "用 isinstance(value, dict) 判断要不要再读一个字母，避免为 t/s 写两套分支。\n"
                   "注意输入统一转小写，用户输入大写也能识别。",
    },
    {
        "id": "E-14",
        "chapter": CHAPTER,
        "no": 14,
        "title": "猴子分桃",
        "topic": "循环 / 整除验证",
        "level": 3,
        "source": "Python100Cases 实例080「猴子分桃」",
        "desc": (
            "5 只猴子依次分桃：每只猴子把当前的桃子平均分成 5 份后会多出 1 个，\n"
            "它丢掉这 1 个、拿走自己那 1 份，剩下的留给下一只猴子。\n"
            "第 5 只猴子走后还剩至少 1 个桃子。求最开始最少有多少个桃子，输出这个数。"
        ),
        "hint": "从 1 开始枚举总数，按规则模拟 5 轮：必须每轮都满足 (剩-1)%5==0，最后剩下的 >0。",
        "ref": """n = 1
while True:
    t = n
    ok = True
    for i in range(5):
        if (t - 1) % 5 != 0:
            ok = False
            break
        t = (t - 1) // 5 * 4
    if ok and t > 0:
        print(n)
        break
    n += 1
""",
        "cases": [_c("", "3121")],
        "explain": "每轮运算 t = (t-1)//5*4：先扣掉多出的 1 个，分成 5 份，猴子拿走 1 份，剩 4 份。\n"
                   "先判 (t-1)%5 再整除，顺序不能反，否则整除会掩盖「不能均分」的情况。\n"
                   "3121 是经典答案，枚举虽然朴素，但验证次数很少（几千次）。",
    },
    {
        "id": "E-15",
        "chapter": CHAPTER,
        "no": 15,
        "title": "八进制转十进制",
        "topic": "进制转换 / 累加",
        "level": 2,
        "source": "Python100Cases 实例082「八进制转十进制」",
        "desc": "输入一个八进制数（只含 0-7 的数字字符），输出它对应的十进制整数。",
        "hint": "逐位处理：结果 = 结果 × 8 + 当前位数字；也可以用 int(s, 8)。",
        "ref": """s = input().strip()
value = 0
for ch in s:
    value = value * 8 + int(ch)
print(value)
""",
        "cases": [_c("17", "15"), _c("100", "64"), _c("7", "7")],
        "explain": "八进制 17 = 1×8 + 7 = 15；100 = 1×64 = 64。\n"
                   "「乘 8 加当前位」就是霍纳法则，从高位往低位扫一遍即可。\n"
                   "Python 内置的 int(s, 8) 也能一步完成，但本题意在练习进位制的手工换算。",
    },
    {
        "id": "E-16",
        "chapter": CHAPTER,
        "no": 16,
        "title": "杨辉三角",
        "topic": "二维列表 / 递推",
        "level": 2,
        "source": "Python100Cases 实例061「杨辉三角」",
        "desc": (
            "输入行数 n（1~15），输出杨辉三角的前 n 行。\n"
            "每行数字之间用一个空格分隔；每行首尾都是 1，中间的数等于上一行相邻两数之和。"
        ),
        "hint": "第 i 行第 j 个数 = 上一行第 j-1 与第 j 个之和；用二维列表逐行生成。",
        "ref": """n = int(input())
rows = []
for i in range(n):
    row = [1]
    for j in range(1, i):
        row.append(rows[i - 1][j - 1] + rows[i - 1][j])
    if i > 0:
        row.append(1)
    rows.append(row)

for row in rows:
    print(" ".join(str(x) for x in row))
""",
        "cases": [
            _c("5", "1\n1 1\n1 2 1\n1 3 3 1\n1 4 6 4 1"),
            _c("3", "1\n1 1\n1 2 1"),
        ],
        "explain": "第 0 行只有一个 1，第 i 行长度 i+1；首尾的 1 要单独补，中间靠上一行相加。\n"
                   "i > 0 才 append 末尾的 1，否则第一行会变成 [1, 1]。\n"
                   "也可以用组合数公式 C(i, j) 计算每个位置，但递推更直观。",
    },
    {
        "id": "E-17",
        "chapter": CHAPTER,
        "no": 17,
        "title": "报数出圈（约瑟夫问题）",
        "topic": "列表 / 模拟",
        "level": 3,
        "source": "Python100Cases 实例069「报数」",
        "desc": (
            "n 个人围成一圈，从 1 开始依次报数，报到 m 的人出圈，下一个人重新从 1 报数。\n"
            "输入 n 和 m（同一行，空格分隔），按出圈顺序输出这些人的编号，用空格分隔。"
        ),
        "hint": "用列表存 1~n，维护一个下标：每次 (下标 + m - 1) % 当前人数 就是出圈位置，pop 后继续。",
        "ref": """n, m = input().split()
n = int(n)
m = int(m)

people = list(range(1, n + 1))
index = 0
out = []
while people:
    index = (index + m - 1) % len(people)
    out.append(people.pop(index))
print(" ".join(str(x) for x in out))
""",
        "cases": [
            _c("10 3", "3 6 9 2 7 1 8 5 10 4"),
            _c("5 2", "2 4 1 5 3"),
        ],
        "explain": "下标公式 (index + m - 1) % len(people)：先算从当前位置数 m 个人，再对当前人数取模。\n"
                   "pop(index) 取出后，后面的人整体前移一位，所以下一轮不需要额外加 1。\n"
                   "n=10、m=3 的出圈顺序是 3 6 9 2 7 1 8 5 10 4。",
    },
    {
        "id": "E-18",
        "chapter": CHAPTER,
        "no": 18,
        "title": "平方小于 50 就退出",
        "topic": "while / break",
        "level": 1,
        "source": "Python100Cases 实例046「打破循环」",
        "desc": (
            "反复读入整数（每行一个），输出「<数> 的平方是 <平方>」。\n"
            "一旦平方小于 50，再输出「平方小于 50，退出」并结束程序。"
        ),
        "hint": "while True 里读一个数、算平方、打印，判断小于 50 就 break。",
        "ref": """while True:
    n = int(input())
    square = n * n
    print("{} 的平方是 {}".format(n, square))
    if square < 50:
        print("平方小于 50，退出")
        break
""",
        "cases": [
            _c("9\n5\n", "9 的平方是 81\n5 的平方是 25\n平方小于 50，退出"),
            _c("3\n", "3 的平方是 9\n平方小于 50，退出"),
        ],
        "explain": "注意顺序：先输出这一行的平方，再判断是否退出，否则最后一步的平方结果会丢。\n"
                   "while True + break 是最常见的「不确定循环次数」写法。\n"
                   "如果要同时处理非数字输入，可以套 try/except ValueError 并提示重输。",
    },
    {
        "id": "E-19",
        "chapter": CHAPTER,
        "no": 19,
        "title": "乒乓球队比赛名单",
        "topic": "穷举 / 条件筛选",
        "level": 3,
        "source": "Python100Cases 实例022「比赛对手」",
        "desc": (
            "甲队 a、b、c 三人，乙队 x、y、z 三人，一对一比赛。已知：\n"
            "1. a 不和 x 比；2. c 不和 x、z 比。\n"
            "求三人的对手，按 a、b、c 的顺序输出，格式：a-<对手> b-<对手> c-<对手>"
        ),
        "hint": "三重循环枚举 a、b、c 的对手，条件是三人对手互不相同，且满足已知限制。",
        "ref": """for a in "xyz":
    for b in "xyz":
        for c in "xyz":
            if len({a, b, c}) != 3:
                continue
            if a == "x":
                continue
            if c in "xz":
                continue
            print("a-{} b-{} c-{}".format(a, b, c))
""",
        "cases": [_c("", "a-z b-x c-y")],
        "explain": "「c 不和 x、z 比」直接把 c 锁定为 y，于是 a、b 只能分 x、z；再由「a 不和 x 比」定出 a=z、b=x。\n"
                   "用 set 判重（len({a,b,c})==3）保证三人对手互不相同。\n"
                   "枚举 + 过滤是解决这类逻辑题的通用套路，条件写全就不会漏解。",
    },
    {
        "id": "E-20",
        "chapter": CHAPTER,
        "no": 20,
        "title": "闰年判断",
        "topic": "逻辑运算 / 取余",
        "level": 1,
        "source": "常见入门练习（闰年规则）",
        "desc": (
            "输入一个年份，判断它是不是闰年：是输出「是闰年」，否则输出「不是闰年」。\n"
            "规则：能被 4 整除且不能被 100 整除，或者能被 400 整除。"
        ),
        "hint": "把三条规则用 and / or 组合：(y%4==0 and y%100!=0) or y%400==0。",
        "ref": """y = int(input())
if (y % 4 == 0 and y % 100 != 0) or y % 400 == 0:
    print("是闰年")
else:
    print("不是闰年")
""",
        "cases": [_c("2024", "是闰年"), _c("1900", "不是闰年"), _c("2000", "是闰年")],
        "explain": "1900 能被 4 整除，但也能被 100 整除且不能被 400 整除，所以不是闰年。\n"
                   "2000 能被 400 整除，是闰年。\n"
                   "注意运算符优先级：and 高于 or，但加括号更清楚，也避免写错。",
    },

    # ------------------------------------------------------------ 序列
    {
        "id": "E-21",
        "chapter": CHAPTER,
        "no": 21,
        "title": "矩阵主对角线之和",
        "topic": "二维列表 / 下标",
        "level": 1,
        "source": "Python100Cases 实例038「矩阵对角线之和」",
        "desc": "输入一个 3×3 整数矩阵（3 行，每行 3 个数），输出主对角线（左上到右下）元素之和。",
        "hint": "主对角线元素是 m[0][0]、m[1][1]、m[2][2]，用循环 i 取 m[i][i]。",
        "ref": """m = []
for i in range(3):
    m.append([int(x) for x in input().split()])

total = 0
for i in range(3):
    total += m[i][i]
print(total)
""",
        "cases": [
            _c("1 2 3\n4 5 6\n7 8 9", "15"),
            _c("2 0 1\n0 3 0\n1 0 4", "9"),
        ],
        "explain": "主对角线满足行号列号相等；副对角线则是 m[i][n-1-i]。\n"
                   "读入时用列表推导逐行转换，比手动 append 三个数不易出错。\n"
                   "求和也可以写成 sum(m[i][i] for i in range(3))。",
    },
    {
        "id": "E-22",
        "chapter": CHAPTER,
        "no": 22,
        "title": "矩阵相加",
        "topic": "二维列表 / 逐元素运算",
        "level": 2,
        "source": "Python100Cases 实例044「矩阵相加」",
        "desc": (
            "输入两个 3×3 的整数矩阵：先输入第一个矩阵的 3 行，再输入第二个矩阵的 3 行。\n"
            "输出它们相加的结果（3 行，每行 3 个数，用空格分隔）。"
        ),
        "hint": "分别读入两个二维列表，逐元素相加，再逐行输出。",
        "ref": """def read_matrix():
    return [[int(x) for x in input().split()] for _ in range(3)]

a = read_matrix()
b = read_matrix()

for i in range(3):
    row = [a[i][j] + b[i][j] for j in range(3)]
    print(" ".join(str(x) for x in row))
""",
        "cases": [
            _c("12 7 3\n4 5 6\n7 8 9\n5 8 1\n6 7 3\n4 5 9",
               "17 15 4\n10 12 9\n11 13 18"),
        ],
        "explain": "矩阵相加要求两个矩阵同型，对应位置直接相加。\n"
                   "读入封装成 read_matrix() 函数，避免写两遍同样的循环。\n"
                   "注意 3×3 的维度是写死的；要通用一点可以按读入的行数动态处理。",
    },
    {
        "id": "E-23",
        "chapter": CHAPTER,
        "no": 23,
        "title": "有序数组插入",
        "topic": "列表插入 / 顺序查找",
        "level": 2,
        "source": "Python100Cases 实例039「有序列表插入元素」",
        "desc": (
            "第一行输入一组从小到大排好序的整数（空格分隔），第二行输入一个待插入的整数。\n"
            "把新数插入后数组仍保持升序，输出插入后的数组（空格分隔）。"
        ),
        "hint": "append 后用 sort() 最简单；也可以找到第一个大于它的位置 insert。",
        "ref": """nums = [int(x) for x in input().split()]
n = int(input())
nums.append(n)
nums.sort()
print(" ".join(str(x) for x in nums))
""",
        "cases": [
            _c("1 10 100\n50", "1 10 50 100"),
            _c("1 2 3\n0", "0 1 2 3"),
            _c("1 2 3\n9", "1 2 3 9"),
        ],
        "explain": "先 append 再 sort 最简单，但复杂度 O(n log n)；原地插入是 O(n)。\n"
                   "手写插入要处理三个位置：比首元素小（插到 0）、在中间、比末尾大（追加）。\n"
                   "本题重点是把「保持有序」这个不变量想清楚，用 sort 并不丢分。",
    },
    {
        "id": "E-24",
        "chapter": CHAPTER,
        "no": 24,
        "title": "方阵顺时针旋转 90°",
        "topic": "二维列表 / zip",
        "level": 3,
        "source": "Python100Cases 实例068「旋转数列」",
        "desc": (
            "输入一个 4×4 的数字方阵（4 行，每行 4 个整数），输出它顺时针旋转 90° 后的方阵（4 行）。"
        ),
        "hint": "顺时针旋转 = 先上下翻转，再转置；转置用 zip(*matrix)。",
        "ref": """m = [[int(x) for x in input().split()] for _ in range(4)]

rotated = [list(row) for row in zip(*m[::-1])]
for row in rotated:
    print(" ".join(str(x) for x in row))
""",
        "cases": [
            _c("1 2 3 4\n5 6 7 8\n9 10 11 12\n13 14 15 16",
               "13 9 5 1\n14 10 6 2\n15 11 7 3\n16 12 8 4"),
        ],
        "explain": "zip(*m) 按列取出元素，等价于转置；m[::-1] 先倒序行，再转置就得到顺时针 90°。\n"
                   "逆时针 90° 则是 zip(*m) 后倒序列：list(zip(*m))[::-1]。\n"
                   "zip 返回的是元组，用 list(row) 转成列表，打印更符合预期。",
    },
    {
        "id": "E-25",
        "chapter": CHAPTER,
        "no": 25,
        "title": "用逗号连接列表",
        "topic": "join / 类型转换",
        "level": 1,
        "source": "Python100Cases 实例033「列表转字符串」",
        "desc": "输入一行整数（空格分隔），把它们用英文逗号连接成一个字符串输出（数字之间不加空格）。",
        "hint": "join 只能连接字符串，先把每个元素 str() 转换。",
        "ref": """nums = input().split()
print(",".join(nums))
""",
        "cases": [
            _c("1 2 3 4 5", "1,2,3,4,5"),
            _c("10 20", "10,20"),
        ],
        "explain": "join 的参数必须是字符串序列；直接 join 整数列表会报 TypeError。\n"
                   "这里输入本来就是字符串，split 后直接 join 即可，不必先转 int 再转回来。\n"
                   "常见写法：','.join(str(n) for n in nums)。",
    },
    {
        "id": "E-26",
        "chapter": CHAPTER,
        "no": 26,
        "title": "列表转平方字典",
        "topic": "字典推导 / 遍历",
        "level": 2,
        "source": "Python100Cases 实例100「列表转字典」",
        "desc": (
            "输入一行整数（空格分隔），构造字典：键为原数，值为它的平方。\n"
            "按输入顺序输出这个字典（直接打印字典对象即可，如 {1: 1, 2: 4, 3: 9}）。"
        ),
        "hint": "字典推导式 {n: n*n for n in nums}，nums 要先转成 int。",
        "ref": """nums = [int(x) for x in input().split()]
d = {n: n * n for n in nums}
print(d)
""",
        "cases": [
            _c("1 2 3", "{1: 1, 2: 4, 3: 9}"),
            _c("5 5 1", "{5: 25, 1: 1}"),
        ],
        "explain": "用字典推导式一步完成；等价写法是循环 d[n] = n*n。\n"
                   "重复的键（如 5 出现两次）只会保留一个，值被后写的覆盖（这里结果相同）。\n"
                   "打印字典时 Python 保持插入顺序，所以输出顺序与输入一致。",
    },
    {
        "id": "E-27",
        "chapter": CHAPTER,
        "no": 27,
        "title": "列表逆序输出",
        "topic": "切片 / reverse",
        "level": 1,
        "source": "Python100Cases 实例040「逆序列表」",
        "desc": "输入一行整数（空格分隔），把列表逆序后输出（直接打印列表对象）。",
        "hint": "切片 [::-1] 得到新列表；reverse() 原地修改且返回 None。",
        "ref": """nums = [int(x) for x in input().split()]
print(nums[::-1])
""",
        "cases": [
            _c("1 10 100", "[100, 10, 1]"),
            _c("1 2 3 4 5", "[5, 4, 3, 2, 1]"),
        ],
        "explain": "切片 [::-1] 返回新列表，原列表不变；reverse() 原地改，没有返回值。\n"
                   "如果要「逐行输出逆序后的每个元素」，用 for 循环打印而不是打印整个列表。\n"
                   "字符串同理：s[::-1] 就是反转后的字符串。",
    },
    {
        "id": "E-28",
        "chapter": CHAPTER,
        "no": 28,
        "title": "统计列表元素出现次数",
        "topic": "字典计数 / 顺序保持",
        "level": 2,
        "source": "常见练习（元素频次统计）",
        "desc": (
            "输入一行用空格分隔的元素，统计每个元素出现的次数。\n"
            "按元素第一次出现的顺序输出，每行格式：<元素> <次数>"
        ),
        "hint": "用字典计数：counts[x] = counts.get(x, 0) + 1；字典保持插入顺序，直接遍历输出即可。",
        "ref": """items = input().split()
counts = {}
for x in items:
    counts[x] = counts.get(x, 0) + 1

for k, v in counts.items():
    print(k, v)
""",
        "cases": [
            _c("a b a c b a", "a 3\nb 2\nc 1"),
            _c("1 2 1", "1 2\n2 1"),
        ],
        "explain": "get(x, 0) 让首次出现的元素从 0 开始计数，省掉 if 判断。\n"
                   "Python 3.7+ 字典按插入顺序遍历，正好满足「按首次出现顺序」。\n"
                   "如果要按次数降序，用 sorted(counts.items(), key=lambda kv: -kv[1])。",
    },
    {
        "id": "E-29",
        "chapter": CHAPTER,
        "no": 29,
        "title": "矩阵转置",
        "topic": "二维列表 / zip",
        "level": 2,
        "source": "常见练习（矩阵转置）",
        "desc": "输入一个 3×3 整数矩阵（3 行），输出它的转置矩阵（行变列，3 行）。",
        "hint": "zip(*matrix) 按列取出，天然就是转置；记得把元组转成列表再打印。",
        "ref": """m = [[int(x) for x in input().split()] for _ in range(3)]

for col in zip(*m):
    print(" ".join(str(x) for x in col))
""",
        "cases": [
            _c("1 2 3\n4 5 6\n7 8 9", "1 4 7\n2 5 8\n3 6 9"),
            _c("1 0 2\n0 1 0\n3 0 4", "1 0 3\n0 1 0\n2 0 4"),
        ],
        "explain": "zip(*m) 把每一行当作参数展开，于是每次取到的是同一列的元素。\n"
                   "转置两次就回到原矩阵；转置也是判断「对称矩阵」的基础。\n"
                   "不用 zip 的话可以双重循环 res[j][i] = m[i][j]。",
    },
    {
        "id": "E-30",
        "chapter": CHAPTER,
        "no": 30,
        "title": "成绩统计",
        "topic": "列表 / max / sum",
        "level": 1,
        "source": "常见练习（列表统计）",
        "desc": (
            "输入一行分数（空格分隔，至少 1 个），输出格式：\n"
            "最高<最高分> 最低<最低分> 平均<平均分>（平均分保留 2 位小数）"
        ),
        "hint": "转成浮点列表后用 max()、min()、sum()/len()；输出用 {:.2f}。",
        "ref": """scores = [float(x) for x in input().split()]
print("最高{} 最低{} 平均{:.2f}".format(max(scores), min(scores), sum(scores) / len(scores)))
""",
        "cases": [
            _c("90 80 70", "最高90.0 最低70.0 平均80.00"),
            _c("100", "最高100.0 最低100.0 平均100.00"),
        ],
        "explain": "max/min/sum 都接受列表，sum(scores)/len(scores) 就是平均值。\n"
                   "用 float 读入，90 会打印成 90.0；若要打印成 90，可以保留原始字符串或用 :g 格式化。\n"
                   "空列表会让 max() 报错，所以题目限定至少 1 个分数。",
    },

    # ------------------------------------------------------------ 字符串
    {
        "id": "E-31",
        "chapter": CHAPTER,
        "no": 31,
        "title": "字符串长度与反转",
        "topic": "len / 切片",
        "level": 1,
        "source": "Python100Cases 实例060「字符串长度」",
        "desc": "输入一个字符串，输出两行：第一行是长度，第二行是反转后的字符串。",
        "hint": "len(s) 取长度，s[::-1] 反转。",
        "ref": """s = input()
print(len(s))
print(s[::-1])
""",
        "cases": [_c("hello", "5\nolleh"), _c("a", "1\na")],
        "explain": "len 统计字符个数，中文也算一个字符（Python 3 的字符串是 Unicode）。\n"
                   "s[::-1] 是切片反转，不影响原字符串。\n"
                   "如果输入可能带空格，注意不要用 split() 丢掉空格。",
    },
    {
        "id": "E-32",
        "chapter": CHAPTER,
        "no": 32,
        "title": "查找子串",
        "topic": "find / count",
        "level": 2,
        "source": "Python100Cases 实例062「查找字符串」",
        "desc": (
            "输入两行：第一行是主串，第二行是要查找的子串。输出两行：\n"
            "第一行：首次出现的位置（找不到输出 -1）；\n"
            "第二行：出现的次数。"
        ),
        "hint": "find 返回首次下标（找不到 -1），count 统计出现次数。",
        "ref": """text = input()
sub = input()
print("首次位置：{}".format(text.find(sub)))
print("出现次数：{}".format(text.count(sub)))
""",
        "cases": [
            _c("ababab\nab", "首次位置：0\n出现次数：3"),
            _c("hello\nzz", "首次位置：-1\n出现次数：0"),
        ],
        "explain": "find 找不到返回 -1，而 index 会抛 ValueError，查表用 find 更安全。\n"
                   "count 统计的是不重叠的出现次数：\"aaa\".count(\"aa\") 结果是 1。\n"
                   "要区分大小写；忽略大小写可以两边先 lower()。",
    },
    {
        "id": "E-33",
        "chapter": CHAPTER,
        "no": 33,
        "title": "字符分类统计",
        "topic": "isalpha / isdigit / isspace",
        "level": 2,
        "source": "Python100Cases 实例017「字符串构成」",
        "desc": (
            "输入一行字符，分别统计英文字母、数字、空格和其它字符的个数，输出格式：\n"
            "字母:<a> 数字:<b> 空格:<c> 其他:<d>"
        ),
        "hint": "遍历字符，用 isalpha()、isdigit()、isspace() 依次判断，剩下的归为其它。",
        "ref": """s = input()
alpha = digit = space = other = 0
for ch in s:
    if ch.isalpha():
        alpha += 1
    elif ch.isdigit():
        digit += 1
    elif ch.isspace():
        space += 1
    else:
        other += 1
print("字母:{} 数字:{} 空格:{} 其他:{}".format(alpha, digit, space, other))
""",
        "cases": [
            _c("a1 b!", "字母:2 数字:1 空格:1 其他:1"),
            _c("Hello 2026", "字母:5 数字:4 空格:1 其他:0"),
        ],
        "explain": "isalpha 对汉字也返回 True，所以本统计会把中文算作字母；要只统计英文需用范围判断。\n"
                   "isdigit 与 isdecimal 的区别：上标 ² 算 digit 但不算 decimal。\n"
                   "四个计数器用一条 if-elif 链，最后 else 兜住其它字符，不会重复统计。",
    },
    {
        "id": "E-34",
        "chapter": CHAPTER,
        "no": 34,
        "title": "字符串排序",
        "topic": "sorted / join",
        "level": 1,
        "source": "Python100Cases 实例079「字符串排序」",
        "desc": "输入一个只含英文字母的字符串，把它的字符按升序排列后输出。",
        "hint": "sorted(s) 返回字符列表，再用 \"\".join 拼回字符串。",
        "ref": """s = input()
print("".join(sorted(s)))
""",
        "cases": [
            _c("cba", "abc"),
            _c("hello", "ehllo"),
        ],
        "explain": "sorted 对字符按 Unicode 码位排序，小写字母 a-z 是连续的一段。\n"
                   "大写字母（A-Z）的码位比小写小，所以 \"Zz\" 排序会变成 \"Zz\" 而不是 \"zZ\"。\n"
                   "要忽略大小写，可以 sorted(s, key=str.lower)。",
    },
    {
        "id": "E-35",
        "chapter": CHAPTER,
        "no": 35,
        "title": "凯撒密码（后移 3 位）",
        "topic": "ord / chr / 取模",
        "level": 3,
        "source": "Python100Cases 实例089「解码」",
        "desc": (
            "把字符串中的英文字母向后移动 3 位（a→d，…，x→a，y→b，z→c），"
            "大写字母同理，非字母字符保持不变。输出加密后的字符串。"
        ),
        "hint": "小写：(ord(ch)-97+3)%26+97，再用 chr 转回字符；大写把 97/65 换掉。",
        "ref": """def shift(ch, k=3):
    if "a" <= ch <= "z":
        return chr((ord(ch) - 97 + k) % 26 + 97)
    if "A" <= ch <= "Z":
        return chr((ord(ch) - 65 + k) % 26 + 65)
    return ch

s = input()
print("".join(shift(ch) for ch in s))
""",
        "cases": [
            _c("abc xyz", "def abc"),
            _c("Hello, World!", "Khoor, Zruog!"),
        ],
        "explain": "关键是先减去基准（a 的 97 或 A 的 65）归零，加位移后对 26 取模，再加回基准。\n"
                   "不取模的话 z+3 会变成 '}' 这种非字母字符。\n"
                   "大小写要分开处理，否则大写字母会落到小写区间。",
    },
    {
        "id": "E-36",
        "chapter": CHAPTER,
        "no": 36,
        "title": "字符出现次数（按首次顺序）",
        "topic": "字典计数 / 字符串遍历",
        "level": 2,
        "source": "常见练习（字符频次）",
        "desc": "输入一个字符串，统计每个字符出现的次数，按字符首次出现的顺序输出，每行：<字符> <次数>",
        "hint": "遍历字符串用字典计数，再遍历字典输出。",
        "ref": """s = input()
counts = {}
for ch in s:
    counts[ch] = counts.get(ch, 0) + 1

for ch, n in counts.items():
    print(ch, n)
""",
        "cases": [
            _c("hello", "h 1\ne 1\nl 2\no 1"),
            _c("aabb", "a 2\nb 2"),
        ],
        "explain": "字典的键是字符，值出现次数；插入顺序就是首次出现顺序。\n"
                   "空格也是字符，会被统计，输入时注意不要多加空格。\n"
                   "要按次数排序，用 sorted(counts.items(), key=lambda kv: -kv[1])。",
    },
    {
        "id": "E-37",
        "chapter": CHAPTER,
        "no": 37,
        "title": "字符串压缩",
        "topic": "游程编码 / 双指针",
        "level": 2,
        "source": "常见练习（行程长度编码）",
        "desc": (
            "把连续重复的字符压缩成「字符+次数」的形式。\n"
            "例如 aaabbc 压缩为 a3b2c1；单个字符也要带次数，如 a 压缩为 a1。"
        ),
        "hint": "用双指针：i 指向当前字符，j 往后找相同字符的边界，输出 字符 + (j-i)。",
        "ref": """s = input()
out = []
i = 0
while i < len(s):
    j = i
    while j < len(s) and s[j] == s[i]:
        j += 1
    out.append("{}{}".format(s[i], j - i))
    i = j
print("".join(out))
""",
        "cases": [
            _c("aaabbc", "a3b2c1"),
            _c("a", "a1"),
            _c("abcd", "a1b1c1d1"),
        ],
        "explain": "j 一直走到与 s[i] 不同的位置，j-i 就是这组重复字符的长度。\n"
                   "处理后把 i 跳到 j，避免重复扫描同一段。\n"
                   "这种编码叫游程编码（RLE），压缩率高不高取决于原文重复程度——abcd 反而变长了。",
    },
    {
        "id": "E-38",
        "chapter": CHAPTER,
        "no": 38,
        "title": "字符串解压",
        "topic": "字符串解析 / 数字提取",
        "level": 3,
        "source": "常见练习（游程解码）",
        "desc": (
            "输入压缩后的字符串（形式为「字符+次数」，如 a3b2c1），还原成原字符串。\n"
            "次数可能是一位或多位数（如 a12）。"
        ),
        "hint": "遍历：遇到字母记下来，继续往后读连续数字拼成次数，再重复该字母。",
        "ref": """s = input()
out = []
i = 0
while i < len(s):
    ch = s[i]
    j = i + 1
    num = ""
    while j < len(s) and s[j].isdigit():
        num += s[j]
        j += 1
    out.append(ch * int(num))
    i = j
print("".join(out))
""",
        "cases": [
            _c("a3b2c1", "aaabbc"),
            _c("a1", "a"),
            _c("x12", "xxxxxxxxxxxx"),
        ],
        "explain": "次数可能是多位数，所以要一直读到非数字为止，不能只取一位。\n"
                   "ch * int(num) 利用字符串乘法快速重复。\n"
                   "本题是上一题（压缩）的逆过程，两题一起做能理解游程编码的双向还原。",
    },
    {
        "id": "E-39",
        "chapter": CHAPTER,
        "no": 39,
        "title": "全字母 / 全数字判断",
        "topic": "isalpha / isdigit",
        "level": 1,
        "source": "常见练习（字符串类型判断）",
        "desc": (
            "输入一个字符串，判断它的组成：\n"
            "全是英文字母 → 输出「全字母」；\n"
            "全是数字 → 输出「全数字」；\n"
            "否则 → 输出「混合」。\n"
            "（空字符串按混合处理）"
        ),
        "hint": "s.isalpha() 与 s.isdigit() 直接判断整串，注意空串两者都是 False。",
        "ref": """s = input()
if s.isalpha():
    print("全字母")
elif s.isdigit():
    print("全数字")
else:
    print("混合")
""",
        "cases": [
            _c("abc", "全字母"),
            _c("123", "全数字"),
            _c("a1", "混合"),
            _c("abc def", "混合"),
        ],
        "explain": "isalpha/isdigit 判断的是「整串每个字符都满足」，空串返回 False，正好落到混合。\n"
                   "含空格、下划线、小数点都算混合；要允许它们需要自己写规则。\n"
                   "注意 isalpha 对汉字也返回 True，本题按「英文字母」理解即可。",
    },
    {
        "id": "E-40",
        "chapter": CHAPTER,
        "no": 40,
        "title": "邮箱格式简单校验",
        "topic": "字符串校验 / 综合",
        "level": 2,
        "source": "常见练习（表单校验）",
        "desc": (
            "校验输入是否为「简单合法」的邮箱，规则：\n"
            "1. 恰好包含一个 @；\n"
            "2. @ 前面至少 1 个字符，@ 后面至少 1 个字符；\n"
            "3. 域名部分至少包含一个点，且点不在开头、不在结尾。\n"
            "合法输出「格式正确」，否则输出「格式错误」。"
        ),
        "hint": "先 count('@')==1，再按 @ 切分成两段，检查长度；域名段用点切分检查每段非空且至少两段。",
        "ref": """s = input().strip()

if s.count("@") != 1:
    print("格式错误")
else:
    name, domain = s.split("@")
    parts = domain.split(".")
    if not name:
        print("格式错误")
    elif len(parts) < 2 or any(p == "" for p in parts):
        print("格式错误")
    else:
        print("格式正确")
""",
        "cases": [
            _c("a@b.com", "格式正确"),
            _c("ab.com", "格式错误"),
            _c("@b.com", "格式错误"),
            _c("a@b.", "格式错误"),
            _c("a@b", "格式错误"),
        ],
        "explain": "count('@') != 1 一次性挡掉没有 @ 和多个 @ 的情况。\n"
                   "域名用点切分后要求「至少两段且没有空段」，正好覆盖「没有点」「点开头」「点结尾」。\n"
                   "这是教学用的简化规则，真实邮箱校验要用正则且规则更复杂。",
    },
]
