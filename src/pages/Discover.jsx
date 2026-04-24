import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/apiClient';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { MapPin, Search, Building2, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';

export default function Discover() {
  const [pincode, setPincode] = useState('');
  const [discoveredCompanies, setDiscoveredCompanies] = useState([]);
  const [step, setStep] = useState('input'); // input | discovering | done
  const [errorMsg, setErrorMsg] = useState('');
  const queryClient = useQueryClient();

  const discoverMutation = useMutation({
    mutationFn: async (code) => {
      setStep('discovering');
      setErrorMsg('');
      // POST /api/discover → runs Maps discovery + saves to Sheets
      return apiClient.post('/discover', { pincode: code });
    },
    onSuccess: (data) => {
      setDiscoveredCompanies(data.companies || []);
      setStep('done');
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      toast.success(`Found ${data.companies_found || 0} companies in ${data.location_name}!`);
    },
    onError: (err) => {
      setStep('input');
      setErrorMsg(err.message || 'Discovery failed. Please try again.');
      toast.error(err.message || 'Discovery failed. Please try again.');
    },
  });

  const handleDiscover = () => {
    if (!pincode.trim()) return;
    discoverMutation.mutate(pincode.trim());
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Pincode Discovery</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Enter a pincode to discover B2B companies in the area
        </p>
      </div>

      {/* Input Section */}
      <div className="bg-card rounded-xl border border-border p-8">
        <div className="max-w-xl mx-auto text-center space-y-6">
          <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto">
            <MapPin className="w-8 h-8 text-primary" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">Enter Pincode</h2>
            <p className="text-sm text-muted-foreground mt-1">
              We'll discover corporate prospects in this area using Google Maps
            </p>
          </div>
          <div className="flex gap-3 max-w-sm mx-auto">
            <Input
              placeholder="e.g. 400001"
              value={pincode}
              onChange={(e) => setPincode(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleDiscover()}
              className="text-center text-lg font-medium h-12"
              disabled={step === 'discovering'}
              maxLength={6}
            />
            <Button
              onClick={handleDiscover}
              disabled={step === 'discovering' || !pincode.trim()}
              className="h-12 px-6 gap-2"
            >
              {step === 'discovering' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Search className="w-4 h-4" />
              )}
              {step === 'discovering' ? 'Searching...' : 'Discover'}
            </Button>
          </div>

          {/* Inline error */}
          {errorMsg && (
            <div className="flex items-center gap-2 justify-center text-sm text-destructive">
              <AlertCircle className="w-4 h-4" />
              {errorMsg}
            </div>
          )}
        </div>
      </div>

      {/* Progress indicator */}
      <AnimatePresence>
        {step === 'discovering' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="bg-card rounded-xl border border-border p-6"
          >
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                <Loader2 className="w-5 h-5 text-primary animate-spin" />
              </div>
              <div>
                <p className="font-medium">Discovering companies near {pincode}...</p>
                <p className="text-sm text-muted-foreground">
                  Querying Google Maps, filtering B2B businesses, saving to database
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Results */}
      <AnimatePresence>
        {step === 'done' && discoveredCompanies.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-500" />
              <h3 className="font-semibold">{discoveredCompanies.length} Companies Discovered</h3>
              <Button
                variant="outline"
                size="sm"
                onClick={() => { setStep('input'); setPincode(''); setDiscoveredCompanies([]); }}
              >
                New Search
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {discoveredCompanies.map((company, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="bg-card rounded-xl border border-border p-4 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <Building2 className="w-5 h-5 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-sm truncate">{company.name}</p>
                      <p className="text-xs text-muted-foreground truncate">{company.address}</p>
                      <div className="flex items-center gap-2 mt-2 flex-wrap">
                        {company.industry && (
                          <Badge variant="secondary" className="text-xs">{company.industry}</Badge>
                        )}
                        {company.domain && (
                          <Badge variant="outline" className="text-xs">{company.domain}</Badge>
                        )}
                        {company.google_rating && (
                          <span className="text-xs text-amber-600 font-medium">
                            ★ {company.google_rating}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}