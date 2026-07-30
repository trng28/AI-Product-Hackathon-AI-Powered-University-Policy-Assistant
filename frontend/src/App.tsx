import { FormEvent, useEffect, useRef, useState } from "react";
import {
  Bot,
  CheckCircle2,
  FileText,
  GraduationCap,
  LoaderCircle,
  Menu,
  MessageSquarePlus,
  Send,
  ShieldCheck,
  Sparkles,
  UserRound,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Answer, Health, api } from "./api";

type ChatTurn = {
  id: string;
  question: string;
  answer?: Answer;
  error?: string;
  pending: boolean;
};

const suggestions = [
  "Điều kiện bị cảnh báo học tập là gì?",
  "Sinh viên được đăng ký tối đa bao nhiêu tín chỉ?",
  "Quy trình chuyển đổi tín chỉ được quy định thế nào?",
];

function AssistantAnswer({ answer }: { answer: Answer }) {
  const confidence = Math.round(answer.confidence * 100);
  const displayAnswer = answer.answer
    .replace(
      /\s*\(Nguồn:\s*\[[a-f0-9]{8,}\](?:,\s*trang\s*\d+)?\)\s*/gi,
      "\n",
    )
    .replace(/\[([a-f0-9]{8,})\]/gi, "")
    .trim();
  return (
    <div className="assistant-content">
      <div className="answer-copy">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {displayAnswer}
        </ReactMarkdown>
      </div>
      <div className="answer-meta">
        <span className={answer.evidence_sufficient ? "grounded" : "ungrounded"}>
          <ShieldCheck size={14} />
          {answer.evidence_sufficient ? "Đã kiểm chứng" : "Chưa đủ căn cứ"}
        </span>
        <span>{confidence}% tin cậy</span>
      </div>
      {!!answer.citations.length && (
        <details className="sources" open>
          <summary>{answer.citations.length} nguồn trích dẫn</summary>
          <div className="source-list">
            {answer.citations.map((citation, index) => (
              <article key={`${citation.chunk_id}-${index}`}>
                <FileText size={17} />
                <div>
                  <b>
                    {citation.article}
                    {citation.clause ? ` · ${citation.clause}` : ""}
                  </b>
                  {citation.support && <p>{citation.support}</p>}
                  <small>
                    {citation.document} · Trang {citation.page}
                  </small>
                </div>
                <CheckCircle2 className="source-check" size={16} />
              </article>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => {
      setHealth({
        status: "configuration_required",
        index_ready: false,
        detail: "Không kết nối được backend.",
      });
    });
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  function newChat() {
    setTurns([]);
    setQuestion("");
    setSidebarOpen(false);
    inputRef.current?.focus();
  }

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    const value = question.trim();
    if (!value || health?.status !== "ready") return;
    const id = crypto.randomUUID();
    setQuestion("");
    setTurns((current) => [
      ...current,
      { id, question: value, pending: true },
    ]);
    try {
      const answer = await api.ask(value);
      setTurns((current) =>
        current.map((turn) =>
          turn.id === id ? { ...turn, answer, pending: false } : turn,
        ),
      );
    } catch (error) {
      setTurns((current) =>
        current.map((turn) =>
          turn.id === id
            ? {
                ...turn,
                error:
                  error instanceof Error
                    ? error.message
                    : "Không thể xử lý câu hỏi.",
                pending: false,
              }
            : turn,
        ),
      );
    }
  }

  function useSuggestion(value: string) {
    setQuestion(value);
    inputRef.current?.focus();
  }

  const busy = turns.some((turn) => turn.pending);
  const statusLabel =
    health?.status === "ready"
      ? `${health.provider} · ${health.model}`
      : health?.detail ?? "Đang kết nối backend";

  return (
    <div className="chat-app">
      <aside className={sidebarOpen ? "chat-sidebar open" : "chat-sidebar"}>
        <div className="sidebar-brand">
          <span>V</span>
          <div>
            <b>VinUni</b>
            <small>Policy Assistant</small>
          </div>
        </div>
        <button className="new-chat" onClick={newChat}>
          <MessageSquarePlus size={18} /> Cuộc trò chuyện mới
        </button>
        <div className="sidebar-info">
          <GraduationCap size={19} />
          <div>
            <b>Kho tri thức</b>
            <span>Quy chế đào tạo đại học</span>
          </div>
        </div>
        <div className="sidebar-foot">
          <span className={health?.status === "ready" ? "online" : ""} />
          <div>
            <b>{health?.status === "ready" ? "Hệ thống sẵn sàng" : "Cần cấu hình"}</b>
            <small>{statusLabel}</small>
          </div>
        </div>
      </aside>

      <section className="chat-main">
        <header className="chat-header">
          <button
            className="menu-button"
            onClick={() => setSidebarOpen((value) => !value)}
            aria-label="Mở menu"
          >
            <Menu />
          </button>
          <div>
            <b>Trợ lý chính sách</b>
            <span><i /> Multi-Agent RAG</span>
          </div>
          <button className="header-new" onClick={newChat}>
            <MessageSquarePlus size={17} /> <span>Chat mới</span>
          </button>
        </header>

        <div className="conversation">
          {!turns.length && (
            <div className="welcome">
              <div className="welcome-icon"><Bot /></div>
              <div className="welcome-tag"><Sparkles size={14} /> AI Policy Assistant</div>
              <h1>Xin chào, mình có thể<br />giúp gì cho bạn?</h1>
              <p>
                Hỏi về quy chế và chính sách VinUniversity. Mỗi câu trả lời
                được kiểm chứng với Điều, Khoản và trang tài liệu.
              </p>
              <div className="chat-suggestions">
                {suggestions.map((item) => (
                  <button key={item} onClick={() => useSuggestion(item)}>
                    {item}
                  </button>
                ))}
              </div>
            </div>
          )}

          {turns.map((turn) => (
            <div className="turn" key={turn.id}>
              <div className="message user-message">
                <div className="avatar user-avatar"><UserRound /></div>
                <div>
                  <span className="speaker">Bạn</span>
                  <div className="bubble">{turn.question}</div>
                </div>
              </div>
              <div className="message assistant-message">
                <div className="avatar bot-avatar"><Bot /></div>
                <div className="message-body">
                  <span className="speaker">Trợ lý chính sách</span>
                  {turn.pending && (
                    <div className="agent-thinking">
                      <LoaderCircle className="spin" />
                      <span>
                        <b>Các agent đang phân tích...</b>
                        Hiểu truy vấn · Truy xuất · Kiểm chứng
                      </span>
                    </div>
                  )}
                  {turn.answer && <AssistantAnswer answer={turn.answer} />}
                  {turn.error && <div className="chat-error">{turn.error}</div>}
                </div>
              </div>
            </div>
          ))}
          <div ref={endRef} />
        </div>

        <div className="composer-wrap">
          {health?.status !== "ready" && (
            <div className="config-warning">{statusLabel}</div>
          )}
          <form className="composer" onSubmit={submit}>
            <textarea
              ref={inputRef}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  submit();
                }
              }}
              rows={1}
              placeholder="Nhập câu hỏi về chính sách..."
              disabled={health?.status !== "ready"}
            />
            <button
              type="submit"
              disabled={!question.trim() || busy || health?.status !== "ready"}
              aria-label="Gửi câu hỏi"
            >
              {busy ? <LoaderCircle className="spin" /> : <Send />}
            </button>
          </form>
          <small>
            AI có thể mắc lỗi. Vui lòng đối chiếu văn bản chính thức.
          </small>
        </div>
      </section>
    </div>
  );
}

export default App;
