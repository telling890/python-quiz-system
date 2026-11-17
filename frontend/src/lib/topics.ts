/**
 * 考点归类：题库里的 topic 是复合标签（"双重循环 / 递减"、"字典计数 / split"），
 * 直接按它分组太细（139 道题有 135 个不同 topic），按章节分组又太粗（只有 5 章）。
 *
 * 这里按「考点家族」归一次：同一族里的题考的是同一类技能。
 * 组卷的「考点覆盖」策略和交卷报告的「考点分布」都用这一套口径。
 */

interface Rule {
  pattern: RegExp;
  group: string;
  /** 刷题页搜索用的关键词（点「去练这个考点」时带进 URL） */
  keyword: string;
}

// 顺序有讲究：越具体的越靠前，先匹配到的生效
const RULES: Rule[] = [
  { pattern: /递归/, group: "递归", keyword: "递归" },
  { pattern: /动态规划/, group: "动态规划", keyword: "动态规划" },
  { pattern: /栈|队列/, group: "栈与队列", keyword: "栈" },
  { pattern: /排序|双指针|二分|查找|摩尔投票/, group: "查找与排序", keyword: "查找" },
  { pattern: /字典|映射/, group: "字典与映射", keyword: "字典" },
  { pattern: /集合|set/i, group: "集合与映射", keyword: "集合" },
  { pattern: /元组|tuple/i, group: "元组", keyword: "元组" },
  { pattern: /列表|数组|list|enumerate/i, group: "列表", keyword: "列表" },
  {
    pattern: /字符串|切片|子串|字符|索引|replace|split|join|find|upper|lower|isalpha|isdecimal|isdigit|ord|chr|expandtabs|strip|format|title/i,
    group: "字符串",
    keyword: "字符串",
  },
  { pattern: /循环|while|for|遍历/i, group: "循环与遍历", keyword: "循环" },
  { pattern: /if|elif|else|分支|条件|逻辑/i, group: "条件分支", keyword: "if" },
  { pattern: /进制|位运算|取位/, group: "进制与位运算", keyword: "进制" },
  { pattern: /穷举|回溯|枚举/, group: "穷举与回溯", keyword: "穷举" },
  { pattern: /递推|数列|斐波那契/, group: "递推与数列", keyword: "递推" },
];

const KEYWORD_BY_GROUP = new Map(RULES.map((rule) => [rule.group, rule.keyword]));

/** 复合考点 → 考点家族 */
export function topicGroup(topic: string): string {
  const text = (topic || "").trim();
  if (!text) return "其他";
  for (const rule of RULES) {
    if (rule.pattern.test(text)) return rule.group;
  }
  return text.split("/")[0].trim() || "其他";
}

/** 考点家族 → 刷题页搜索关键词（"循环与遍历" → "循环"） */
export function topicKeyword(group: string): string {
  return KEYWORD_BY_GROUP.get(group) ?? group;
}
