import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import apiClient from '@/api/apiClient';
import { CheckCircle2, Loader2, AlertCircle, MailX } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function Unsubscribe() {
  const [searchParams] = useSearchParams();
  const email = searchParams.get('email') || '';

  const [status, setStatus] = useState('idle'); // idle | loading | success | error
  const [errorMsg, setErrorMsg] = useState('');

  const handleUnsubscribe = async () => {
    if (!email) return;
    setStatus('loading');
    try {
      await apiClient.post('/unsubscribe', { email });
      setStatus('success');
    } catch (err) {
      setErrorMsg(err.message || 'Something went wrong. Please try again.');
      setStatus('error');
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6">
      <div className="w-full max-w-md text-center space-y-6">

        {/* Icon */}
        <div className="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center mx-auto">
          {status === 'success'
            ? <CheckCircle2 className="w-8 h-8 text-emerald-500" />
            : status === 'error'
            ? <AlertCircle className="w-8 h-8 text-destructive" />
            : <MailX className="w-8 h-8 text-muted-foreground" />
          }
        </div>

        {/* Content */}
        {status === 'success' ? (
          <>
            <h1 className="text-2xl font-bold tracking-tight">You've been unsubscribed</h1>
            <p className="text-muted-foreground text-sm">
              <span className="font-medium text-foreground">{email}</span> has been removed from
              our outreach list. You will no longer receive emails from Adler's Den.
            </p>
            <p className="text-xs text-muted-foreground">
              If this was a mistake, please contact us at{' '}
              <a href="mailto:marketing@adlersden.com" className="underline">
                marketing@adlersden.com
              </a>
            </p>
          </>
        ) : status === 'error' ? (
          <>
            <h1 className="text-2xl font-bold tracking-tight">Something went wrong</h1>
            <p className="text-muted-foreground text-sm">{errorMsg}</p>
            <Button variant="outline" onClick={handleUnsubscribe}>Try Again</Button>
          </>
        ) : (
          <>
            <h1 className="text-2xl font-bold tracking-tight">Unsubscribe</h1>
            {email ? (
              <>
                <p className="text-muted-foreground text-sm">
                  You're about to unsubscribe{' '}
                  <span className="font-medium text-foreground">{email}</span> from all future
                  outreach emails from Adler's Den.
                </p>
                <Button
                  className="w-full gap-2"
                  onClick={handleUnsubscribe}
                  disabled={status === 'loading'}
                >
                  {status === 'loading'
                    ? <><Loader2 className="w-4 h-4 animate-spin" /> Unsubscribing…</>
                    : 'Confirm Unsubscribe'
                  }
                </Button>
                <p className="text-xs text-muted-foreground">
                  This action cannot be undone from this page.
                </p>
              </>
            ) : (
              <p className="text-muted-foreground text-sm">
                No email address provided. Please use the unsubscribe link from the email you received.
              </p>
            )}
          </>
        )}

        {/* Branding footer */}
        <p className="text-xs text-muted-foreground pt-4 border-t border-border">
          © Adler's Den · Premium Corporate Gifting &amp; Employee Engagement
        </p>
      </div>
    </div>
  );
}
