import { FormEvent, useEffect, useRef, useState } from "react";
import { Bot, LoaderCircle, Sparkles, UserRound } from "lucide-react";
import { Health, api } from "../api";
import { AssistantAnswer } from "../components/chat/AssistantAnswer";
import { ChatComposer } from "../components/chat/ChatComposer";
import { ChatTurn } from "../types";

const suggestions = ["Điều kiện bị cảnh báo học tập là gì?", "Học phí thạc sĩ Computer Science một năm?", "Điều kiện chuyển ngành tại VinUni?"];

export function AssistantPage({ health }: { health: Health | null }) {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    const value = question.trim();
    if (!value || busy || health?.status !== "ready") return;
    const id = crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
    setQuestion("");
    setTurns((items) => [...items, { id, question: value, pending: true }]);
    try {
      const answer = await api.ask(value);
      setTurns((items) => items.map((item) => item.id === id ? { ...item, answer, pending: false } : item));
    } catch (error) {
      setTurns((items) => items.map((item) => item.id === id ? { ...item, pending: false, error: error instanceof Error ? error.message : "Không thể xử lý câu hỏi." } : item));
    }
  }

  const busy = turns.some((item) => item.pending);
  const unavailable = health?.status !== "ready";
  return <main className="assistant-page">
    <section className="chat-scroll">
      {!turns.length && <div className="assistant-hero"><div className="hero-bot"><Bot /></div><span><Sparkles /> Trợ lý chính sách có kiểm chứng</span><h1>Chào bạn, mình có thể giúp gì?</h1><p>Nhận câu trả lời nhanh từ kho chính sách công khai của VinUniversity, kèm điều khoản và liên kết tài liệu nguồn.</p><div className="suggestion-grid">{suggestions.map((item) => <button key={item} onClick={() => { setQuestion(item); inputRef.current?.focus(); }}>{item}</button>)}</div></div>}
      {turns.map((turn) => <div className="chat-turn" key={turn.id}>
        <div className="user-row"><div><span>Bạn</span><p>{turn.question}</p></div><i><UserRound /></i></div>
        <div className="assistant-row"><i><Bot /></i><div><span>AI-Powered University Policy Assistant</span>{turn.pending && <div className="thinking-card"><LoaderCircle className="spin" /><div><b>Đang phân tích chính sách...</b><small>Hiểu truy vấn · Truy xuất · Kiểm chứng nguồn</small></div></div>}{turn.answer && <AssistantAnswer answer={turn.answer} />}{turn.error && <div className="request-error">{turn.error}</div>}</div></div>
      </div>)}
      <div ref={endRef} />
    </section>
    {unavailable && <div className="health-warning">{health?.detail ?? "Backend chưa sẵn sàng. Vui lòng kiểm tra cấu hình hệ thống."}</div>}
    <ChatComposer value={question} setValue={setQuestion} submit={() => submit()} disabled={unavailable} busy={busy} inputRef={inputRef} />
  </main>;
}
