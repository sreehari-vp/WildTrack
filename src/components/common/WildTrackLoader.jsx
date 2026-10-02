const WildTrackLoader = ({ compact = false }) => <div className={`wildtrack-loading${compact ? " is-compact" : ""}`} role="status" aria-label="Loading WildTrack">
  <div className="wildtrack-loading__panel">
    <div className="wildtrack-loading__radar" aria-hidden="true">
      <span className="radar-ring radar-ring--outer" /><span className="radar-ring radar-ring--middle" /><span className="radar-sweep" />
      <svg viewBox="0 0 40 40" className="radar-mark"><path d="M20 31c-5.1-5.2-8.4-9.7-8.4-14.6C11.6 10.5 15.4 6 20 6s8.4 4.5 8.4 10.4C28.4 21.3 25.1 25.8 20 31Z" fill="currentColor" /><path d="M20 26V11m0 8c-2.8-.7-4.7-2.4-6-5m6 7c2.8-.7 4.7-2.4 6-5" fill="none" stroke="var(--paper)" strokeWidth="1.8" strokeLinecap="round" /></svg>
      <span className="radar-ping" />
    </div>
    <div className="wildtrack-loading__content">
      <p className="wildtrack-loading__kicker">FIELD MONITORING SYSTEM</p>
      <h2>WildTrack</h2>
      <p className="wildtrack-loading__message">Establishing live connection</p>
      <div className="wildtrack-loading__progress" aria-hidden="true"><span /></div>
    </div>
  </div>
</div>;
export { WildTrackLoader };