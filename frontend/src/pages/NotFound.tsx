import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
import { Button } from "../components/ui";

export default function NotFound() {
  return (
    <div className="relative z-10 grid min-h-dvh place-items-center px-6">
      <div className="flex flex-col items-center gap-4 text-center">
        <span className="grid size-14 place-items-center rounded-2xl border border-line bg-ink-850 text-fg-dim">
          <Compass size={24} />
        </span>
        <div>
          <p className="text-4xl font-semibold tracking-tight">404</p>
          <p className="mt-1 text-sm text-fg-dim">这个页面不存在，可能是链接过期了。</p>
        </div>
        <Link to="/">
          <Button>回到概览</Button>
        </Link>
      </div>
    </div>
  );
}
