import { ReactNode, useState } from "react";
import { BookOpen, Bot, CircleHelp, Menu, Network, Plus, X } from "lucide-react";
import { Health } from "../../api";
import { AppRoute, Navigate } from "../../types";

type Props = { route: AppRoute; health: Health | null; navigate: Navigate; children: ReactNode };

export function AppShell({ route, health, navigate, children }: Props) {
  const [open, setOpen] = useState(false);
  const go = (next: AppRoute) => { navigate(next); setOpen(false); };
  const itemClass = (name: AppRoute["name"]) => `shell-nav-item ${route.name === name ? "active" : ""}`;
  return (
    <div className="app-frame">
      {open && <button className="mobile-backdrop" onClick={() => setOpen(false)} aria-label="Đóng menu" />}
      <aside className={`app-sidebar ${open ? "open" : ""}`}>
        <div className="shell-brand"><span>V</span><div><b>VinUni</b><small>Policy Assistant</small></div></div>
        <button className="sidebar-primary" onClick={() => go({ name: "assistant" })}><Plus size={18} /> Cuộc trò chuyện mới</button>
        <nav className="shell-nav">
          <button className={itemClass("assistant")} onClick={() => go({ name: "assistant" })}><Bot /> Trợ lý chính sách</button>
          <button className={itemClass("library")} onClick={() => go({ name: "library" })}><BookOpen /> Thư viện chính sách</button>
          <button className={itemClass("how")} onClick={() => go({ name: "how" })}><Network /> Cách hệ thống hoạt động</button>
        </nav>
        <div className="sidebar-bottom">
          <div className="system-status"><span className={health?.status === "ready" ? "ready" : ""} /><div><b>{health?.status === "ready" ? "Hệ thống sẵn sàng" : "Đang kiểm tra hệ thống"}</b><small>{health?.provider ? `${health.provider} · ${health.model}` : health?.detail ?? "Kết nối backend"}</small></div></div>
          <a href="https://policy.vinuni.edu.vn/all-policies/" target="_blank" rel="noreferrer"><CircleHelp /> Nguồn chính sách chính thức</a>
        </div>
      </aside>
      <div className="app-workspace">
        <header className="workspace-header">
          <button className="mobile-menu" onClick={() => setOpen((value) => !value)}>{open ? <X /> : <Menu />}</button>
          <div><b>AI-Powered University Policy Assistant</b><span>Tra cứu chính sách VinUniversity có kiểm chứng</span></div>
          <button className="header-chat" onClick={() => go({ name: "assistant" })}><Bot /> <span>Hỏi trợ lý</span></button>
        </header>
        {children}
      </div>
    </div>
  );
}
