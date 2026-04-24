import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/api/apiClient';
import { Building2, Search, ExternalLink, MapPin } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import StatusBadge from '@/components/shared/StatusBadge';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';

export default function Companies() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const { data: companies = [], isLoading } = useQuery({
    queryKey: ['companies'],
    queryFn: () => apiClient.get('/companies'),
  });

  const filtered = companies.filter((c) => {
    // Normalise keys — Google Sheets returns Title Case headers
    const name = c.name || c['Company Name'] || '';
    const industry = c.industry || c['Industry'] || '';
    const pincode = c.pincode || c['Pincode'] || '';
    const status = c.status || c['Status'] || '';

    const matchSearch =
      !search ||
      name.toLowerCase().includes(search.toLowerCase()) ||
      industry.toLowerCase().includes(search.toLowerCase()) ||
      pincode.includes(search);
    const matchStatus = statusFilter === 'all' || status === statusFilter;
    return matchSearch && matchStatus;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Companies</h1>
          <p className="text-muted-foreground text-sm mt-1">{companies.length} companies in database</p>
        </div>
        <Link to="/discover">
          <Button variant="outline" className="gap-2">
            <MapPin className="w-4 h-4" /> Discover More
          </Button>
        </Link>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search companies..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="discovered">Discovered</SelectItem>
            <SelectItem value="contacts_found">Contacts Found</SelectItem>
            <SelectItem value="pitched">Pitched</SelectItem>
            <SelectItem value="emailed">Emailed</SelectItem>
            <SelectItem value="replied">Replied</SelectItem>
            <SelectItem value="converted">Converted</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="bg-card rounded-xl border border-border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50">
              <TableHead>Company</TableHead>
              <TableHead>Industry</TableHead>
              <TableHead>Pincode</TableHead>
              <TableHead>Employees</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Domain</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array(5).fill(0).map((_, i) => (
                <TableRow key={i}>
                  {Array(6).fill(0).map((_, j) => (
                    <TableCell key={j}><Skeleton className="h-4 w-24" /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-12 text-muted-foreground">
                  No companies found
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((company, idx) => {
                const name = company.name || company['Company Name'];
                const industry = company.industry || company['Industry'];
                const pincode = company.pincode || company['Pincode'];
                const employeeCount = company.employee_count || company['Employee Count'];
                const status = company.status || company['Status'];
                const domain = company.domain || company['Domain'];
                const id = company.id || company['ID'] || idx;

                return (
                  <TableRow key={id} className="hover:bg-muted/30 cursor-pointer">
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                          <Building2 className="w-4 h-4 text-primary" />
                        </div>
                        <span className="font-medium text-sm">{name}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">{industry || '—'}</TableCell>
                    <TableCell className="text-sm">{pincode}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{employeeCount || '—'}</TableCell>
                    <TableCell><StatusBadge status={status} /></TableCell>
                    <TableCell>
                      {domain ? (
                        <a
                          href={`https://${domain}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary hover:underline text-sm flex items-center gap-1"
                        >
                          {domain} <ExternalLink className="w-3 h-3" />
                        </a>
                      ) : '—'}
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