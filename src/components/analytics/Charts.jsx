import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { ChartPanel } from "./ChartPanel";
const colors = {
  safe: "var(--risk-safe)",
  medium: "var(--risk-medium)",
  high: "var(--risk-high)",
  critical: "var(--risk-critical)",
  info: "var(--risk-info)",
  forest: "var(--forest-700)",
  moss: "var(--moss-300)",
  protected: "var(--zone-protected)"
};
const AnalyticsCharts = ({ analytics }) => <div className="grid gap-4 xl:grid-cols-2">
    <ChartPanel title="GPS observations by hour (UTC)">
      <div className="h-72">
        <ResponsiveContainer>
          <AreaChart data={analytics.hourlyActivity}>
            <CartesianGrid stroke="var(--line)" vertical={false} />
            <XAxis dataKey="hour" tickLine={false} axisLine={false} />
            <YAxis tickLine={false} axisLine={false} />
            <Tooltip />
            <Area type="monotone" dataKey="elephants" stackId="1" stroke={colors.forest} fill={colors.forest} fillOpacity={0.28} />
            <Area type="monotone" dataKey="tigers" stackId="1" stroke={colors.high} fill={colors.high} fillOpacity={0.22} />
            <Area type="monotone" dataKey="deer" stackId="1" stroke={colors.safe} fill={colors.safe} fillOpacity={0.22} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </ChartPanel>
    <ChartPanel title="Alerts over time">
      <div className="h-72">
        <ResponsiveContainer>
          <BarChart data={analytics.alertTrend}>
            <CartesianGrid stroke="var(--line)" vertical={false} />
            <XAxis dataKey="day" tickLine={false} axisLine={false} />
            <YAxis tickLine={false} axisLine={false} />
            <Tooltip />
            <Bar dataKey="info" stackId="a" fill={colors.info} />
            <Bar dataKey="low" stackId="a" fill={colors.safe} />
            <Bar dataKey="medium" stackId="a" fill={colors.medium} />
            <Bar dataKey="high" stackId="a" fill={colors.high} />
            <Bar dataKey="critical" stackId="a" fill={colors.critical} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ChartPanel>
    <ChartPanel title="GPS observations by species">
      <div className="h-72">
        <ResponsiveContainer>
          <BarChart layout="vertical" data={analytics.speciesActivity}>
            <CartesianGrid stroke="var(--line)" horizontal={false} />
            <XAxis type="number" tickLine={false} axisLine={false} />
            <YAxis dataKey="name" type="category" tickLine={false} axisLine={false} width={90} />
            <Tooltip />
            <Bar dataKey="value" fill={colors.forest} radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ChartPanel>
    <ChartPanel title="Estimated zone dwell time (hours)">
      <div className="h-72">
        <ResponsiveContainer>
          <PieChart>
            <Pie data={analytics.zoneTime} dataKey="value" nameKey="name" innerRadius={58} outerRadius={95} paddingAngle={2}>
              {analytics.zoneTime.map((entry, index) => <Cell key={entry.name} fill={[colors.safe, colors.medium, colors.high, colors.critical, colors.info, colors.protected][index]} />)}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </ChartPanel>
  </div>;
export {
  AnalyticsCharts
};
