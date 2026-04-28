import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/apiClient';
import {
  Mail, Send, Loader2, Sparkles, Search, Eye,
  CheckCircle2, AlertCircle, ChevronDown, X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import StatusBadge from '@/components/shared/StatusBadge';
import { toast } from 'sonner';
import { format } from 'date-fns';

// ─── Searchable Contact Combobox ──────────────────────────────────────────────
function ContactCombobox({ contacts, value, onChange }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');

  const emailContacts = contacts.filter((c) => c.email || c['Email']);

  const filtered = useMemo(() => {
    if (!query) return emailContacts;
    const q = query.toLowerCase();
    return emailContacts.filter((c) => {
      const name    = (c.full_name    || c['Full Name']    || '').toLowerCase();
      const company = (c.company_name || c['Company Name'] || '').toLowerCase();
      const email   = (c.email        || c['Email']        || '').toLowerCase();
      return name.includes(q) || company.includes(q) || email.includes(q);
    });
  }, [query, contacts]);

  const selected = emailContacts.find(
    (c) => (c.id || c['ID']) === value
  );

  const handleSelect = (c) => {
    onChange(c.id || c['ID']);
    setQuery('');
    setOpen(false);
  };

  const handleClear = (e) => {
    e.stopPropagation();
    onChange('');
    setQuery('');
  };

  return (
    <div className="relative">
      {/* Trigger */}
      <button
        type="button"
        className="w-full flex items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="listbox"
        id="contact-combobox-trigger"
      >
        {selected ? (
          <span className="truncate">
            {selected.full_name || selected['Full Name']}
            <span className="text-muted-foreground ml-1.5 text-xs">
              — {selected.company_name || selected['Company Name']}
            </span>
          </span>
        ) : (
          <span className="text-muted-foreground">Select a contact…</span>
        )}
        <span className="flex items-center gap-1 flex-shrink-0 ml-2">
          {selected && (
            <X
              className="w-3 h-3 text-muted-foreground hover:text-foreground"
              onClick={handleClear}
            />
          )}
          <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform ${open ? 'rotate-180' : ''}`} />
        </span>
      </button>

      {/* Dropdown */}
      {open && (
        <div
          className="absolute z-50 mt-1 w-full rounded-md border border-border bg-popover shadow-lg"
          role="listbox"
          id="contact-combobox-list"
        >
          {/* Search input */}
          <div className="p-2 border-b border-border">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
              <input
                autoFocus
                className="w-full pl-8 pr-3 py-1.5 text-sm bg-muted rounded border-0 outline-none focus:ring-1 focus:ring-ring"
                placeholder={`Search ${emailContacts.length} contacts…`}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                id="contact-combobox-search"
              />
            </div>
          </div>

          {/* Results */}
          <ul className="max-h-60 overflow-y-auto py-1">
            {filtered.length === 0 ? (
              <li className="px-3 py-4 text-center text-sm text-muted-foreground">
                No contacts match "{query}"
              </li>
            ) : (
              filtered.map((c, i) => {
                const id    = c.id    || c['ID'] || i;
                const name  = c.full_name    || c['Full Name']    || '—';
                const co    = c.company_name || c['Company Name'] || '';
                const email = c.email        || c['Email']        || '';
                const isSelected = id === value;

                return (
                  <li
                    key={id}
                    role="option"
                    aria-selected={isSelected}
                    className={`px-3 py-2 cursor-pointer flex items-center gap-2 hover:bg-muted transition-colors ${isSelected ? 'bg-muted' : ''}`}
                    onClick={() => handleSelect(c)}
                  >
                    <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 text-xs font-bold text-primary">
                      {name[0]?.toUpperCase() || '?'}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{name}</p>
                      <p className="text-xs text-muted-foreground truncate">{co} · {email}</p>
                    </div>
                    {isSelected && <CheckCircle2 className="w-4 h-4 text-primary flex-shrink-0" />}
                  </li>
                );
              })
            )}
          </ul>

          {/* Footer count */}
          <div className="px-3 py-1.5 border-t border-border">
            <p className="text-[11px] text-muted-foreground">
              {filtered.length} of {emailContacts.length} contacts with email
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function Outreach() {
  const [search, setSearch]                 = useState('');
  const [showCompose, setShowCompose]       = useState(false);
  const [selectedContactId, setSelectedContactId] = useState('');
  const [generatedPitch, setGeneratedPitch] = useState({ subject: '', body: '' });
  const [previewLog, setPreviewLog]         = useState(null);
  const queryClient                         = useQueryClient();

  const { data: logs = [], isLoading } = useQuery({
    queryKey: ['outreach'],
    queryFn: () => apiClient.get('/outreach'),
  });

  const { data: contacts = [] } = useQuery({
    queryKey: ['contacts'],
    queryFn: () => apiClient.get('/contacts'),
  });

  const generatePitchMutation = useMutation({
    mutationFn: async (contactId) => {
      const contact = contacts.find((c) => (c.id || c['ID']) === contactId);
      if (!contact) throw new Error('Contact not found');
      return apiClient.post('/pitches/generate', {
        contact_name: contact.full_name || contact['Full Name'],
        role:         contact.role      || contact['Role'],
        company_name: contact.company_name || contact['Company Name'],
      });
    },
    onSuccess: (data) => setGeneratedPitch({ subject: data.subject, body: data.body }),
    onError:   (err)  => toast.error(err.message || 'Pitch generation failed'),
  });

  const sendEmailMutation = useMutation({
    mutationFn: async () => {
      const contact = contacts.find((c) => (c.id || c['ID']) === selectedContactId);
      if (!contact) throw new Error('Contact not found');
      const email = contact.email || contact['Email'];
      if (!email) throw new Error('This contact has no email address');
      return apiClient.post('/outreach/send', {
        contact_id:    contact.id    || contact['ID'],
        contact_name:  contact.full_name || contact['Full Name'],
        contact_email: email,
        company_name:  contact.company_name || contact['Company Name'],
        subject: generatedPitch.subject,
        body:    generatedPitch.body,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['outreach'] });
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      setShowCompose(false);
      setGeneratedPitch({ subject: '', body: '' });
      setSelectedContactId('');
      toast.success('Email sent via marketing@adlersden.com!');
    },
    onError: (err) => toast.error(err.message || 'Failed to send email'),
  });

  const filtered = logs.filter((l) => {
    const name    = l.contact_name  || l['Contact Name'] || '';
    const company = l.company_name  || l['Company Name'] || '';
    const email   = l.contact_email || l['Contact Email'] || '';
    return (
      !search ||
      name.toLowerCase().includes(search.toLowerCase()) ||
      company.toLowerCase().includes(search.toLowerCase()) ||
      email.toLowerCase().includes(search.toLowerCase())
    );
  });

  const resetCompose = () => {
    setGeneratedPitch({ subject: '', body: '' });
    setSelectedContactId('');
  };

  return (
    <div className="space-y-6">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Outreach</h1>
          <p className="text-muted-foreground text-sm mt-1">{logs.length} emails tracked</p>
        </div>

        <Dialog
          open={showCompose}
          onOpenChange={(open) => { setShowCompose(open); if (!open) resetCompose(); }}
        >
          <DialogTrigger asChild>
            <Button className="gap-2" id="compose-email-btn">
              <Mail className="w-4 h-4" /> Compose Email
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>AI-Powered Outreach</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 pt-2">

              {/* ── Searchable contact picker ── */}
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Contact</label>
                <ContactCombobox
                  contacts={contacts}
                  value={selectedContactId}
                  onChange={(id) => {
                    setSelectedContactId(id);
                    setGeneratedPitch({ subject: '', body: '' });
                  }}
                />
              </div>

              {selectedContactId && !generatedPitch.subject && (
                <Button
                  variant="outline"
                  className="w-full gap-2"
                  disabled={generatePitchMutation.isPending}
                  onClick={() => generatePitchMutation.mutate(selectedContactId)}
                  id="generate-pitch-btn"
                >
                  {generatePitchMutation.isPending
                    ? <><Loader2 className="w-4 h-4 animate-spin" /> Generating via Gemini…</>
                    : <><Sparkles className="w-4 h-4" /> Generate AI Pitch</>}
                </Button>
              )}

              {generatedPitch.subject && (
                <>
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium">Subject</label>
                    <Input
                      id="pitch-subject"
                      value={generatedPitch.subject}
                      onChange={(e) => setGeneratedPitch((p) => ({ ...p, subject: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium">Body</label>
                    <Textarea
                      id="pitch-body"
                      value={generatedPitch.body}
                      onChange={(e) => setGeneratedPitch((p) => ({ ...p, body: e.target.value }))}
                      rows={8}
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      className="flex-1 gap-2"
                      disabled={generatePitchMutation.isPending}
                      onClick={() => generatePitchMutation.mutate(selectedContactId)}
                      id="regenerate-pitch-btn"
                    >
                      <Sparkles className="w-4 h-4" /> Regenerate
                    </Button>
                    <Button
                      className="flex-1 gap-2"
                      disabled={sendEmailMutation.isPending}
                      onClick={() => sendEmailMutation.mutate()}
                      id="send-email-btn"
                    >
                      {sendEmailMutation.isPending
                        ? <><Loader2 className="w-4 h-4 animate-spin" /> Sending…</>
                        : <><Send className="w-4 h-4" /> Send via SendGrid</>}
                    </Button>
                  </div>
                </>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* ── Search bar ──────────────────────────────────────────────────── */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          id="outreach-search"
          placeholder="Search outreach…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* ── Table ───────────────────────────────────────────────────────── */}
      <div className="bg-card rounded-xl border border-border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50">
              <TableHead>Contact</TableHead>
              <TableHead>Company</TableHead>
              <TableHead>Subject</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Sent</TableHead>
              <TableHead />
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
                  No outreach emails yet
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((log, idx) => {
                const id        = log.id || log['ID'] || idx;
                const name      = log.contact_name  || log['Contact Name'];
                const email     = log.contact_email || log['Contact Email'];
                const company   = log.company_name  || log['Company Name'];
                const subject   = log.subject       || log['Subject'];
                const status    = log.status        || log['Status'];
                const timestamp = log.sent_date     || log['Timestamp'] || log.created_date;

                return (
                  <TableRow key={id} className="hover:bg-muted/30">
                    <TableCell>
                      <div>
                        <p className="font-medium text-sm">{name || email}</p>
                        <p className="text-xs text-muted-foreground">{email}</p>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm">{company}</TableCell>
                    <TableCell className="text-sm text-muted-foreground max-w-[200px] truncate">
                      {subject}
                    </TableCell>
                    <TableCell><StatusBadge status={status} /></TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {timestamp ? format(new Date(timestamp), 'MMM d, h:mm a') : '—'}
                    </TableCell>
                    <TableCell>
                      <Button variant="ghost" size="icon" onClick={() => setPreviewLog(log)} aria-label="Preview email">
                        <Eye className="w-4 h-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* ── Email Preview Dialog ─────────────────────────────────────────── */}
      <Dialog open={!!previewLog} onOpenChange={(open) => !open && setPreviewLog(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Email Preview</DialogTitle>
          </DialogHeader>
          {previewLog && (
            <div className="space-y-4 pt-2">
              <div>
                <p className="text-xs text-muted-foreground">To</p>
                <p className="text-sm font-medium">
                  {previewLog.contact_name || previewLog['Contact Name']} &lt;
                  {previewLog.contact_email || previewLog['Contact Email']}&gt;
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Subject</p>
                <p className="text-sm font-medium">{previewLog.subject || previewLog['Subject']}</p>
              </div>
              <div className="border-t pt-4">
                <p className="text-sm whitespace-pre-wrap">
                  {previewLog.body || previewLog['AI Pitch Body']}
                </p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}