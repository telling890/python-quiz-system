# -*- coding: utf-8 -*-
"""进阶算法 · 30 道（排序 / 查找 / 递归 / 简单动态规划）

面向学完教材三章、想继续练算法的同学。题目都是算法入门经典题材，
题干按本系统的判题约定重写，参考答案与用例自行编写。

约定：除非特别说明，输入都是「一行整数，空格分隔」，输出都是最终结果，
不输出中间过程，保证判题唯一。
"""

CHAPTER = "进阶算法"


def _c(stdin, expect):
    return {"stdin": stdin, "expect": expect}


QUESTIONS = [
    # ------------------------------------------------------------ 排序
    {
        "id": "A-01",
        "chapter": CHAPTER,
        "no": 1,
        "title": "冒泡排序",
        "topic": "排序 / 相邻交换",
        "level": 2,
        "source": "经典算法练习（排序）",
        "desc": "输入一行整数，用冒泡排序（相邻两两比较交换）从小到大排序后输出，数字之间用空格分隔。",
        "hint": "外层跑 n-1 轮，内层从头比较相邻两个，逆序就交换；每轮结束末尾就固定了一个最大值。",
        "ref": """nums = [int(x) for x in input().split()]
n = len(nums)
for i in range(n - 1):
    swapped = False
    for j in range(n - 1 - i):
        if nums[j] > nums[j + 1]:
            nums[j], nums[j + 1] = nums[j + 1], nums[j]
            swapped = True
    if not swapped:
        break
print(" ".join(str(x) for x in nums))
""",
        "cases": [
            _c("3 1 2", "1 2 3"),
            _c("5 4 3 2 1", "1 2 3 4 5"),
            _c("1 2 3", "1 2 3"),
        ],
        "explain": "每轮把当前未排序部分的最大值「冒」到末尾，所以内层上界可以每轮减 1。\n"
                   "swapped 标记是优化：一轮下来没发生交换就说明已经有序，可以提前结束。\n"
                   "最坏 O(n²)，但它是稳定排序（相等元素不会交换位置）。",
    },
    {
        "id": "A-02",
        "chapter": CHAPTER,
        "no": 2,
        "title": "选择排序",
        "topic": "排序 / 最小值选择",
        "level": 2,
        "source": "经典算法练习（排序）",
        "desc": "输入一行整数，用选择排序（每轮选出最小值放到前面）从小到大排序后输出。",
        "hint": "第 i 轮在 i..n-1 里找最小值的下标，和位置 i 交换。",
        "ref": """nums = [int(x) for x in input().split()]
n = len(nums)
for i in range(n - 1):
    min_idx = i
    for j in range(i + 1, n):
        if nums[j] < nums[min_idx]:
            min_idx = j
    if min_idx != i:
        nums[i], nums[min_idx] = nums[min_idx], nums[i]
print(" ".join(str(x) for x in nums))
""",
        "cases": [
            _c("3 1 2", "1 2 3"),
            _c("9 7 5 3 1", "1 3 5 7 9"),
        ],
        "explain": "每轮确定一个位置的最终值，交换次数最多 n-1 次，比冒泡少。\n"
                   "比较次数固定为 n(n-1)/2，与初始顺序无关，所以没有「已有序」的提前结束优化。\n"
                   "选择排序是不稳定的：交换可能把相等元素的前后顺序打乱。",
    },
    {
        "id": "A-03",
        "chapter": CHAPTER,
        "no": 3,
        "title": "插入排序",
        "topic": "排序 / 逐步插入",
        "level": 2,
        "source": "经典算法练习（排序）",
        "desc": "输入一行整数，用插入排序（把每个元素插入到前面已排好序的序列中）从小到大排序后输出。",
        "hint": "从第 2 个元素开始，把它暂存起来，往前找位置：比它大的元素依次后移，最后填回空位。",
        "ref": """nums = [int(x) for x in input().split()]
for i in range(1, len(nums)):
    key = nums[i]
    j = i - 1
    while j >= 0 and nums[j] > key:
        nums[j + 1] = nums[j]
        j -= 1
    nums[j + 1] = key
print(" ".join(str(x) for x in nums))
""",
        "cases": [
            _c("5 2 4 6 1 3", "1 2 3 4 5 6"),
            _c("2 1", "1 2"),
        ],
        "explain": "插入排序像整理扑克牌：手里已有的牌有序，新牌插到合适位置。\n"
                   "内层 while 一边比较一边后移，最后 j+1 就是插入点。\n"
                   "对基本有序的数据很快（接近 O(n)），是很多库内部对小数组使用的排序。",
    },
    {
        "id": "A-04",
        "chapter": CHAPTER,
        "no": 4,
        "title": "二分查找",
        "topic": "查找 / 折半",
        "level": 2,
        "source": "经典算法练习（查找）",
        "desc": (
            "第一行输入一组升序排列的整数，第二行输入要查找的目标值。\n"
            "输出目标值在数组中的下标（从 0 开始）；找不到输出 -1。"
        ),
        "hint": "维护 left、right 两个指针，每次比较中间元素，缩小一半区间。",
        "ref": """nums = [int(x) for x in input().split()]
target = int(input())

left, right = 0, len(nums) - 1
answer = -1
while left <= right:
    mid = (left + right) // 2
    if nums[mid] == target:
        answer = mid
        break
    if nums[mid] < target:
        left = mid + 1
    else:
        right = mid - 1
print(answer)
""",
        "cases": [
            _c("1 3 5 7 9\n7", "3"),
            _c("1 3 5\n4", "-1"),
            _c("1 2 3 4 5\n1", "0"),
        ],
        "explain": "循环条件是 left <= right，用 < 会漏掉区间只剩一个元素的情况。\n"
                   "mid 用 (left+right)//2，整数除法；写成 / 会得到浮点数，不能当下标。\n"
                   "时间复杂度 O(log n)，但数组必须有序——无序时二分是错的。",
    },
    {
        "id": "A-05",
        "chapter": CHAPTER,
        "no": 5,
        "title": "快速排序",
        "topic": "递归 / 分治",
        "level": 3,
        "source": "经典算法练习（排序）",
        "desc": "输入一行整数，用快速排序（选基准、分成小于/大于基准的两部分，再递归）从小到大排序后输出。",
        "hint": "取第一个元素为基准，用列表推导分成 left/right 两部分，再递归排序并拼接。",
        "ref": """def quick_sort(nums):
    if len(nums) <= 1:
        return nums
    pivot = nums[0]
    left = [x for x in nums[1:] if x < pivot]
    right = [x for x in nums[1:] if x >= pivot]
    return quick_sort(left) + [pivot] + quick_sort(right)

nums = [int(x) for x in input().split()]
print(" ".join(str(x) for x in quick_sort(nums)))
""",
        "cases": [
            _c("3 1 2", "1 2 3"),
            _c("5 3 8 1 9 2", "1 2 3 5 8 9"),
        ],
        "explain": "递归的基线条件：长度 ≤ 1 时天然有序。\n"
                   "用列表推导分组比原地双指针好写，代价是额外的内存；right 用 >= 保证相等元素不丢。\n"
                   "平均 O(n log n)，最坏（每次基准都是最值）退化为 O(n²)；随机选基准可以缓解。",
    },
    {
        "id": "A-06",
        "chapter": CHAPTER,
        "no": 6,
        "title": "最大子段和",
        "topic": "动态规划 / 贪心",
        "level": 3,
        "source": "经典算法练习（Kadane 算法）",
        "desc": "输入一行整数（可能有负数），求连续子数组的最大和，输出这个和。",
        "hint": "Kadane：维护「以当前元素结尾的最大和」，若它变成负数就重新从当前元素开始。",
        "ref": """nums = [int(x) for x in input().split()]

best = current = nums[0]
for x in nums[1:]:
    current = max(x, current + x)
    best = max(best, current)
print(best)
""",
        "cases": [
            _c("1 -2 3 10 -4 7 2 -5", "18"),
            _c("-3 -1 -2", "-1"),
            _c("5", "5"),
        ],
        "explain": "current = max(x, current + x) 的含义：前面的和如果是负数，就不如从自己重新开始。\n"
                   "必须同时记录 best，因为最大和可能出现在中间而不是末尾。\n"
                   "全负数时答案是最小的那个负数（单个元素），所以初值取 nums[0] 而不是 0。",
    },
    {
        "id": "A-07",
        "chapter": CHAPTER,
        "no": 7,
        "title": "两数之和（返回下标）",
        "topic": "字典 / 一次遍历",
        "level": 2,
        "source": "经典算法练习（哈希表）",
        "desc": (
            "第一行输入一组整数，第二行输入目标值 target。\n"
            "找出数组中两个下标 i < j，使 nums[i] + nums[j] == target，输出「i j」。\n"
            "保证至少有一组解；若有多组，输出第一组（i 最小的）。"
        ),
        "hint": "遍历时用字典记录「值 → 下标」，对每个值查 target - 值 是否出现过。",
        "ref": """nums = [int(x) for x in input().split()]
target = int(input())

seen = {}
answer = None
for i, x in enumerate(nums):
    need = target - x
    if need in seen:
        answer = (seen[need], i)
        break
    seen[x] = i
print("{} {}".format(answer[0], answer[1]))
""",
        "cases": [
            _c("2 7 11 15\n9", "0 1"),
            _c("3 2 4\n6", "1 2"),
            _c("3 3\n6", "0 1"),
        ],
        "explain": "边遍历边建表，保证找到的下标是「前面的那个 + 当前」，天然满足 i < j。\n"
                   "先查后存（而不是先存后查）可以避免同一个元素用两次：3 3 求和 6 必须用两个不同位置。\n"
                   "复杂度 O(n)，比双重循环的 O(n²) 快一个量级。",
    },
    {
        "id": "A-08",
        "chapter": CHAPTER,
        "no": 8,
        "title": "最长递增子序列长度",
        "topic": "动态规划",
        "level": 3,
        "source": "经典算法练习（LIS）",
        "desc": "输入一行整数，求「最长严格递增子序列」的长度（子序列不要求连续），输出这个长度。",
        "hint": "dp[i] 表示以第 i 个元素结尾的最长递增子序列长度，内层枚举 j < i 且 nums[j] < nums[i]。",
        "ref": """nums = [int(x) for x in input().split()]
n = len(nums)
dp = [1] * n
for i in range(n):
    for j in range(i):
        if nums[j] < nums[i]:
            dp[i] = max(dp[i], dp[j] + 1)
print(max(dp))
""",
        "cases": [
            _c("10 9 2 5 3 7 101 18", "4"),
            _c("1 2 3", "3"),
            _c("5 4 3", "1"),
        ],
        "explain": "dp 的每一项至少是 1（只有自己），然后看前面有没有能接上的更小元素。\n"
                   "答案是 max(dp) 而不是 dp[-1]：最长的那一段不一定以最后一个元素结尾。\n"
                   "O(n²) 写法最好理解；进阶有 O(n log n) 的贪心 + 二分写法。",
    },
    {
        "id": "A-09",
        "chapter": CHAPTER,
        "no": 9,
        "title": "爬楼梯",
        "topic": "动态规划 / 递推",
        "level": 2,
        "source": "经典算法练习（斐波那契型 DP）",
        "desc": "一次可以爬 1 阶或 2 阶，问爬到第 n 阶共有多少种走法，输出这个数（n ≥ 1）。",
        "hint": "f(n) = f(n-1) + f(n-2)，f(1)=1、f(2)=2；只保留前两个值滚动即可。",
        "ref": """n = int(input())
if n == 1:
    print(1)
else:
    a, b = 1, 2
    for i in range(3, n + 1):
        a, b = b, a + b
    print(b)
""",
        "cases": [_c("1", "1"), _c("2", "2"), _c("5", "8")],
        "explain": "最后一步要么从 n-1 跨 1 阶，要么从 n-2 跨 2 阶，所以是前两项之和。\n"
                   "这就是斐波那契数列的变形（从 1、2 开始）。\n"
                   "用两个变量滚动，空间 O(1)；递归写法会指数级重复计算。",
    },
    {
        "id": "A-10",
        "chapter": CHAPTER,
        "no": 10,
        "title": "0/1 背包",
        "topic": "动态规划 / 二维转一维",
        "level": 3,
        "source": "经典算法练习（背包问题）",
        "desc": (
            "第一行输入背包容量 W，第二行输入物品件数 n，接下来 n 行每行两个整数：重量 和 价值。\n"
            "每件物品只能取或不取，求能装下的最大总价值，输出这个值。"
        ),
        "hint": "一维 dp：dp[c] 表示容量 c 的最大价值；遍历每件物品，容量从 W 倒着更新到 w。",
        "ref": """W = int(input())
n = int(input())
dp = [0] * (W + 1)

for _ in range(n):
    w, v = [int(x) for x in input().split()]
    for c in range(W, w - 1, -1):
        dp[c] = max(dp[c], dp[c - w] + v)

print(dp[W])
""",
        "cases": [
            _c("5\n3\n2 3\n3 4\n4 5", "7"),
            _c("4\n1\n4 5", "5"),
            _c("10\n4\n5 10\n4 40\n6 30\n3 50", "90"),
        ],
        "explain": "容量必须倒着更新：正着更新会让同一件物品被重复放多次（那就变成完全背包了）。\n"
                   "dp[c - w] + v 表示「留出 w 的空间后，剩余容量能装的最大价值」再加上本件价值。\n"
                   "答案在 dp[W]，不是 dp 的最大值（容量越大价值不会更小，这里二者相同，但习惯取 dp[W]）。",
    },
    {
        "id": "A-11",
        "chapter": CHAPTER,
        "no": 11,
        "title": "数字三角形最大路径和",
        "topic": "动态规划 / 自底向上",
        "level": 3,
        "source": "经典算法练习（数字三角形）",
        "desc": (
            "输入一个数字三角形：第一行是行数 n，之后每行 i 有 i 个整数。\n"
            "从顶部出发，每次只能走到下一行的相邻位置，求到底部的路径最大和。"
        ),
        "hint": "自底向上：从倒数第二行开始，每个元素加上它下方两个相邻元素中的较大者，最后三角形顶部就是答案。",
        "ref": """n = int(input())
tri = [[int(x) for x in input().split()] for _ in range(n)]

for i in range(n - 2, -1, -1):
    for j in range(len(tri[i])):
        tri[i][j] += max(tri[i + 1][j], tri[i + 1][j + 1])
print(tri[0][0])
""",
        "cases": [
            _c("5\n7\n3 8\n8 1 0\n2 7 4 4\n4 5 2 6 5", "30"),
            _c("1\n5", "5"),
        ],
        "explain": "自底向上避免了重复计算，也不需要额外数组（直接在原三角形上累加）。\n"
                   "状态转移：tri[i][j] += max(下一行同列, 下一行下一列)。\n"
                   "自顶向下要处理边界并保存记忆表，写起来更啰嗦。",
    },
    {
        "id": "A-12",
        "chapter": CHAPTER,
        "no": 12,
        "title": "求众数",
        "topic": "字典计数 / 打擂台",
        "level": 1,
        "source": "经典算法练习（计数）",
        "desc": "输入一行整数（保证众数唯一），输出出现次数最多的那个数。",
        "hint": "用字典计数，再找最大值对应的键；也可以用 list.count 打擂台。",
        "ref": """nums = [int(x) for x in input().split()]
counts = {}
for x in nums:
    counts[x] = counts.get(x, 0) + 1

best = max(counts, key=lambda k: counts[k])
print(best)
""",
        "cases": [
            _c("1 3 3 2 3", "3"),
            _c("4 4 1 2", "4"),
        ],
        "explain": "max(counts, key=...) 直接返回字典里按自定义规则最大化的键。\n"
                   "题目保证众数唯一，所以不用处理并列；如果并列，可以再按数值取最小。\n"
                   "如果要 O(1) 空间且众数超过一半，可以用摩尔投票法。",
    },
    # ------------------------------------------------------------ 数组操作
    {
        "id": "A-13",
        "chapter": CHAPTER,
        "no": 13,
        "title": "移动零到末尾",
        "topic": "双指针 / 原地",
        "level": 2,
        "source": "经典算法练习（双指针）",
        "desc": "输入一行整数，把所有 0 移到末尾，非零元素保持原来的相对顺序，输出处理后的数组。",
        "hint": "双指针：j 记录非零元素应放的位置，遍历时遇到非零就写到 j 并 j+=1，最后把 j 之后补 0。",
        "ref": """nums = [int(x) for x in input().split()]

j = 0
for i in range(len(nums)):
    if nums[i] != 0:
        nums[j] = nums[i]
        j += 1
for k in range(j, len(nums)):
    nums[k] = 0
print(" ".join(str(x) for x in nums))
""",
        "cases": [
            _c("0 1 0 3 12", "1 3 12 0 0"),
            _c("0 0 1", "1 0 0"),
            _c("1 2 3", "1 2 3"),
        ],
        "explain": "就地覆盖避免了额外的数组，j 始终指向「下一个非零元素该放的位置」。\n"
                   "非零元素之间的相对顺序自然保持不变，因为按原顺序依次写入。\n"
                   "最后把剩余位置统一填 0 即可，不需要再移动。",
    },
    {
        "id": "A-14",
        "chapter": CHAPTER,
        "no": 14,
        "title": "原地反转数组",
        "topic": "双指针 / 交换",
        "level": 1,
        "source": "经典算法练习（双指针）",
        "desc": "输入一行整数，输出逆序后的数组（用首尾交换实现，不借助额外数组）。",
        "hint": "i 从头、j 从尾，交换后 i+=1、j-=1，直到 i >= j。",
        "ref": """nums = [int(x) for x in input().split()]
i, j = 0, len(nums) - 1
while i < j:
    nums[i], nums[j] = nums[j], nums[i]
    i += 1
    j -= 1
print(" ".join(str(x) for x in nums))
""",
        "cases": [
            _c("1 2 3", "3 2 1"),
            _c("1 2 3 4", "4 3 2 1"),
            _c("7", "7"),
        ],
        "explain": "交换只需要走到中间：i < j 保证每对只换一次，偶数长度时 i 和 j 会错过。\n"
                   "并行赋值 a, b = b, a 不需要临时变量。\n"
                   "原地反转是很多题的前置操作（比如旋转数组）。",
    },
    {
        "id": "A-15",
        "chapter": CHAPTER,
        "no": 15,
        "title": "合并两个有序数组",
        "topic": "双指针 / 归并",
        "level": 2,
        "source": "经典算法练习（归并）",
        "desc": (
            "输入两行，每行是升序排列的整数。把它们合并成一个仍然升序的数组，输出结果。\n"
            "要求用双指针逐个取较小值，而不是直接拼起来再排序。"
        ),
        "hint": "两个指针分别指向两个数组开头，每次把较小的那个放进结果并后移，最后把剩下的接上。",
        "ref": """a = [int(x) for x in input().split()]
b = [int(x) for x in input().split()]

i = j = 0
out = []
while i < len(a) and j < len(b):
    if a[i] <= b[j]:
        out.append(a[i])
        i += 1
    else:
        out.append(b[j])
        j += 1
out.extend(a[i:])
out.extend(b[j:])
print(" ".join(str(x) for x in out))
""",
        "cases": [
            _c("1 3 5\n2 4 6", "1 2 3 4 5 6"),
            _c("1 2\n3 4", "1 2 3 4"),
            _c("1 5\n2", "1 2 5"),
        ],
        "explain": "两个指针各走一遍，复杂度 O(m+n)，这正是归并排序的合并步骤。\n"
                   "比较用 <= 保证相等时优先取前一个数组的元素（保持稳定）。\n"
                   "循环结束后一定有一个数组有剩余，用 extend 直接接上，不用再比较。",
    },
    {
        "id": "A-16",
        "chapter": CHAPTER,
        "no": 16,
        "title": "括号匹配",
        "topic": "栈",
        "level": 3,
        "source": "经典算法练习（栈）",
        "desc": (
            "输入一个只含 ()、[]、{} 的字符串，判断括号是否配对：\n"
            "配对输出「匹配」，否则输出「不匹配」。"
        ),
        "hint": "遇左括号入栈；遇右括号时栈顶必须是它的左括号，否则不匹配；结束时栈必须为空。",
        "ref": """s = input().strip()
pairs = {")": "(", "]": "[", "}": "{"}
stack = []
ok = True

for ch in s:
    if ch in "([{":
        stack.append(ch)
    elif ch in pairs:
        if not stack or stack[-1] != pairs[ch]:
            ok = False
            break
        stack.pop()

if stack:
    ok = False
print("匹配" if ok else "不匹配")
""",
        "cases": [
            _c("([]{})", "匹配"),
            _c("(]", "不匹配"),
            _c("([)]", "不匹配"),
            _c("((", "不匹配"),
        ],
        "explain": "「([)]」不匹配：右括号必须和最近的未闭合左括号配对，这正是栈的后进先出。\n"
                   "两个容易漏的边界：栈空时来了右括号（如 \")\"）、扫描完栈里还有左括号（如 \"(\"）。\n"
                   "用字典把右括号映射到左括号，判断逻辑最简洁。",
    },
    {
        "id": "A-17",
        "chapter": CHAPTER,
        "no": 17,
        "title": "十进制转二进制",
        "topic": "进制转换 / 循环",
        "level": 2,
        "source": "经典算法练习（进制）",
        "desc": "输入一个非负整数，输出它的二进制表示（不能用 bin() 直接转换）。",
        "hint": "不断对 2 取余得到低位，除以 2 继续；把余数逆序拼起来。",
        "ref": """n = int(input())
if n == 0:
    print("0")
else:
    bits = []
    while n > 0:
        bits.append(str(n % 2))
        n //= 2
    print("".join(reversed(bits)))
""",
        "cases": [_c("10", "1010"), _c("0", "0"), _c("255", "11111111")],
        "explain": "每次取余得到的是最低位，所以要逆序拼接。\n"
                   "n 必须用 // 整除，用 / 会得到浮点数导致死循环。\n"
                   "0 需要单独处理：while 0 > 0 不执行，否则会输出空字符串。",
    },
    {
        "id": "A-18",
        "chapter": CHAPTER,
        "no": 18,
        "title": "最大公约数（递归）",
        "topic": "递归 / 辗转相除",
        "level": 2,
        "source": "经典算法练习（递归）",
        "desc": "输入两个正整数（同一行），用递归实现欧几里得算法求最大公约数，输出结果。",
        "hint": "gcd(a,b) = gcd(b, a%b)；基线条件 b == 0 时返回 a。",
        "ref": """def gcd(a, b):
    if b == 0:
        return a
    return gcd(b, a % b)

a, b = [int(x) for x in input().split()]
print(gcd(a, b))
""",
        "cases": [
            _c("12 18", "6"),
            _c("7 5", "1"),
            _c("100 75", "25"),
        ],
        "explain": "基线条件必须是 b == 0（返回 a），写成 a == b 就只能在相同时结束。\n"
                   "a % b 会严格变小，所以递归一定会终止。\n"
                   "最小公倍数 = a*b // gcd，注意先乘后除。",
    },
    {
        "id": "A-19",
        "chapter": CHAPTER,
        "no": 19,
        "title": "汉诺塔移动次数",
        "topic": "递归 / 递推",
        "level": 2,
        "source": "经典算法练习（汉诺塔）",
        "desc": "有三根柱子，把 n 个盘子从起始柱全部移到目标柱（每次只能移一个，大盘不能压在小盘上）。输出最少移动次数。",
        "hint": "f(n) = 2*f(n-1) + 1，f(1)=1；闭式解是 2^n - 1。",
        "ref": """n = int(input())
moves = 0
for i in range(n):
    moves = moves * 2 + 1
print(moves)
""",
        "cases": [_c("1", "1"), _c("3", "7"), _c("10", "1023")],
        "explain": "思路：先把上面 n-1 个盘子移到辅助柱，再把最大的移到目标柱，最后把那 n-1 个移过来。\n"
                   "所以 f(n) = 2f(n-1) + 1，展开就是 2^n - 1。\n"
                   "n=64 时需要约 1.8×10^19 次，按每秒一次要几百亿年——这就是汉诺塔的传说来源。",
    },
    {
        "id": "A-20",
        "chapter": CHAPTER,
        "no": 20,
        "title": "埃氏筛求素数个数",
        "topic": "筛选法 / 布尔数组",
        "level": 3,
        "source": "经典算法练习（埃拉托斯特尼筛）",
        "desc": "输入正整数 n（2 ≤ n ≤ 100000），输出 n 以内（含 n）素数的个数。",
        "hint": "建 bool 数组标记是否素数，从 2 开始把每个素数的倍数划掉；只需筛到 √n。",
        "ref": """n = int(input())
is_prime = [True] * (n + 1)
is_prime[0] = is_prime[1] = False

for i in range(2, int(n ** 0.5) + 1):
    if is_prime[i]:
        for j in range(i * i, n + 1, i):
            is_prime[j] = False

print(sum(is_prime))
""",
        "cases": [_c("30", "10"), _c("2", "1"), _c("100", "25")],
        "explain": "从 i*i 开始划掉：比 i*i 小的 i 的倍数，已经被更小的素数划过了。\n"
                   "外层只需到 √n，因为更大的合数一定有一个不超过 √n 的因子。\n"
                   "复杂度 O(n log log n)，比逐个试除快得多；30 以内有 10 个素数，100 以内 25 个。",
    },
    {
        "id": "A-21",
        "chapter": CHAPTER,
        "no": 21,
        "title": "字符串全排列",
        "topic": "回溯 / 递归",
        "level": 3,
        "source": "经典算法练习（回溯）",
        "desc": (
            "输入一个不含重复字符的字符串，按字典序输出它的全部排列，每行一个。"
        ),
        "hint": "递归：依次把每个字符「固定」在第一位，剩下的部分继续排列；先排序保证字典序。",
        "ref": """def permute(chars, prefix=""):
    if not chars:
        print(prefix)
        return
    for i, ch in enumerate(chars):
        permute(chars[:i] + chars[i + 1:], prefix + ch)

permute(sorted(input().strip()))
""",
        "cases": [
            _c("abc", "abc\nacb\nbac\nbca\ncab\ncba"),
            _c("ab", "ab\nba"),
            _c("a", "a"),
        ],
        "explain": "先 sorted 保证按字典序输出，否则顺序取决于输入。\n"
                   "每层递归「选一个字符放到前缀里，剩下的继续排」，走到底就输出一种排列。\n"
                   "n 个字符有 n! 种排列，n=10 就是 360 万行，回溯适合小规模。",
    },
    {
        "id": "A-22",
        "chapter": CHAPTER,
        "no": 22,
        "title": "只出现一次的数",
        "topic": "位运算 / 异或",
        "level": 2,
        "source": "经典算法练习（异或）",
        "desc": "输入一行整数，除一个数只出现一次外，其余每个数都出现两次。找出这个只出现一次的数并输出。",
        "hint": "异或的性质：a^a=0、a^0=a，把所有数异或起来，成对的会互相抵消。",
        "ref": """nums = [int(x) for x in input().split()]
result = 0
for x in nums:
    result ^= x
print(result)
""",
        "cases": [
            _c("4 1 2 1 2", "4"),
            _c("7 7 9", "9"),
        ],
        "explain": "异或满足交换律和结合律，所以顺序无关，成对的元素一定抵消成 0。\n"
                   "空间 O(1)、时间 O(n)，比用字典计数更省。\n"
                   "如果「只出现一次」的数有两个，需要先按某一位分组再分别异或。",
    },
    {
        "id": "A-23",
        "chapter": CHAPTER,
        "no": 23,
        "title": "判断回文数",
        "topic": "数字 / 取位",
        "level": 1,
        "source": "经典算法练习（回文）",
        "desc": "输入一个非负整数，判断它是不是回文数（正着读和倒着读相同）：是输出「是回文数」，否则输出「不是回文数」。",
        "hint": "转成字符串比较 s == s[::-1]；也可以逐位取余构造反转数再比较。",
        "ref": """n = input().strip()
print("是回文数" if n == n[::-1] else "不是回文数")
""",
        "cases": [
            _c("121", "是回文数"),
            _c("123", "不是回文数"),
            _c("0", "是回文数"),
            _c("1221", "是回文数"),
        ],
        "explain": "按字符串处理最简单，且天然保留前导 0 的语义（如 00100 也算回文）。\n"
                   "如果要求用整数运算：反复取余构造反转数，比较是否等于原数。\n"
                   "负数不是回文数（如 -121 反转后是 121-），本题限定非负。",
    },
    {
        "id": "A-24",
        "chapter": CHAPTER,
        "no": 24,
        "title": "第二大值",
        "topic": "遍历 / 打擂台",
        "level": 2,
        "source": "经典算法练习（打擂台）",
        "desc": "输入一行整数（至少 2 个，且至少有两个不同的值），输出第二大的数（严格小于最大值的最大者）。",
        "hint": "一次遍历维护最大和第二大：比最大大就更新两者；只比第二大则更新第二大。",
        "ref": """nums = [int(x) for x in input().split()]
first = second = None

for x in nums:
    if first is None or x > first:
        second = first
        first = x
    elif x < first and (second is None or x > second):
        second = x
print(second)
""",
        "cases": [
            _c("3 1 4 4 2", "3"),
            _c("5 1", "1"),
            _c("2 2 1", "1"),
        ],
        "explain": "关键是处理重复值：x == first 时既不能更新最大，也不能当第二大（要求严格小于）。\n"
                   "用 None 表示「还没找到」，避免用 0 或 -inf 这类哨兵值干扰负数输入。\n"
                   "排序后取「第一个不等于最大值的元素」也行，但 O(n log n)。",
    },
    {
        "id": "A-25",
        "chapter": CHAPTER,
        "no": 25,
        "title": "数组右移 k 位",
        "topic": "切片 / 取模",
        "level": 2,
        "source": "经典算法练习（旋转数组）",
        "desc": "第一行输入一行整数，第二行输入 k，把数组整体循环右移 k 位后输出。",
        "hint": "k 先对长度取模；结果是「后 k 个元素」+「前面剩下的元素」。",
        "ref": """nums = [int(x) for x in input().split()]
k = int(input()) % len(nums)
print(" ".join(str(x) for x in nums[-k:] + nums[:-k]))
""",
        "cases": [
            _c("1 2 3 4 5\n2", "4 5 1 2 3"),
            _c("1 2 3\n3", "1 2 3"),
            _c("1 2 3 4\n0", "1 2 3 4"),
        ],
        "explain": "k 可能大于数组长度，所以先对 len 取模，k=0 时结果不变。\n"
                   "切片拼接是 O(n) 的简洁写法；原地做法是三次反转（整体、前段、后段）。\n"
                   "注意 nums[-0:] 会取整个数组，所以 k=0 要单独考虑——取模后 k=0 时 nums[-0:] 等于 nums，"
                   "与 nums[:-0]（空）拼起来恰好还是原数组，正好正确。",
    },
    {
        "id": "A-26",
        "chapter": CHAPTER,
        "no": 26,
        "title": "统计逆序对",
        "topic": "双重循环 / 归并",
        "level": 3,
        "source": "经典算法练习（逆序对）",
        "desc": "输入一行整数（不超过 200 个），输出逆序对的个数（i < j 且 nums[i] > nums[j] 的对数）。",
        "hint": "双重循环直接数；进阶可用归并排序在合并时统计（O(n log n)）。",
        "ref": """nums = [int(x) for x in input().split()]
count = 0
for i in range(len(nums)):
    for j in range(i + 1, len(nums)):
        if nums[i] > nums[j]:
            count += 1
print(count)
""",
        "cases": [
            _c("2 4 1 3", "3"),
            _c("1 2 3", "0"),
            _c("3 2 1", "3"),
        ],
        "explain": "2 4 1 3 的逆序对：(2,1)、(4,1)、(4,3) 共 3 个。\n"
                   "内层从 i+1 开始，保证每对只数一次。\n"
                   "题目限定 200 个以内，O(n²) 可行；数据量大时要用归并排序统计。",
    },
    {
        "id": "A-27",
        "chapter": CHAPTER,
        "no": 27,
        "title": "提取并求和字符串中的数字",
        "topic": "字符串解析 / 连续数字",
        "level": 3,
        "source": "经典算法练习（字符串解析）",
        "desc": (
            "输入一个字符串，把其中所有连续的数字当作一个整数，求这些整数的和。\n"
            "例如 a1b22c 得到 1 和 22，和为 23。"
        ),
        "hint": "遍历字符，遇到数字就累积到当前数字，遇到非数字就把当前数字结算并清零。",
        "ref": """s = input()
total = 0
current = 0
for ch in s:
    if ch.isdigit():
        current = current * 10 + int(ch)
    else:
        if current:
            total += current
            current = 0
if current:
    total += current
print(total)
""",
        "cases": [
            _c("a1b22c", "23"),
            _c("12ab3", "15"),
            _c("abc", "0"),
        ],
        "explain": "current 表示「正在读的这个数」，遇到非数字就结算并归零。\n"
                   "循环结束后要再结算一次，否则字符串结尾是数字时会漏掉（如 abc12）。\n"
                   "用 if current 而不是 if current > 0，避免 0 被跳过——这里 0 不影响和，但逻辑更严谨。",
    },
    {
        "id": "A-28",
        "chapter": CHAPTER,
        "no": 28,
        "title": "出现次数超过一半的数",
        "topic": "摩尔投票 / 计数",
        "level": 3,
        "source": "经典算法练习（摩尔投票法）",
        "desc": "输入一行整数，已知某个数出现的次数严格超过总数的一半，找出这个数并输出。",
        "hint": "摩尔投票：候选数 + 计数器，相同则加一、不同则减一，减到 0 就换候选；最后剩下的就是答案。",
        "ref": """nums = [int(x) for x in input().split()]

candidate = None
count = 0
for x in nums:
    if count == 0:
        candidate = x
        count = 1
    elif x == candidate:
        count += 1
    else:
        count -= 1
print(candidate)
""",
        "cases": [
            _c("1 1 2 1", "1"),
            _c("3 3 3 1 2", "3"),
            _c("5 5 5 5 1 2", "5"),
        ],
        "explain": "把不同的数两两抵消，超过一半的那个数一定抵消不完，最后留下的候选就是答案。\n"
                   "时间 O(n)、空间 O(1)，比字典计数更省内存。\n"
                   "前提是「一定存在超过一半的数」；不保证时还要再遍历一次验证。",
    },
    {
        "id": "A-29",
        "chapter": CHAPTER,
        "no": 29,
        "title": "求平方根的整数部分",
        "topic": "二分查找",
        "level": 3,
        "source": "经典算法练习（二分）",
        "desc": (
            "输入一个非负整数 n（n ≤ 10^12），输出 ⌊√n⌋（平方根的整数部分）。\n"
            "要求用二分查找，不能用 sqrt() 或 ** 0.5 直接算。"
        ),
        "hint": "在 0..n 上二分找最大的 x，使 x*x <= n；注意用 x <= n//x 避免溢出。",
        "ref": """n = int(input())

left, right = 0, n
answer = 0
while left <= right:
    mid = (left + right) // 2
    if mid * mid <= n:
        answer = mid
        left = mid + 1
    else:
        right = mid - 1
print(answer)
""",
        "cases": [_c("8", "2"), _c("10", "3"), _c("1", "1"), _c("0", "0")],
        "explain": "二分的是「答案」而不是数组下标：ans 是满足 ans² ≤ n 的最大整数。\n"
                   "每次满足就把 mid 记下来并向右找，否则向左缩。\n"
                   "n 很大时 mid*mid 可能溢出（C 语言），Python 整数不溢出，但用 mid <= n//mid 更通用。",
    },
    {
        "id": "A-30",
        "chapter": CHAPTER,
        "no": 30,
        "title": "去重并排序",
        "topic": "set / sorted",
        "level": 1,
        "source": "经典算法练习（集合去重）",
        "desc": "输入一行整数，去掉重复值后按升序输出，数字之间用空格分隔。",
        "hint": "sorted(set(nums)) 一步完成；set 自动去重，sorted 返回升序列表。",
        "ref": """nums = [int(x) for x in input().split()]
print(" ".join(str(x) for x in sorted(set(nums))))
""",
        "cases": [
            _c("3 1 3 2", "1 2 3"),
            _c("5 5 5", "5"),
            _c("2 1", "1 2"),
        ],
        "explain": "set 去重后无序，sorted 再排一次，顺序就稳定了。\n"
                   "如果要求「保持原顺序去重」，就不能用 set，要用列表 + in 判断或 dict.fromkeys。\n"
                   "复杂度 O(n log n)，主要花在排序上。",
    },
]
