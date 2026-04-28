import React from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/apiClient';
import {
  Building2, Users, Mail, MapPin, ArrowRight,
  CheckCircle2, AlertTriangle, MousePointerClick, TrendingUp,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import StatCard from '@/components/dashboard/StatCard';
import RecentActivity from '@/components/dashboard/RecentActivity';
import PipelineChart from '@/components/dashboard/PipelineChart';

function readField(record, ...keys) {
  for (const key of keys) {
    const value = record?.[key];
    if (value !== undefined && value !== null && value !== '') {
      return value;
    }
  }
  return undefined;
}

export default function Dashboard() {
  const { data: stats = {} } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => apiClient.get('/dashboard-stats'),
    refetchInterval: 30_000,
  });

  const { data: companies = [] } = useQuery({
    queryKey: ['companies'],
    queryFn: () => apiClient.get('/companies'),
  });

  const { data: contacts = [] } = useQuery({
    queryKey: ['contacts'],
    queryFn: () => apiClient.get('/contacts'),
  });

  // -- Delivery analytics derived from outreach logs ---------------------------
  const { data: outreachLogs = [] } = useQuery({
    queryKey: ['outreach'],
    queryFn: () => apiClient.get('/outreach'),
    refetchInterval: 60_000,
  });

  const totalSent      = outreachLogs.length;
  const delivered      = outreachLogs.filter((l) => (l.status || l['Status']) === 'delivered').length;
  const opened         = outreachLogs.filter((l) => (l.status || l['Status']) === 'opened').length;
  const bounced        = outreachLogs.filter((l) => (l.status || l['Status']) === 'bounced').length;

  const deliveryRate   = totalSent > 0 ? Math.round((delivered / totalSent) * 100) : 0;
  const openRate       = delivered > 0  ? Math.round((opened    / delivered) * 100) : 0;
  const bounceRate     = totalSent > 0 ? Math.round((bounced   / totalSent) * 100) : 0;

  // -- Activity feed ------------------------------------------------------------
  const recentRuns = (stats.recent_runs || []).map((r) => {
    const pincode = String(readField(r, 'Pincode', 'pincode') || '').trim();
    const complexName = String(readField(r, 'Complex Name', 'complex_name') || '').trim();
    const location = String(readField(r, 'Location Name', 'location_name') || '').trim();
    const label = pincode || complexName || location || 'Discovery';

    return {
      type: 'discovery',
      title: pincode ? `Pincode run: ${label}` : `Area run: ${label}`,
      subtitle: `${readField(r, 'Companies Found', 'companies_found') || 0} companies found`,
      date: readField(r, 'Timestamp', 'created_date'),
    };
  });

  const recentOutreach = (stats.recent_outreach || []).map((o) => ({
    type:     'email',
    title:    `Email to ${o['Contact Email'] || o.contact_email}`,
    subtitle: o['Company Name'] || o.company_name,
    date:     o.Timestamp || o.created_date,
  }));

  const activities = [...recentRuns, ...recentOutreach]
    .filter((activity) => activity.date)
    .sort((a, b) => new Date(b.date) - new Date(a.date))
    .slice(0, 8);

  const totalCompanies = companies.length || stats.companies || 0;
  const totalContacts = contacts.length || stats.contacts || 0;
  const replyRate = stats.reply_rate ?? 0;

  const isEmpty = totalCompanies === 0 && totalContacts === 0 && totalSent === 0;

  return (
    <div className="space-y-8">
      {/* -- Header -------------------------------------------------------- */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground text-sm mt-1">Your lead intelligence overview</p>
        </div>
        <Link to="/discover">
          <Button className="gap-2" id="new-discovery-btn">
            <MapPin className="w-4 h-4" />
            New Discovery
            <ArrowRight className="w-4 h-4" />
          </Button>
        </Link>
      </div>

      {/* -- Empty state CTA ----------------------------------------------- */}
      {isEmpty && (
        <div className="bg-card rounded-xl border border-dashed border-border p-10 text-center">
          <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
            <MapPin className="w-7 h-7 text-primary" />
          </div>
          <h3 className="text-lg font-semibold">Run your first discovery</h3>
          <p className="text-sm text-muted-foreground mt-2 max-w-sm mx-auto">
            Enter a pincode or business complex to discover B2B companies and kick off your outreach pipeline.
          </p>
          <Link to="/discover">
            <Button className="mt-5 gap-2" id="dashboard-start-btn">
              <MapPin className="w-4 h-4" /> Start Discovering
              <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
        </div>
      )}

      {/* -- Primary stats row ---------------------------------------------- */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Companies"    value={totalCompanies} icon={Building2} />
        <StatCard title="Contacts"     value={totalContacts} icon={Users} />
        <StatCard title="Emails Sent"  value={totalSent}            icon={Mail} />
        <StatCard title="Reply Rate"   value={`${replyRate}%`} icon={TrendingUp} />
      </div>

      {/* -- Email delivery analytics row (from SendGrid webhook data) ----- */}
      <div>
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
          Email Delivery Analytics
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard
            title="Delivery Rate"
            value={`${deliveryRate}%`}
            icon={CheckCircle2}
            trendLabel={totalSent > 0 ? `${delivered} of ${totalSent} delivered` : undefined}
          />
          <StatCard
            title="Open Rate"
            value={`${openRate}%`}
            icon={MousePointerClick}
            trendLabel={delivered > 0 ? `${opened} of ${delivered} opened` : undefined}
          />
          <StatCard
            title="Bounce Rate"
            value={`${bounceRate}%`}
            icon={AlertTriangle}
            trendLabel={totalSent > 0 ? `${bounced} bounced` : undefined}
            className={bounceRate > 5 ? 'border-destructive/40' : ''}
          />
        </div>
        {totalSent === 0 && (
          <p className="text-xs text-muted-foreground mt-2">
            Delivery analytics will appear here once emails have been sent and SendGrid webhook events are received.
          </p>
        )}
      </div>

      {/* -- Pipeline chart + activity feed -------------------------------- */}
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