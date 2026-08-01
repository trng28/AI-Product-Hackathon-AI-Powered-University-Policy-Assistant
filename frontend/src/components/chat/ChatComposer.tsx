import { FormEvent, KeyboardEvent, RefObject } from "react";
import { LoaderCircle, Send } from "lucide-react";

type Props = { value: string; setValue: (value: string) => void; submit: () => void; disabled: boolean; busy: boolean; inputRef: RefObject<HTMLTextAreaElement | null> };
export function ChatComposer({ value, setValue, submit, disabled, busy, inputRef }: Props) {
  const send = (event?: FormEvent) => { event?.preventDefault(); submit(); };
  const keyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); submit(); } };
  return <div className="chat-composer-area"><form className="chat-composer" onSubmit={send}><textarea ref={inputRef} rows={1} value={value} onChange={(event) => setValue(event.target.value)} onKeyDown={keyDown} placeholder="Nhập câu hỏi về chính sách VinUni..." disabled={disabled} /><button type="submit" disabled={disabled || busy || !value.trim()}>{busy ? <LoaderCircle className="spin" /> : <Send />}</button></form><small>AI có thể mắc lỗi. Vui lòng đối chiếu văn bản chính thức.</small></div>;
}
