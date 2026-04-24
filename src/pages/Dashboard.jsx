import React from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/apiClient';
import { Building2, Users, Mail, MapPin, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import StatCard from '@/components/dashboard/StatCard';
import RecentActivity from '@/components/dashboard/RecentActivity';
import PipelineChart from '@/components/dashboard/PipelineChart';

export default function Dashboard() {
  const { data: stats = {} } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => apiClient.get('/dashboard-stats'),
    refetchInterval: 30000, // refresh every 30s
  });

  const { data: companies = [] } = useQuery({
    queryKey: ['companies'],
    queryFn: () => apiClient.get('/companies'),
  });

  const sentEmails = stats.emails_sent ?? 0;
  const replyRate = stats.reply_rate ?? 0;

  // Build activity feed from recent runs + outreach logs
  const recentRuns = (stats.recent_runs || []).map((r) => ({
    type: 'discovery',
    title: `Pincode run: ${r.Pincode || r.pincode}`,
    subtitle: `${r['Companies Found'] || r.companies_found || 0} companies found`,
    date: r.Timestamp || r.created_date,
  }));

  const recentOutreach = (stats.recent_outreach || []).map((o) => ({
    type: 'email',
    title: `Email to ${o['Contact Email'] || o.contact_email}`,
    subtitle: o['Company Name'] || o.company_name,
    date: o.Timestamp || o.created_date,
  }));

  const activities = [...recentRuns, ...recentOutreach]
    .sort((a, b) => new Date(b.date) - new Date(a.date))
    .slice(0, 8);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground text-sm mt-1">Your lead intelligence overview</p>
        </div>
        <Link to="/discover">
          <Button className="gap-2">
            <MapPin className="w-4 h-4" />
            New Discovery
            <ArrowRight className="w-4 h-4" />
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Companies" value={stats.companies ?? 0} icon={Building2} />
        <StatCard title="Contacts" value={stats.contacts ?? 0} icon={Users} />
        <StatCard title="Emails Sent" value={sentEmails} icon={Mail} />
        <StatCard title="Reply Rate" value={`${replyRate}%`} icon={MapPin} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3">
          <PipelineChart companies={companies} />
        </div>
        <div className="lg:col-span-2">
          <RecentActivity activities={activities} />
        </div>
      </div>
    </div>
  );
}