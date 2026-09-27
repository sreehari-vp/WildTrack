import { analytics } from "../data/analytics";
import { withDelay } from "./mockDelay";
const analyticsService = {
  getAnalytics: () => withDelay(analytics)
};
export {
  analyticsService
};
