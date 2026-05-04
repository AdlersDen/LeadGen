import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/apiClient';
import {
  Mail, Send, Loader2, Sparkles, Search, CheckCircle2, AlertCircle
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import StatusBadge from '@/components/shared/StatusBadge';
import { toast } from 'sonner';
import { format } from 'date-fns';

export default function Outreach() {
  const [search, setSearch] = useState('');
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [showCompose, setShowCompose] = useState(false);
  const [pitchData, setPitchData] = useState({}); 
  const [isSendingAll, setIsSendingAll] = useState(false);
  const [sendingProgress, setSendingProgress] = useState(0);

  const abortControllerRef = useRef(null);
  const queryClient = useQueryClient();

  // ── Data Fetching ─────────────────────────────────────────────────────────

  const { data: contacts = [], isLoading: isContactsLoading } = useQuery({
    queryKey: ['contacts'],
    queryFn: () => apiClient.get('/contacts'),
  });

  const { data: logs = [] } = useQuery({
    queryKey: ['outreach'],
    queryFn: () => apiClient.get('/outreach'),
  });

  const { data: cooldownMap = {} } = useQuery({
    queryKey: ['cooldown-status'],
    queryFn: () => apiClient.get('/contacts/cooldown-status'),
    staleTime: 60_000,
  });

  // ── Helper derived data ───────────────────────────────────────────────────

  const validContacts = useMemo(() => contacts.filter(c => c.email || c['Email']), [contacts]);

  const filteredContacts = useMemo(() => {
    if (!search) return validContacts;
    const q = search.toLowerCase();
    return validContacts.filter(c => {
      const name = (c.full_name || c['Full Name'] || '').toLowerCase();
      const comp = (c.company_name || c['Company Name'] || '').toLowerCase();
      const em   = (c.email || c['Email'] || '').toLowerCase();
      return name.includes(q) || comp.includes(q) || em.includes(q);
    });
  }, [search, validContacts]);

  // Determine selectable rows (not in cooldown)
  const selectableIds = useMemo(() => {
    return filteredContacts.filter(c => {
      const em = (c.email || c['Email'] || '').trim();
      return !cooldownMap[em];
    }).map(c => c.id || c['ID']);
  }, [filteredContacts, cooldownMap]);

  const allSelected = selectableIds.length > 0 && selectableIds.every(id => selectedIds.has(id));

  const toggleSelectAll = (checked) => {
    if (checked) {
      setSelectedIds(new Set(selectableIds));
    } else {
      setSelectedIds(new Set());
    }
  };

  const toggleOne = (checked, id) => {
    const next = new Set(selectedIds);
    if (checked) next.add(id);
    else next.delete(id);
    setSelectedIds(next);
  };

  // ── Fetch Pitches Sequentially on Modal Open ──────────────────────────────

  useEffect(() => {
    if (!showCompose || selectedIds.size === 0) return;

    abortControllerRef.current = new AbortController();
    const ids = Array.from(selectedIds);

    const fetchPitches = async () => {
      for (const id of ids) {
        if (abortControllerRef.current?.signal.aborted) break;

        const contact = validContacts.find(c => (c.id || c['ID']) === id);
        if (!contact) continue;

        // Skip if already fetched
        setPitchData(prev => {
          if (prev[id]) return prev;
          return { ...prev, [id]: { loading: true } };
        });

        try {
          const payload = {
            contact_name: contact.full_name || contact['Full Name'],
            role: contact.role || contact['Role'],
            company_name: contact.company_name || contact['Company Name'],
          };
          
          const res = await apiClient.post('/pitches/generate', payload);
          
          if (!abortControllerRef.current?.signal.aborted) {
            setPitchData(prev => ({
              ...prev,
              [id]: {
                loading: false,
                ai_pitch: res.ai_pitch,
                predefined_pitch: res.predefined_pitch,
                choice: 'predefined',
                final_subject: res.predefined_pitch.subject,
                final_body: res.predefined_pitch.body,
                status: 'pending' // pending, sending, sent, error
              }
            }));
          }
          // Slight delay to be kind to Gemini API limits
          await new Promise(r => setTimeout(r, 1000));
        } catch (err) {
          if (!abortControllerRef.current?.signal.aborted) {
            setPitchData(prev => ({
              ...prev,
              [id]: { loading: false, error: err.message || 'Failed to generate pitch' }
            }));
          }
        }
      }
    };

    fetchPitches();

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [showCompose, selectedIds, validContacts]);


  // ── Handle Sending ────────────────────────────────────────────────────────

  const handleSendAll = async () => {
    setIsSendingAll(true);
    setSendingProgress(0);
    const ids = Array.from(selectedIds);
    let sentCount = 0;

    for (const id of ids) {
      const data = pitchData[id];
      if (!data || data.loading || data.error || data.status === 'sent') {
        setSendingProgress(p => p + 1);
        continue;
      }

      const contact = validContacts.find(c => (c.id || c['ID']) === id);
      const email = contact.email || contact['Email'];

      setPitchData(prev => ({ ...prev, [id]: { ...prev[id], status: 'sending' } }));

      try {
        await apiClient.post('/outreach/send', {
          contact_id: id,
          contact_name: contact.full_name || contact['Full Name'],
          contact_email: email,
          company_name: contact.company_name || contact['Company Name'],
          subject: data.final_subject,
          body: data.final_body,
        });
        
        setPitchData(prev => ({ ...prev, [id]: { ...prev[id], status: 'sent' } }));
        sentCount++;
        
        // Invalidate immediately so background badges update
        queryClient.invalidateQueries({ queryKey: ['outreach'] });
        queryClient.invalidateQueries({ queryKey: ['cooldown-status'] });
      } catch (err) {
        setPitchData(prev => ({ ...prev, [id]: { ...prev[id], status: 'error', error_msg: err.message } }));
        toast.error(`Failed to send to ${email}: ${err.message}`);
      }

      setSendingProgress(p => p + 1);
      
      // 5-second delay between emails as requested (if not the last one)
      if (id !== ids[ids.length - 1]) {
        await new Promise(r => setTimeout(r, 5000));
      }
    }

    setIsSendingAll(false);
    if (sentCount > 0) {
      toast.success(`Successfully sent ${sentCount} emails.`);
      setSelectedIds(new Set()); // clear selection after success
      setTimeout(() => setShowCompose(false), 1500);
    }
  };


  // ── Render Helpers ────────────────────────────────────────────────────────

  const updatePitch = (id, field, value) => {
    setPitchData(prev => ({
      ...prev,
      [id]: { ...prev[id], [field]: value }
    }));
  };

  const setChoice = (id, choice) => {
    const data = pitchData[id];
    if (!data) return;
    const source = choice === 'ai' ? data.ai_pitch : data.predefined_pitch;
    setPitchData(prev => ({
      ...prev,
      [id]: { ...data, choice, final_subject: source.subject, final_body: source.body }
    }));
  };

  return (
    <div className="space-y-6">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Outreach Compose</h1>
          <p className="text-muted-foreground text-sm mt-1">{validContacts.length} contacts available for outreach</p>
        </div>

        <Dialog open={showCompose} onOpenChange={(open) => {
          if (!open && isSendingAll) return; // prevent closing while sending
          setShowCompose(open);
          if (!open) setPitchData({}); // reset state on close
        }}>
          <DialogTrigger asChild>
            <Button className="gap-2" disabled={selectedIds.size === 0}>
              <Mail className="w-4 h-4" /> 
              Send to Selected ({selectedIds.size})
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-6xl w-[90vw] max-h-[90vh] flex flex-col p-0 overflow-hidden">
            <div className="p-6 border-b border-border flex justify-between items-center bg-muted/30">
              <div>
                <DialogTitle className="text-xl">Review & Send Outreach</DialogTitle>
                <DialogDescription className="mt-1">
                  Review the predefined and AI-generated pitches for your {selectedIds.size} selected contacts.
                </DialogDescription>
              </div>
            </div>

            {/* Scrollable List of Contacts */}
            <div className="flex-1 overflow-y-auto p-6 space-y-8 bg-muted/10">
              {Array.from(selectedIds).map((id) => {
                const contact = validContacts.find(c => (c.id || c['ID']) === id);
                if (!contact) return null;
                const data = pitchData[id];

                return (
                  <div key={id} className={`bg-card border rounded-xl shadow-sm overflow-hidden transition-all ${data?.status === 'sent' ? 'opacity-50 grayscale' : ''}`}>
                    {/* Header */}
                    <div className="bg-muted/40 px-5 py-3 border-b flex justify-between items-center">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 text-xs font-bold text-primary">
                          {(contact.full_name || contact['Full Name'] || '?')[0].toUpperCase()}
                        </div>
                        <div>
                          <p className="font-semibold text-sm">{contact.full_name || contact['Full Name']}</p>
                          <p className="text-xs text-muted-foreground">
                            {contact.role || contact['Role']} at {contact.company_name || contact['Company Name']} · {contact.email || contact['Email']}
                          </p>
                        </div>
                      </div>
                      <div>
                        {data?.status === 'sending' && <Badge className="bg-amber-500"><Loader2 className="w-3 h-3 animate-spin mr-1"/> Sending</Badge>}
                        {data?.status === 'sent' && <Badge className="bg-emerald-500"><CheckCircle2 className="w-3 h-3 mr-1"/> Sent</Badge>}
                        {data?.status === 'error' && <Badge variant="destructive"><AlertCircle className="w-3 h-3 mr-1"/> Error</Badge>}
                      </div>
                    </div>

                    {/* Content */}
                    <div className="p-5">
                      {!data || data.loading ? (
                        <div className="py-12 flex flex-col items-center justify-center text-muted-foreground space-y-3">
                          <Loader2 className="w-8 h-8 animate-spin text-primary/50" />
                          <p className="text-sm font-medium">Generating pitches...</p>
                        </div>
                      ) : data.error ? (
                        <div className="py-6 text-center text-destructive flex flex-col items-center">
                          <AlertCircle className="w-8 h-8 mb-2" />
                          <p className="text-sm">{data.error}</p>
                        </div>
                      ) : (
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                          
                          {/* Left Panel: Options */}
                          <div className="space-y-4">
                            <h3 className="text-sm font-semibold flex items-center gap-2 text-muted-foreground uppercase tracking-wider">
                              1. Select Base Template
                            </h3>
                            
                            <div className="grid grid-cols-2 gap-4">
                              {/* Predefined Option */}
                              <div className={`border rounded-lg p-4 cursor-pointer transition-all ${data.choice === 'predefined' ? 'ring-2 ring-primary border-primary bg-primary/5' : 'hover:border-foreground/30'}`}
                                   onClick={() => setChoice(id, 'predefined')}>
                                <div className="flex justify-between items-center mb-2">
                                  <span className="font-semibold text-sm">Predefined Template</span>
                                  {data.choice === 'predefined' && <CheckCircle2 className="w-4 h-4 text-primary" />}
                                </div>
                                <p className="text-xs text-muted-foreground line-clamp-4">{data.predefined_pitch.body}</p>
                              </div>

                              {/* AI Option */}
                              <div className={`border rounded-lg p-4 cursor-pointer transition-all ${data.choice === 'ai' ? 'ring-2 ring-primary border-primary bg-primary/5' : 'hover:border-foreground/30'}`}
                                   onClick={() => setChoice(id, 'ai')}>
                                <div className="flex justify-between items-center mb-2">
                                  <span className="font-semibold text-sm flex items-center gap-1.5"><Sparkles className="w-3.5 h-3.5 text-amber-500" /> AI Generated</span>
                                  {data.choice === 'ai' && <CheckCircle2 className="w-4 h-4 text-primary" />}
                                </div>
                                <p className="text-xs text-muted-foreground line-clamp-4">{data.ai_pitch.body}</p>
                              </div>
                            </div>
                          </div>

                          {/* Right Panel: Editor */}
                          <div className="space-y-4">
                             <h3 className="text-sm font-semibold flex items-center gap-2 text-muted-foreground uppercase tracking-wider">
                              2. Review & Edit
                            </h3>
                            <div className="space-y-3">
                              <Input 
                                value={data.final_subject} 
                                onChange={e => updatePitch(id, 'final_subject', e.target.value)}
                                className="font-medium"
                                placeholder="Subject line"
                                disabled={data.status === 'sending' || data.status === 'sent'}
                              />
                              <Textarea 
                                value={data.final_body}
                                onChange={e => updatePitch(id, 'final_body', e.target.value)}
                                rows={8}
                                className="resize-none text-sm"
                                placeholder="Email body"
                                disabled={data.status === 'sending' || data.status === 'sent'}
                              />
                            </div>
                          </div>

                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Footer Action */}
            <div className="p-4 border-t border-border bg-background flex justify-between items-center">
              <div className="text-sm text-muted-foreground">
                {isSendingAll && (
                  <span className="flex items-center gap-2">
                     <Loader2 className="w-4 h-4 animate-spin" />
                     Sending {sendingProgress + 1} of {selectedIds.size}... (5s delay between sends)
                  </span>
                )}
              </div>
              <Button 
                size="lg" 
                className="gap-2 px-8" 
                onClick={handleSendAll}
                disabled={isSendingAll || selectedIds.size === 0}
              >
                {isSendingAll ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                {isSendingAll ? 'Sending...' : `Send All (${selectedIds.size})`}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* ── Search & Filters ────────────────────────────────────────────── */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          placeholder="Search contacts by name, company, or email..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* ── Contacts Table (Checklist) ────────────────────────────────────── */}
      <div className="bg-card rounded-xl border border-border overflow-hidden">
        <div className="px-4 py-3 bg-muted/40 border-b border-border flex items-center gap-3">
          <Checkbox
            id="select-all"
            checked={allSelected}
            onCheckedChange={toggleSelectAll}
            disabled={isContactsLoading || selectableIds.length === 0}
          />
          <label htmlFor="select-all" className="text-sm font-medium cursor-pointer select-none">
            {isContactsLoading
              ? 'Loading contacts...'
              : `Select All (${selectableIds.length} eligible)`}
          </label>
        </div>

        <div className="max-h-[600px] overflow-y-auto">
          <Table>
            <TableHeader className="sticky top-0 bg-muted/90 backdrop-blur z-10 shadow-sm">
              <TableRow>
                <TableHead className="w-12"></TableHead>
                <TableHead>Contact</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Company</TableHead>
                <TableHead>Confidence</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isContactsLoading ? (
                Array(5).fill(0).map((_, i) => (
                  <TableRow key={i}>
                    {Array(6).fill(0).map((_, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-24" /></TableCell>
                    ))}
                  </TableRow>
                ))
              ) : filteredContacts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-12 text-muted-foreground">
                    No valid contacts found. Extract contacts first.
                  </TableCell>
                </TableRow>
              ) : (
                filteredContacts.map((contact, idx) => {
                  const id         = contact.id           || contact['ID']             || idx;
                  const fullName   = contact.full_name    || contact['Full Name']      || '';
                  const role       = contact.role         || contact['Role']           || '';
                  const company    = contact.company_name || contact['Company Name']   || '';
                  const email      = contact.email        || contact['Email']          || '';
                  const confidence = contact.confidence_score || contact['Confidence Score'];
                  const status     = contact.status       || contact['Status']         || '';
                  
                  const emTrimmed  = email.trim();
                  const isCooldown = !!cooldownMap[emTrimmed];

                  // Find log to show date
                  const matchedLog = isCooldown ? logs.find(l => (l.contact_email || l['Contact Email']) === emTrimmed) : null;
                  const logDate = matchedLog ? (matchedLog.sent_date || matchedLog['Timestamp'] || matchedLog.created_date) : null;

                  return (
                    <TableRow key={id} className={`hover:bg-muted/30 ${isCooldown ? 'opacity-60 bg-muted/10' : ''}`}>
                      <TableCell>
                        <Checkbox
                          checked={selectedIds.has(id)}
                          onCheckedChange={(checked) => toggleOne(checked, id)}
                          disabled={isCooldown}
                        />
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center flex-shrink-0">
                            <span className="text-xs font-bold text-accent">
                              {fullName?.[0]?.toUpperCase() || '?'}
                            </span>
                          </div>
                          <div>
                            <span className="font-medium text-sm block">{fullName || '—'}</span>
                            <span className="text-xs text-muted-foreground block">{email}</span>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">{role || '—'}</TableCell>
                      <TableCell className="text-sm font-medium">{company || '—'}</TableCell>
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
                      <TableCell>
                        {isCooldown ? (
                           <div className="inline-flex flex-col gap-1">
                             <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 border border-amber-200 whitespace-nowrap">
                               ⏱ Already Sent
                             </span>
                             {logDate && (
                               <span className="text-[10px] text-muted-foreground ml-1">
                                 {format(new Date(logDate), 'MMM d, yyyy')}
                               </span>
                             )}
                           </div>
                        ) : (
                           <StatusBadge status={status} />
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}