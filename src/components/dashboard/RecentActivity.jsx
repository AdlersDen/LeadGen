import React from 'react';
import { format } from 'date-fns';
import { Building2, Mail, Users, MapPin } from 'lucide-react';
import { cn } from '@/lib/utils';

const iconMap = {
  company: Building2,
  email: Mail,
  contact: Users,
  discovery: MapPin,
};

const colorMap = {
  company: 'bg-blue-100 text-blue-600',
  email: 'bg-emerald-100 text-emerald-600',
  contact: 'bg-violet-100 text-violet-600',
  discovery: 'bg-amber-100 text-amber-600',
};

export default function RecentActivity({ activities }) {
  if (!activities || activities.length === 0) {
    return (
      <div className="bg-card rounded-xl border border-border p-6">
        <h3 className="font-semibold text-base mb-4">Recent Activity</h3>
        <p className="text-sm text-muted-foreground text-center py-8">No activity yet. Start a pincode discovery to get going!</p>
      </div>
    );
  }

  return (
    <div className="bg-card rounded-xl border border-border p-6">
      <h3 className="font-semibold text-base mb-4">Recent Activity</h3>
      <div className="space-y-3">
        {activities.map((activity, i) => {
          const Icon = iconMap[activity.type] || Building2;
          const color = colorMap[activity.type] || colorMap.company;
          const parsedDate = activity.date ? new Date(activity.date) : null;
          const hasValidDate = parsedDate && !Number.isNaN(parsedDate.getTime());
          return (
            <div key={i} className="flex items-start gap-3 group">
              <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5", color)}>
                <Icon className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{activity.title}</p>
                <p className="text-xs text-muted-foreground">{activity.subtitle}</p>
              </div>
              <span className="text-xs text-muted-foreground whitespace-nowrap">
                {hasValidDate ? format(parsedDate, 'MMM d, h:mm a') : '—'}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}