import React from 'react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

const statusStyles = {
  discovered: 'bg-blue-100 text-blue-700 border-blue-200',
  contacts_found: 'bg-violet-100 text-violet-700 border-violet-200',
  pitched: 'bg-amber-100 text-amber-700 border-amber-200',
  emailed: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  replied: 'bg-teal-100 text-teal-700 border-teal-200',
  converted: 'bg-green-100 text-green-700 border-green-200',
  rejected: 'bg-red-100 text-red-700 border-red-200',
  verified: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  bounced: 'bg-red-100 text-red-700 border-red-200',
  unsubscribed: 'bg-gray-100 text-gray-700 border-gray-200',
  draft: 'bg-gray-100 text-gray-700 border-gray-200',
  sent: 'bg-blue-100 text-blue-700 border-blue-200',
  delivered: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  opened: 'bg-violet-100 text-violet-700 border-violet-200',
  failed: 'bg-red-100 text-red-700 border-red-200',
  spam: 'bg-orange-100 text-orange-700 border-orange-200',
  spamreport: 'bg-orange-100 text-orange-700 border-orange-200',
  running: 'bg-blue-100 text-blue-700 border-blue-200',
  completed: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  no_contacts_found: 'bg-red-50 text-red-700 border-red-200',
};

export default function StatusBadge({ status }) {
  const style = statusStyles[status] || 'bg-gray-100 text-gray-700 border-gray-200';
  return (
    <Badge variant="outline" className={cn('text-xs font-medium capitalize border', style)}>
      {status?.replace(/_/g, ' ') || 'unknown'}
    </Badge>
  );
}