import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, ApiError } from "./api";
import type { Bank, Chapter, Question, Stats } from "./types";

const EMPTY_STATS: Stats = { total: 0, solved: 0, tried: 0, favorite: 0, attempts: 0, passes: 0, rate: 0 };

interface BankValue {
  questions: Question[];
  chapters: Chapter[];
  stats: Stats;
  loading: boolean;
  error: string;
  reload: () => Promise<void>;
  patchQuestion: (qid: string, patch: Partial<Question>) => void;
  toggleFavorite: (qid: string) => Promise<void>;
  find: (qid: string) => Question | undefined;
}

const BankCtx = createContext<BankValue | null>(null);

export function BankProvider({ children }: { children: ReactNode }) {
  const [bank, setBank] = useState<Bank | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.bank();
      setBank(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "题库加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const patchQuestion = useCallback((qid: string, patch: Partial<Question>) => {
    setBank((prev) => {
      if (!prev) return prev;
      const questions = prev.questions.map((q) => (q.id === qid ? { ...q, ...patch } : q));
      // 收藏数、已通过数跟着变
      const stats = {
        ...prev.stats,
        solved: questions.filter((q) => q.last === "pass").length,
        tried: questions.filter((q) => q.attempts > 0).length,
        favorite: questions.filter((q) => q.favorite).length,
      };
      return { ...prev, questions, stats };
    });
  }, []);

  const toggleFavorite = useCallback(
    async (qid: string) => {
      const current = bank?.questions.find((q) => q.id === qid);
      const next = !current?.favorite;
      patchQuestion(qid, { favorite: next, attempts: current?.attempts ?? 0 });
      try {
        const res = await api.setFavorite(qid, next);
        patchQuestion(qid, { favorite: res.favorite });
      } catch (err) {
        patchQuestion(qid, { favorite: !next });
        throw err;
      }
    },
    [bank, patchQuestion],
  );

  const value = useMemo<BankValue>(
    () => ({
      questions: bank?.questions ?? [],
      chapters: bank?.chapters ?? [],
      stats: bank?.stats ?? EMPTY_STATS,
      loading,
      error,
      reload,
      patchQuestion,
      toggleFavorite,
      find: (qid) => bank?.questions.find((q) => q.id === qid),
    }),
    [bank, loading, error, reload, patchQuestion, toggleFavorite],
  );

  return <BankCtx.Provider value={value}>{children}</BankCtx.Provider>;
}

export function useBank(): BankValue {
  const ctx = useContext(BankCtx);
  if (!ctx) throw new Error("useBank 必须在 <BankProvider> 内使用");
  return ctx;
}
