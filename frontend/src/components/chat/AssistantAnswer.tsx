import { CheckCircle2, ExternalLink, FileText, ShieldCheck } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Answer } from "../../api";

export function AssistantAnswer({ answer }: { answer: Answer }) {
  const confidence = Math.round(answer.confidence * 100);
  const content = answer.answer.replace(/\s*\(Nguồn:\s*\[[a-f0-9]{8,}\](?:,\s*trang\s*\d+)?\)\s*/gi, "\n").replace(/\[([a-f0-9]{8,})\]/gi, "").trim();
  return <div className="assistant-answer">
    <div className="markdown-answer"><ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown></div>
    <div className="answer-proof"><span className={answer.evidence_sufficient ? "verified" : "insufficient"}><ShieldCheck />{answer.evidence_sufficient ? "Đã kiểm chứng" : "Chưa đủ căn cứ"}</span><span>{confidence}% tin cậy</span></div>
    {!!answer.citations.length && <div className="citation-block"><div className="citation-title"><FileText /> Nguồn trích dẫn ({answer.citations.length})</div>{answer.citations.map((citation, index) => <article key={`${citation.chunk_id}-${index}`}>
      <div><b>{citation.article}{citation.clause ? ` · ${citation.clause}` : ""}</b>{citation.support && <p>{citation.support}</p>}<small>{citation.page > 0 ? `Trang ${citation.page}` : "Tài liệu chính thức"}</small></div>
      {citation.source_url ? <a href={citation.source_url} target="_blank" rel="noreferrer" aria-label="Mở nguồn"><ExternalLink /></a> : <CheckCircle2 />}
    </article>)}</div>}
  </div>;
}
