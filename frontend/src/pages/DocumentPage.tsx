import { ArrowLeft, Bot, ExternalLink, FileCheck2 } from "lucide-react";
import { policies } from "../data/policies";
import { Navigate } from "../types";

export function DocumentPage({ policyId, navigate }: { policyId: string; navigate: Navigate }) {
  const policy = policies.find((item) => item.id === policyId);
  if (!policy) return <main className="content-page"><div className="empty-state">Không tìm thấy tài liệu.<button onClick={() => navigate({ name: "library" })}>Quay lại thư viện</button></div></main>;
  return <main className="document-page"><div className="document-toolbar"><button onClick={() => navigate({ name: "library" })}><ArrowLeft /> Thư viện</button><div><button onClick={() => navigate({ name: "assistant" })}><Bot /> Hỏi trợ lý</button><a href={policy.sourceUrl} target="_blank" rel="noreferrer">Nguồn chính thức <ExternalLink /></a></div></div>
    <article className="document-sheet"><header><span>{policy.category}</span><small>{policy.reference} · Cập nhật {policy.updated}</small><h1>{policy.title}</h1><p>{policy.description}</p></header><section><h2>Phạm vi tài liệu</h2><p>Tài liệu này thuộc nguồn chính sách công khai của VinUniversity và được hệ thống sử dụng để truy xuất, phân tích và tạo câu trả lời có căn cứ.</p></section><section><h2>Nội dung nổi bật</h2><ul>{policy.highlights.map((item) => <li key={item}><FileCheck2 /> {item}</li>)}</ul></section><aside><b>Lưu ý kiểm chứng</b><p>Trang này trình bày metadata và tóm tắt tích hợp. Khi ra quyết định, luôn mở tài liệu nguồn để kiểm tra phiên bản và toàn văn điều khoản.</p></aside></article>
  </main>;
}
