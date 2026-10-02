import { EmptyState } from "../components/common/EmptyState";
import { WildTrackLoader } from "../components/common/WildTrackLoader";
const DataState = ({ loading, error, empty, onRetry }) => {
  if (loading) return <div className="data-state data-state--loading"><WildTrackLoader compact /></div>;
  if (error) return <EmptyState title="Unable to load data" text={error.message || "The server is unavailable. Check the connection and retry."} action="Retry" onAction={onRetry} />;
  if (empty) return <EmptyState title="No records found" text="Adjust filters or clear the search to see monitoring records." />;
  return null;
};
export { DataState };
