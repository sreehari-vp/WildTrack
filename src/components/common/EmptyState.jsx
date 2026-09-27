import { AlertCircle } from "lucide-react";
import { Button } from "./Button";
const EmptyState = ({
  title,
  text,
  action,
  onAction
}) => <div className="flex min-h-40 flex-col items-center justify-center rounded-panel border border-dashed border-line bg-paper p-8 text-center">
    <AlertCircle className="mb-3 h-5 w-5 text-ink-400" strokeWidth={1.75} />
    <h3 className="font-medium text-ink-900">{title}</h3>
    <p className="mt-1 max-w-sm text-sm text-ink-600">{text}</p>
    {action ? <Button className="mt-4" onClick={onAction}>
        {action}
      </Button> : null}
  </div>;
export {
  EmptyState
};
