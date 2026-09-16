import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function MarkdownReport({ markdown }: { markdown: string }) {
  return (
    <div className="prose-report max-w-none">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
    </div>
  );
}
