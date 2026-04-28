import React from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/apiClient';
import { Activity, Building2, Users, Mail, MapPin } from 'lucide-react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import StatusBadge from '@/components/shared/StatusBadge';
import { format } from 'date-fns';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';

export default function Runs() {
  const { data: runs = [], isLoading } = useQuery({
    queryKey: ['runs'],
    queryFn: () => apiClient.get('/runs'),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Run History</h1>
          <p className="text-muted-foreground text-sm mt-1">All pincode discovery runs</p>
        </div>
        <Link to="/discover">
          <Button className="gap-2">
            <MapPin className="w-4 h-4" /> New Run
          </Button>
        </Link>
      </div>

      <div className="bg-card rounded-xl border border-border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50">
              <TableHead>Pincode</TableHead>
              <TableHead>Location</TableHead>
              <TableHead>Companies</TableHead>
              <TableHead>Contacts</TableHead>
              <TableHead>Emails</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Date</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array(5).fill(0).map((_, i) => (
                <TableRow key={i}>
                  {Array(7).fill(0).map((_, j) => (
                    <TableCell key={j}><Skeleton className="h-4 w-20" /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : runs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-12 text-muted-foreground">
                  No runs yet. Start a pincode discovery!
                </TableCell>
              </TableRow>
            ) : (
              runs.map((run, idx) => {
                const id = run.id || run['ID'] || idx;
                const pincode = String(run.pincode || run['Pincode'] || '').trim();
                const complexName = String(run.complex_name || run['Complex Name'] || '').trim();
                const location = String(run.location_name || run['Location Name'] || complexName).trim();
                const companiesFound = run.companies_found ?? run['Companies Found'] ?? 0;
                const contactsFound = run.contacts_found ?? run['Contacts Found'] ?? 0;
                const emailsSent = run.emails_sent ?? run['Emails Sent'] ?? 0;
                const status = run.status || run['Status'];
                const timestamp = run.created_date || run['Timestamp'];

                return (
                  <TableRow key={id} className="hover:bg-muted/30">
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <MapPin className="w-4 h-4 text-primary" />
                        <span className="font-mono font-semibold text-sm">{pincode || complexName || 'complex'}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm">{location || '—'}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1 text-sm">
                        <Building2 className="w-3.5 h-3.5 text-muted-foreground" />
                        {companiesFound}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1 text-sm">
                        <Users className="w-3.5 h-3.5 text-muted-foreground" />
                        {contactsFound}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1 text-sm">
                        <Mail className="w-3.5 h-3.5 text-muted-foreground" />
                        {emailsSent}
                      </div>
                    </TableCell>
                    <TableCell><StatusBadge status={status} /></TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {timestamp ? format(new Date(timestamp), 'MMM d, yyyy h:mm a') : '—'}
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}