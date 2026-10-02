import { Search } from "lucide-react";
import { useEffect, useState } from "react";
import { NotificationsMenu } from "./NotificationsMenu";
import { BrandMark } from "./BrandMark";
const TopBar = ({ onSearch }) => {
  const [isMac, setIsMac] = useState(false);
  useEffect(() => setIsMac(navigator.platform.toLowerCase().includes("mac")), []);
  return <header className="app-masthead">
    <div className="app-masthead__identity"><BrandMark /></div>
    <div className="app-masthead__actions">
      <button className="masthead-search" onClick={onSearch} aria-label="Search WildTrack">
        <Search size={17} strokeWidth={1.8} /><span>Search</span><kbd>{isMac ? "⌘ K" : "Ctrl K"}</kbd>
      </button>
      <NotificationsMenu />
    </div>
  </header>;
};
export { TopBar };