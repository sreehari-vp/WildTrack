const BrandMark = () => <div className="brand-mark">
  <svg className="brand-mark__icon" viewBox="0 0 40 40" aria-hidden="true">
    <rect x="1" y="1" width="38" height="38" rx="8" fill="var(--forest-700)" stroke="rgba(255,255,255,.22)" />
    <path d="M20 31c-5.1-5.2-8.4-9.7-8.4-14.6C11.6 10.5 15.4 6 20 6s8.4 4.5 8.4 10.4C28.4 21.3 25.1 25.8 20 31Z" fill="var(--moss-300)" />
    <path d="M20 26V10.8m0 8.3c-2.8-.7-4.7-2.4-6-5.1m6 6.9c2.8-.7 4.7-2.4 6-5.1" stroke="var(--forest-950)" strokeWidth="1.9" strokeLinecap="round" />
  </svg>
  <span className="brand-mark__copy"><span className="brand-mark__name">WildTrack</span><span className="brand-mark__location">NILGIRI RIDGE RESERVE</span></span>
</div>;
export { BrandMark };