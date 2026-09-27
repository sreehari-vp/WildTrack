import { analyticsService } from "../services/analyticsService";
import { useAsyncData } from "./useAsyncData";
const useAnalytics = () => useAsyncData(analyticsService.getAnalytics, []);
export {
  useAnalytics
};
