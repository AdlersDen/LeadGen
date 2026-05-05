// @ts-nocheck
import React, { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/apiClient';
import { Search, Loader2, Zap, Building2, ChevronDown, ChevronUp, Clock } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import StatusBadge from '@/components/shared/StatusBadge';
import { toast } from 'sonner';
import RunAlert from '@/components/RunAlert';

export default function Contacts() {
  const [search, setSearch] = useState('');
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [panelOpen, setPanelOpen] = useState(false);
  const [extractProgress, setExtractProgress] = useState(null); // { total, remaining, pct }
  const [extractionAlert, setExtractionAlert] = useState(null);
  const pollRef = useRef(null);
  const queryClient = useQueryClient();

  // ── Contacts list ──────────────────────────────────────────────────────────
  const { data: contacts = [], isLoading } = useQuery({
    queryKey: ['contacts'],
    queryFn: () => apiClient.get('/contacts'),
  });

  // ── Pending companies — always fetched so the count badge is always visible ─
  const { data: pendingCompanies = [], isLoading: isPendingLoading } = useQuery({
    queryKey: ['companies-pending'],
    queryFn: () => apiClient.get('/companies/pending'),
    staleTime: 0,
  });

  // ── 90-day cooldown status map (email -> bool) ────────────────────────────
  const { data: cooldownMap = {} } = useQuery({
    queryKey: ['cooldown-status'],
    queryFn: () => apiClient.get('/contacts/cooldown-status'),
    staleTime: 60_000,
  });

  // ── Extraction mutation ────────────────────────────────────────────────────
  const extractMutation = useMutation({
    mutationFn: (company_ids) =>
      apiClient.post('/contacts/extract-selected', { company_ids }),
    onMutate: (company_ids) => {
      setExtractionAlert(null);
      const total = company_ids.length;
      let processed = 0;
      setExtractProgress({ total, remaining: total, pct: 0 });
      
      // Simulate progress (approx 3 seconds per company) to avoid burning Google Sheets API read quota
      pollRef.current = setInterval(() => {
        processed = Math.min(total - 1, processed + 0.33); 
        const pct = Math.round((processed / total) * 100);
        setExtractProgress({ total, remaining: Math.max(1, Math.round(total - processed)), pct });
      }, 1000);
    },
    onSuccess: (data) => {
      clearInterval(pollRef.current);
      setExtractProgress(null);
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      queryClient.invalidateQueries({ queryKey: ['companies-pending'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      setSelectedIds(new Set());
      
      const queued = data.queued || 0;
      const skipped_domain = data.skipped_no_domain || 0;
      const skipped_extracted = data.skipped_already_extracted || 0;
      
      let type = 'info';
      if (queued > 0) type = 'success';
      else if (queued === 0 && (skipped_domain > 0 || skipped_extracted > 0)) type = 'warning';
      
      const message = {
        type: type,
        title: queued > 0 ? `Extraction Processed` : 'No Contacts Extracted',
        body: queued > 0 
            ? `Successfully processed ${queued} companies for extraction. (Skipped ${skipped_domain} without domain).`
            : `Skipped all selected companies (No domain: ${skipped_domain}, Already extracted: ${skipped_extracted}).`,
        action: 'none'
      };
      setExtractionAlert(message);
      
      toast.success(
        `Done! Queued: ${data.queued} · Skipped (no domain): ${data.skipped_no_domain} · Already done: ${data.skipped_already_extracted}`
      );
    },
    onError: (err) => {
      clearInterval(pollRef.current);
      setExtractProgress(null);
      toast.error(err.message || 'Extraction failed. Please try again.');
    },
  });

  // Cleanup poll on unmount
  useEffect(() => () => clearInterval(pollRef.current), []);

  // ── Selection helpers ──────────────────────────────────────────────────────
  const pendingIds = pendingCompanies.map(c => c.ID || c.id).filter(Boolean);
  const allSelected = pendingIds.length > 0 && pendingIds.every(id => selectedIds.has(id));

  const toggleSelectAll = (checked) => {
    setSelectedIds(checked ? new Set(pendingIds) : new Set());
  };

  const toggleOne = (checked, id) => {
    const next = new Set(selectedIds);
    checked ? next.add(id) : next.delete(id);
    setSelectedIds(next);
  };

  const handleExtract = () => {
    const ids = Array.from(selectedIds);
    if (!ids.length) { toast.error('Select at least one company first.'); return; }
    if (ids.length > 20) { toast.error('Max 20 companies per request.'); return; }
    extractMutation.mutate(ids);
  };

  // ── Contacts search filter ─────────────────────────────────────────────────
  const filtered = contacts.filter((c) => {
    const name    = c.full_name   || c['Full Name']    || '';
    const company = c.company_name || c['Company Name'] || '';
    const email   = c.email       || c['Email']         || '';
    return (
      !search ||
      name.toLowerCase().includes(search.toLowerCase()) ||
      company.toLowerCase().includes(search.toLowerCase()) ||
      email.toLowerCase().includes(search.toLowerCase())
    );
  });

  const tierColors = { A: 'text-emerald-600 font-bold', B: 'text-amber-600 font-semibold' };

  return (
    <div className="space-y-6">

      {/* ── Page header ──────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Contacts</h1>
          <p className="text-muted-foreground text-sm mt-1">{contacts.length} contacts in database</p>
        </div>

        {/* Toggle panel button with pending badge */}
        <Button
          variant={panelOpen ? 'default' : 'outline'}
          className="gap-2"
          onClick={() => setPanelOpen(v => !v)}
        >
          <Zap className="w-4 h-4" />
          Extract Contacts
          {!isPendingLoading && pendingCompanies.length > 0 && (
            <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-xs">
              {pendingCompanies.length} pending
            </Badge>
          )}
          {panelOpen ? <ChevronUp className="w-3.5 h-3.5 ml-1" /> : <ChevronDown className="w-3.5 h-3.5 ml-1" />}
        </Button>
      </div>

      {extractionAlert && (
        <RunAlert message={extractionAlert} onClose={() => setExtractionAlert(null)} />
      )}

      {/* ── Extraction panel ─────────────────────────────────────────────── */}
      {panelOpen && (
        <div className="bg-card rounded-xl border border-border overflow-hidden">

          {/* Panel header */}
          <div className="flex items-center justify-between px-5 py-3 bg-muted/40 border-b border-border">
            <div className="flex items-center gap-3">
              <Checkbox
                id="select-all-pending"
                checked={allSelected}
                onCheckedChange={toggleSelectAll}
                disabled={isPendingLoading || pendingCompanies.length === 0}
                aria-label="Select all pending companies"
              />
              <label htmlFor="select-all-pending" className="text-sm font-medium cursor-pointer select-none">
                {isPendingLoading
                  ? 'Loading pending companies…'
                  : pendingCompanies.length === 0
                  ? 'All companies have been extracted already'
                  : `Select All — ${pendingCompanies.length} companies pending extraction`}
              </label>
            </div>

            {selectedIds.size > 0 && (
              <Button
                size="sm"
                className="gap-2"
                disabled={extractMutation.isPending}
                onClick={handleExtract}
              >
                {extractMutation.isPending
                  ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Extracting…</>
                  : <><Zap className="w-3.5 h-3.5" /> Extract for Selected ({selectedIds.size}) — Est. {selectedIds.size} Credit{selectedIds.size > 1 ? 's' : ''}</>
                }
              </Button>
            )}
          </div>

          {/* ── Live progress bar (visible only during extraction) ──── */}
          {extractMutation.isPending && extractProgress && (
            <div className="px-5 py-3 bg-primary/5 border-b border-border">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-primary flex items-center gap-1.5">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Extracting contacts via Apollo.io…
                </span>
                <span className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Clock className="w-3 h-3" />
                  ~{Math.ceil((extractProgress.total - (extractProgress.total - extractProgress.remaining)) * 7 / 60)} min remaining
                </span>
              </div>
              {/* Progress bar */}
              <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-700 ease-out"
                  style={{ width: `${Math.max(5, extractProgress.pct)}%` }}
                />
              </div>
              <p className="text-[11px] text-muted-foreground mt-1.5">
                {extractProgress.total - extractProgress.remaining} of {extractProgress.total} companies processed
              </p>
            </div>
          )}

          {/* Pending companies list */}
          {isPendingLoading ? (
            <div className="p-4 space-y-2">
              {Array(3).fill(0).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full rounded-lg" />
              ))}
            </div>
          ) : pendingCompanies.length === 0 ? (
            <p className="text-center text-sm text-muted-foreground py-8">
              🎉 All discovered companies have had contacts extracted.
            </p>
          ) : (
            <div className="divide-y divide-border max-h-72 overflow-y-auto">
              {pendingCompanies.map((company, idx) => {
                const id     = company.ID     || company.id     || idx;
                const name   = company.Name   || company.name   || '—';
                const domain = company.Domain || company.domain || '';
                const tier   = company.Tier   || company.tier   || '';

                return (
                  <label
                    key={id}
                    htmlFor={`company-${id}`}
                    className="flex items-center gap-3 px-5 py-3 hover:bg-muted/30 cursor-pointer transition-colors"
                  >
                    <Checkbox
                      id={`company-${id}`}
                      checked={selectedIds.has(id)}
                      onCheckedChange={(checked) => toggleOne(checked, id)}
                      disabled={extractMutation.isPending}
                    />
                    <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <Building2 className="w-4 h-4 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{name}</p>
                      <p className="text-xs text-muted-foreground truncate">{domain || 'No domain'}</p>
                    </div>
                    {tier && (
                      <span className={`text-xs flex-shrink-0 ${tierColors[tier] || 'text-muted-foreground'}`}>
                        Tier {tier}
                      </span>
                    )}
                    {!domain && (
                      <Badge variant="outline" className="text-[10px] px-1.5 h-5 flex-shrink-0 text-muted-foreground">
                        No domain
                      </Badge>
                    )}
                  </label>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── Contacts search & table ───────────────────────────────────────── */}
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
                const id         = contact.id           || contact['ID']             || idx;
                const fullName   = contact.full_name    || contact['Full Name']      || '';
                const role       = contact.role         || contact['Role']           || '';
                const company    = contact.company_name || contact['Company Name']   || '';
                const email      = contact.email        || contact['Email']          || '';
                const confidence = contact.confidence_score || contact['Confidence Score'];
                const status     = contact.status       || contact['Status']         || '';

                return (
                  <TableRow key={id} className="hover:bg-muted/30">
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center flex-shrink-0">
                          <span className="text-xs font-bold text-accent">
                            {fullName?.[0]?.toUpperCase() || '?'}
                          </span>
                        </div>
                        <span className="font-medium text-sm">{fullName || '—'}</span>
                        {cooldownMap[email] && (
                          <span
                            title="Already contacted within 90 days — outreach skipped."
                            className="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 cursor-help border border-amber-200 flex-shrink-0"
                          >
                            ⏱ In Cooldown
                          </span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">{role || '—'}</TableCell>
                    <TableCell className="text-sm">{company || '—'}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{email || '—'}</TableCell>
                    <TableCell>
                      {confidence ? (
                        <span
                          className={`text-xs font-semibold ${
                            confidence >= 70 ? 'text-emerald-600'
                            : confidence >= 50 ? 'text-amber-600'
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