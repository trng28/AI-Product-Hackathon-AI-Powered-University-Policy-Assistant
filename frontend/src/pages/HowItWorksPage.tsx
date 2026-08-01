import { ArrowRight, Bot, CheckCircle2, FileSearch, MessageSquareText, Network, ShieldCheck } from "lucide-react";
import { Navigate } from "../types";

const steps = [
  [MessageSquareText, "01", "Hiểu truy vấn", "Chuẩn hóa ý định, giữ từ khóa gốc và mở rộng thuật ngữ Việt–Anh."],
  [FileSearch, "02", "Truy xuất", "Tìm kiếm trong các chunks chính sách public bằng semantic hoặc lexical retrieval."],
  [Network, "03", "Phân tích chính sách", "Đối chiếu câu hỏi với bằng chứng và không sử dụng kiến thức ngoài tài liệu."],
  [ShieldCheck, "04", "Kiểm chứng citation", "Guardrail xác nhận chunk nguồn tồn tại trước khi chấp nhận trích dẫn."],
  [CheckCircle2, "05", "Phản hồi", "Trả lời cùng ngôn ngữ người dùng với độ tin cậy và liên kết nguồn."],
] as const;
export function HowItWorksPage({ navigate }: { navigate: Navigate }) {
  return <main className="content-page how-page"><div className="page-heading centered"><span>Policy query orchestration agent</span><h1>Cách hệ thống hoạt động</h1><p>Workflow nhiều bước giúp câu trả lời chính xác, có ngữ cảnh và được kiểm chứng từ tài liệu chính thức.</p></div><div className="workflow-grid">{steps.map(([Icon, number, title, body]) => <article key={number}><div><Icon /></div><span>{number}</span><h2>{title}</h2><p>{body}</p></article>)}</div><section className="grounding-panel"><Bot /><div><h2>Grounded by design</h2><p>Hệ thống chỉ xác nhận câu trả lời khi có evidence và citation hợp lệ. Nếu tài liệu không đủ căn cứ, trợ lý chủ động từ chối suy diễn.</p></div><button onClick={() => navigate({ name: "assistant" })}>Thử đặt câu hỏi <ArrowRight /></button></section></main>;
}
