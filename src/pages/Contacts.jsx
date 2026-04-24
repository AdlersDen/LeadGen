import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/apiClient';
import { Users, Search, UserPlus, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import StatusBadge from '@/components/shared/StatusBadge';
import { toast } from 'sonner';

export default function Contacts() {
  const [search, setSearch] = useState('');
  const [showFinder, setShowFinder] = useState(false);
  const [bulkLimit, setBulkLimit] = useState('5');
  const queryClient = useQueryClient();

  const { data: contacts = [], isLoading } = useQuery({
    queryKey: ['contacts'],
    queryFn: () => apiClient.get('/contacts'),
  });

  const { data: companies = [] } = useQuery({
    queryKey: ['companies'],
    queryFn: () => apiClient.get('/companies'),
  });

  const bulkFindContactsMutation = useMutation({
    mutationFn: async (limit) => {
      return apiClient.post('/contacts/bulk-find', { limit: parseInt(limit, 10) });
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      setShowFinder(false);
      toast.success(data.message || `Processed companies successfully!`);
    },
    onError: (err) => {
      toast.error(err.message || 'Bulk contact discovery failed');
    },
  });

  const filtered = contacts.filter((c) => {
    const name = c.full_name || c['Full Name'] || '';
    const company = c.company_name || c['Company Name'] || '';
    const email = c.email || c['Email'] || '';
    return (
      !search ||
      name.toLowerCase().includes(search.toLowerCase()) ||
      company.toLowerCase().includes(search.toLowerCase()) ||
      email.toLowerCase().includes(search.toLowerCase())
    );
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Contacts</h1>
          <p className="text-muted-foreground text-sm mt-1">{contacts.length} contacts in database</p>
        </div>

        <Dialog open={showFinder} onOpenChange={setShowFinder}>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <UserPlus className="w-4 h-4" /> Bulk Find Contacts
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Auto-Extract Decision Makers</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 pt-4">
              <p className="text-sm text-muted-foreground">
                Automatically extract HR, Marketing, and Admin contacts for newly discovered companies via Hunter.io.
              </p>
              
              <div className="space-y-2">
                <label className="text-sm font-medium">Processing Limit (Save API Credits)</label>
                <Select value={bulkLimit} onValueChange={setBulkLimit}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select limit" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="5">Process 5 companies</SelectItem>
                    <SelectItem value="10">Process 10 companies</SelectItem>
                    <SelectItem value="25">Process 25 companies</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Button
                className="w-full gap-2"
                disabled={bulkFindContactsMutation.isPending}
                onClick={() => bulkFindContactsMutation.mutate(bulkLimit)}
              >
                {bulkFindContactsMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Search className="w-4 h-4" />
                )}
                {bulkFindContactsMutation.isPending ? 'Extracting Contacts...' : 'Start Extraction'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          placeholder="Search contacts..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      <div className="bg-card rounded-xl border border-border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50">
              <TableHead>Name</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Company</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Confidence</TableHead>
              <TableHead>Status</TableHead>
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
                  No contacts found
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((contact, idx) => {
                const id = contact.id || contact['ID'] || idx;
                const fullName = contact.full_name || contact['Full Name'] || '';
                const role = contact.role || contact['Role'] || '';
                const company = contact.company_name || contact['Company Name'] || '';
                const email = contact.email || contact['Email'] || '';
                const confidence = contact.confidence_score || contact['Confidence Score'];
                const status = contact.status || contact['Status'] || '';

                return (
                  <TableRow key={id} className="hover:bg-muted/30">
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center">
                          <span className="text-xs font-bold text-accent">
                            {fullName?.[0] || '?'}
                          </span>
                        </div>
                        <span className="font-medium text-sm">{fullName}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">{role || '—'}</TableCell>
                    <TableCell className="text-sm">{company}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{email || '—'}</TableCell>
                    <TableCell>
                      {confidence ? (
                        <span
                          className={`text-xs font-semibold ${
                            confidence >= 70
                              ? 'text-emerald-600'
                              : confidence >= 50
                              ? 'text-amber-600'
                              : 'text-red-600'
                          }`}
                        >
                          {confidence}%
                        </span>
                      ) : '—'}
                    </TableCell>
                    <TableCell><StatusBadge status={status} /></TableCell>
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