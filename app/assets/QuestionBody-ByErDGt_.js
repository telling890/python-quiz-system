import{c as n,x as h,s as f,k as g,j as e,q as j,n as o,B as b,l as u,r as m,g as p}from"./index-DjF3JMP-.js";import{B as y}from"./book-open-CRJ8YCpu.js";/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const k=n("Check",[["path",{d:"M20 6 9 17l-5-5",key:"1gmf2c"}]]);/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const v=n("ChevronDown",[["path",{d:"m6 9 6 6 6-6",key:"qrunsl"}]]);/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const N=n("Copy",[["rect",{width:"14",height:"14",x:"8",y:"8",rx:"2",ry:"2",key:"17jyea"}],["path",{d:"M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2",key:"zix9uf"}]]);/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const w=n("Lightbulb",[["path",{d:"M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5",key:"1gvzjb"}],["path",{d:"M9 18h6",key:"x1upvd"}],["path",{d:"M10 22h4",key:"ceow96"}]]);/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const M=n("ListTree",[["path",{d:"M21 12h-8",key:"1bmf0i"}],["path",{d:"M21 6H8",key:"1pqkrb"}],["path",{d:"M21 18h-8",key:"1tm79t"}],["path",{d:"M3 6v4c0 1.1.9 2 2 2h3",key:"1ywdgy"}],["path",{d:"M3 10v6c0 1.1.9 2 2 2h3",key:"2wc746"}]]);/**
 * @license lucide-react v0.468.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const S=n("Send",[["path",{d:"M14.536 21.686a.5.5 0 0 0 .937-.024l6.5-19a.496.496 0 0 0-.635-.635l-19 6.5a.5.5 0 0 0-.024.937l7.93 3.18a2 2 0 0 1 1.112 1.11z",key:"1ffxy3"}],["path",{d:"m21.854 2.147-10.94 10.939",key:"12cjpa"}]]);function i({icon:t,title:a,children:l,defaultOpen:c=!1,tone:d="neutral"}){const[r,s]=m.useState(c);return e.jsxs("div",{className:"overflow-hidden rounded-xl border border-line bg-ink-900/50",children:[e.jsxs("button",{type:"button",onClick:()=>s(x=>!x),className:"flex w-full items-center justify-between gap-2 px-3 py-2 text-left transition-colors hover:bg-ink-800/60","aria-expanded":r,children:[e.jsxs("span",{className:p("flex items-center gap-1.5 text-xs font-semibold",d==="brand"?"text-brand-300":"text-fg-muted"),children:[t,a]}),e.jsx(v,{size:14,className:p("text-fg-dim transition-transform",r&&"rotate-180")})]}),r?e.jsx("div",{className:"animate-fade-in border-t border-line px-3 py-2.5",children:l}):null]})}function C({text:t}){const[a,l]=m.useState(!1);return e.jsxs("button",{type:"button",onClick:async()=>{try{await navigator.clipboard.writeText(t),l(!0),setTimeout(()=>l(!1),1500)}catch{}},className:"flex items-center gap-1 rounded-md border border-line px-1.5 py-1 text-[0.66rem] text-fg-dim transition-colors hover:text-fg",children:[a?e.jsx(k,{size:11,className:"text-ok-400"}):e.jsx(N,{size:11}),a?"已复制":"复制"]})}function L({question:t,chapters:a,favoriteSlot:l}){const c=h(t.level),d=f(t.last),r=g(a,t.chapter_id);return e.jsxs("div",{className:"space-y-3",children:[e.jsxs("div",{className:"flex flex-wrap items-center gap-1.5",children:[e.jsx("span",{className:"rounded-md px-1.5 py-0.5 font-mono text-[0.7rem] font-semibold",style:{background:`${r}22`,color:r},children:j(t)}),e.jsx("span",{className:"text-[0.7rem] text-fg-dim",children:t.chapter}),e.jsx(o,{tone:c.tone,children:c.label}),e.jsx(o,{tone:d.tone,children:d.label}),t.topic?e.jsx(o,{tone:"neutral",children:t.topic}):null,e.jsxs("span",{className:"ml-auto flex items-center gap-1.5",children:[t.attempts>0?e.jsxs("span",{className:"text-[0.68rem] tabular-nums text-fg-dim",children:["作答 ",t.attempts," 次"]}):null,l]})]}),e.jsx("h2",{className:"text-lg font-semibold leading-snug tracking-tight text-fg",children:t.title}),e.jsx("p",{className:"whitespace-pre-wrap text-[0.86rem] leading-relaxed text-fg-muted",children:t.desc}),t.cases.length>0?e.jsx(i,{icon:e.jsx(M,{size:13}),title:`测试用例（${t.cases.length} 条）`,defaultOpen:!0,children:e.jsx("div",{className:"space-y-1.5",children:t.cases.map((s,x)=>e.jsxs("div",{className:"grid gap-1.5 rounded-lg bg-ink-950/50 p-2 sm:grid-cols-2",children:[e.jsxs("div",{children:[e.jsx("p",{className:"mb-0.5 text-[0.64rem] font-semibold text-fg-dim",children:"输入"}),e.jsx("pre",{className:"whitespace-pre-wrap break-all font-mono text-[0.74rem] text-fg-muted",children:s.stdin||"（无输入）"})]}),e.jsxs("div",{children:[e.jsx("p",{className:"mb-0.5 text-[0.64rem] font-semibold text-fg-dim",children:"期望输出"}),e.jsx("pre",{className:"whitespace-pre-wrap break-all font-mono text-[0.74rem] text-ok-400",children:s.expect||"（无输出）"})]})]},x))})}):null,t.hint?e.jsx(i,{icon:e.jsx(w,{size:13}),title:"提示",tone:"brand",children:e.jsx("p",{className:"whitespace-pre-wrap text-[0.82rem] leading-relaxed text-fg-muted",children:t.hint})}):null,t.ref?e.jsx(i,{icon:e.jsx(y,{size:13}),title:"参考答案",children:e.jsxs("div",{className:"space-y-1.5",children:[e.jsx("div",{className:"flex justify-end",children:e.jsx(C,{text:t.ref})}),e.jsx("pre",{className:"max-h-64 overflow-auto rounded-lg border border-line bg-ink-950/70 px-3 py-2 font-mono text-[0.76rem] leading-relaxed text-fg-muted",children:t.ref}),e.jsx(b,{variant:"ghost",size:"sm",onClick:()=>{var s;(s=navigator.clipboard)==null||s.writeText(t.ref)},children:"复制到编辑器（先清空再粘贴）"})]})}):null,t.explain?e.jsx(i,{icon:e.jsx(u,{size:13}),title:"题解",children:e.jsx("p",{className:"whitespace-pre-wrap text-[0.82rem] leading-relaxed text-fg-muted",children:t.explain})}):null,t.source?e.jsxs("p",{className:"text-[0.68rem] text-fg-dim",children:["来源：",t.source]}):null]})}export{L as Q,S};
