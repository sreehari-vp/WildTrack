const analytics = {
  metrics: [
    { key: "total-alerts", label: "Total alerts", value: 15 },
    { key: "zone-violations", label: "Zone violations", value: 9 },
    { key: "active-animals", label: "Active animals", value: 21 },
    { key: "avg-distance", label: "Avg. daily distance", value: "6.8", unit: "km" },
    { key: "peak-hour", label: "Peak activity hour", value: "15:00" }
  ],
  hourlyActivity: [
    { hour: "00", elephants: 8, tigers: 4, deer: 10 },
    { hour: "03", elephants: 5, tigers: 6, deer: 6 },
    { hour: "06", elephants: 9, tigers: 3, deer: 14 },
    { hour: "09", elephants: 11, tigers: 2, deer: 17 },
    { hour: "12", elephants: 7, tigers: 4, deer: 12 },
    { hour: "15", elephants: 12, tigers: 6, deer: 19 },
    { hour: "18", elephants: 10, tigers: 5, deer: 15 },
    { hour: "21", elephants: 6, tigers: 5, deer: 8 }
  ],
  alertTrend: [
    { day: "Thu", info: 1, low: 1, medium: 2, high: 2, critical: 1 },
    { day: "Fri", info: 0, low: 1, medium: 1, high: 3, critical: 0 },
    { day: "Sat", info: 1, low: 0, medium: 2, high: 1, critical: 1 },
    { day: "Sun", info: 1, low: 1, medium: 1, high: 2, critical: 2 },
    { day: "Mon", info: 0, low: 2, medium: 1, high: 3, critical: 1 },
    { day: "Tue", info: 1, low: 0, medium: 3, high: 2, critical: 2 },
    { day: "Wed", info: 1, low: 1, medium: 3, high: 5, critical: 5 }
  ],
  speciesActivity: [
    { name: "Elephants", value: 74 },
    { name: "Deer", value: 68 },
    { name: "Tigers", value: 42 }
  ],
  zoneTime: [
    { name: "Safe", value: 32 },
    { name: "Buffer", value: 23 },
    { name: "Restricted", value: 16 },
    { name: "High risk", value: 12 },
    { name: "Water source", value: 9 },
    { name: "Protected", value: 8 }
  ]
};
export {
  analytics
};
