const Skeleton = ({ className = "" }) => <div className={`animate-pulse rounded-control bg-moss-100 ${className}`} />;
const TableSkeleton = ({ rows = 6 }) => <div className="space-y-2">
    {Array.from({ length: rows }).map((_, index) => <Skeleton key={index} className="h-11 w-full" />)}
  </div>;
export {
  Skeleton,
  TableSkeleton
};
