import { lazy, Suspense } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import Layout from "./components/Layout";
import { Spinner } from "./components/ui";
import { BankProvider } from "./lib/bank";
import { useAuth } from "./lib/auth";
import Dashboard from "./pages/Dashboard";

// 代码编辑器（CodeMirror）只在刷题/自由编程/组卷里用到，按页拆包
const Practice = lazy(() => import("./pages/Practice"));
const Book = lazy(() => import("./pages/Book"));
const FreeCoding = lazy(() => import("./pages/FreeCoding"));
const StatsPage = lazy(() => import("./pages/Stats"));
const Exam = lazy(() => import("./pages/Exam"));
const LoginPage = lazy(() => import("./pages/Login"));
const NotFound = lazy(() => import("./pages/NotFound"));

function Splash({ text = "正在校验登录状态…" }: { text?: string }) {
  return (
    <div className="relative z-10 grid min-h-dvh place-items-center">
      <div className="flex flex-col items-center gap-3 text-fg-dim">
        <Spinner size={26} />
        <p className="text-xs">{text}</p>
      </div>
    </div>
  );
}

function RequireAuth() {
  const { user, ready } = useAuth();
  const location = useLocation();
  if (!ready) return <Splash />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return (
    <BankProvider>
      <Layout />
    </BankProvider>
  );
}

export default function App() {
  return (
    <Suspense fallback={<Splash text="加载中…" />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<RequireAuth />}>
          <Route index element={<Dashboard />} />
          <Route path="practice" element={<Practice />} />
          <Route path="practice/:qid" element={<Practice />} />
          <Route path="book" element={<Book />} />
          <Route path="free" element={<FreeCoding />} />
          <Route path="stats" element={<StatsPage />} />
          <Route path="exam" element={<Exam />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}
