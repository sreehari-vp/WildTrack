import { EmptyState } from "../components/common/EmptyState";
import { TableSkeleton } from "../components/common/Skeleton";
const DataState = ({
  loading,
  error,
  empty,
  onRetry
}) => {
  if (loading) return <TableSkeleton rows={7} />;
  if (error) return <EmptyState title="Unable to load data" text="The local mock service did not respond. Try again." action="Retry" onAction={onRetry} />;
  if (empty) return <EmptyState title="No records found" text="Adjust filters or clear the search to see monitoring records." />;
  return null;
};
export {
  DataState
};
