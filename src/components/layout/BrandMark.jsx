const BrandMark = ({ compact = false }) => <div className="flex items-center gap-3">
    <svg className="h-9 w-9 shrink-0" viewBox="0 0 40 40" aria-hidden="true">
      <rect width="40" height="40" rx="8" fill="var(--forest-900)" />
      <path
  d="M20 31c-5.1-5.2-8.4-9.7-8.4-14.6C11.6 10.5 15.4 6 20 6s8.4 4.5 8.4 10.4C28.4 21.3 25.1 25.8 20 31Z"
  fill="var(--moss-300)"
/>
      <path
  d="M20 26V10.8m0 8.3c-2.8-.7-4.7-2.4-6-5.1m6 6.9c2.8-.7 4.7-2.4 6-5.1"
  stroke="var(--forest-950)"
  strokeWidth="1.9"
  strokeLinecap="round"
/>
    </svg>
    {!compact ? <div>
        <div className="font-display text-lg text-paper">WildTrack</div>
        <div className="text-xs text-moss-300">Nilgiri ridge</div>
      </div> : null}
  </div>;
export {
  BrandMark
};
