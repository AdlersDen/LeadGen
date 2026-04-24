import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/apiClient';
import { Mail, Send, Loader2, Sparkles, Search, Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import StatusBadge from '@/components/shared/StatusBadge';
import { toast } from 'sonner';
import { format } from 'date-fns';

export default function Outreach() {
  const [search, setSearch] = useState('');
  const [showCompose, setShowCompose] = useState(false);
  const [selectedContactId, setSelectedContactId] = useState('');
  const [generatedPitch, setGeneratedPitch] = useState({ subject: '', body: '' });
  const [previewLog, setPreviewLog] = useState(null);
  const queryClient = useQueryClient();

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
        role: contact.role || contact['Role'],
        company_name: contact.company_name || contact['Company Name'],
      });
    },
    onSuccess: (data) => {
      setGeneratedPitch({ subject: data.subject, body: data.body });
    },
    onError: (err) => {
      toast.error(err.message || 'Pitch generation failed');
    },
  });

  const sendEmailMutation = useMutation({
    mutationFn: async () => {
      const contact = contacts.find((c) => (c.id || c['ID']) === selectedContactId);
      if (!contact) throw new Error('Contact not found');

      const email = contact.email || contact['Email'];
      if (!email) throw new Error('This contact has no email address');

      return apiClient.post('/outreach/send', {
        contact_id: contact.id || contact['ID'],
        contact_name: contact.full_name || contact['Full Name'],
        contact_email: email,
        company_name: contact.company_name || contact['Company Name'],
        subject: generatedPitch.subject,
        body: generatedPitch.body,
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
      toast.success('Email sent successfully via SendGrid!');
    },
    onError: (err) => {
      toast.error(err.message || 'Failed to send email');
    },
  });

  const filtered = logs.filter((l) => {
    const name = l.contact_name || l['Contact Name'] || '';
    const company = l.company_name || l['Company Name'] || '';
    const email = l.contact_email || l['Contact Email'] || '';
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
            <Button className="gap-2">
              <Mail className="w-4 h-4" /> Compose Email
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>AI-Powered Outreach</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 pt-2">
              <Select
                value={selectedContactId}
                onValueChange={(val) => { setSelectedContactId(val); setGeneratedPitch({ subject: '', body: '' }); }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a contact" />
                </SelectTrigger>
                <SelectContent>
                  {contacts
                    .filter((c) => c.email || c['Email'])
                    .map((c, i) => {
                      const id = c.id || c['ID'] || i;
                      return (
                        <SelectItem key={id} value={id}>
                          {c.full_name || c['Full Name']} — {c.company_name || c['Company Name']}
                        </SelectItem>
                      );
                    })}
                </SelectContent>
              </Select>

              {selectedContactId && !generatedPitch.subject && (
                <Button
                  variant="outline"
                  className="w-full gap-2"
                  disabled={generatePitchMutation.isPending}
                  onClick={() => generatePitchMutation.mutate(selectedContactId)}
                >
                  {generatePitchMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4" />
                  )}
                  {generatePitchMutation.isPending ? 'Generating via Gemini...' : 'Generate AI Pitch'}
                </Button>
              )}

              {generatedPitch.subject && (
                <>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Subject</label>
                    <Input
                      value={generatedPitch.subject}
                      onChange={(e) => setGeneratedPitch((p) => ({ ...p, subject: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Body</label>
                    <Textarea
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
                    >
                      <Sparkles className="w-4 h-4" /> Regenerate
                    </Button>
                    <Button
                      className="flex-1 gap-2"
                      disabled={sendEmailMutation.isPending}
                      onClick={() => sendEmailMutation.mutate()}
                    >
                      {sendEmailMutation.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Send className="w-4 h-4" />
                      )}
                      Send via SendGrid
                    </Button>
                  </div>
                </>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          placeholder="Search outreach..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      <div className="bg-card rounded-xl border border-border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50">
              <TableHead>Contact</TableHead>
              <TableHead>Company</TableHead>
              <TableHead>Subject</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Sent</TableHead>
              <TableHead></TableHead>
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
                const id = log.id || log['ID'] || idx;
                const name = log.contact_name || log['Contact Name'];
                const email = log.contact_email || log['Contact Email'];
                const company = log.company_name || log['Company Name'];
                const subject = log.subject || log['Subject'];
                const status = log.status || log['Status'];
                const timestamp = log.sent_date || log['Timestamp'] || log.created_date;

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
                      <Button variant="ghost" size="icon" onClick={() => setPreviewLog(log)}>
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

      {/* Email Preview Dialog */}
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