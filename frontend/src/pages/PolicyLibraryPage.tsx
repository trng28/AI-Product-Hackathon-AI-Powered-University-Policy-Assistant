import { useMemo, useState } from "react";
import { ArrowRight, BookOpen, Search } from "lucide-react";
import { policies, policyCategories } from "../data/policies";
import { Navigate } from "../types";

export function PolicyLibraryPage({ navigate }: { navigate: Navigate }) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All");
  const visible = useMemo(() => policies.filter((policy) => (category === "All" || policy.category === category) && `${policy.title} ${policy.reference} ${policy.description}`.toLowerCase().includes(query.toLowerCase())), [category, query]);
  return <main className="content-page library-page"><div className="page-heading"><span>Kho tri thức công khai</span><h1>Thư viện chính sách</h1><p>Tra cứu các quy chế, thủ tục và hướng dẫn chính thức đã được lập chỉ mục cho hệ thống RAG.</p></div>
    <div className="library-toolbar"><label><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tìm theo tên hoặc mã chính sách..." /></label><div>{policyCategories.map((item) => <button className={category === item ? "active" : ""} onClick={() => setCategory(item)} key={item}>{item}</button>)}</div></div>
    <div className="policy-grid">{visible.map((policy) => <article className="policy-card" key={policy.id}><div className="policy-icon"><BookOpen /></div><span>{policy.category}</span><h2>{policy.title}</h2><b>{policy.reference}</b><p>{policy.description}</p><footer><small>Cập nhật {policy.updated}</small><button onClick={() => navigate({ name: "document", id: policy.id })}>Xem tài liệu <ArrowRight /></button></footer></article>)}</div>
    {!visible.length && <div className="empty-state">Không tìm thấy chính sách phù hợp.</div>}
  </main>;
}
