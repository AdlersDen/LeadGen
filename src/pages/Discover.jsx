// @ts-nocheck
import React, { useState, useRef, useEffect, useMemo } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/api/apiClient';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { MapPin, Search, Building2, Users, Loader2, CheckCircle2, AlertCircle, Building } from 'lucide-react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import RunAlert from '@/components/RunAlert';

// // ─── Global business complex suggestions ─────────────────────────────────────
const COMPLEXES = [
  // Mumbai
  'Bandra Kurla Complex Mumbai',
  'Mindspace Business Park Malad Mumbai',
  'Nesco IT Park Goregaon Mumbai',
  'Oberoi Commerz Goregaon Mumbai',
  'Peninsula Corporate Park Lower Parel Mumbai',
  'Equinox Business Park Kurla Mumbai',
  'Supreme Business Park Powai Mumbai',
  '72 Business Park Andheri East Mumbai',
  'One BKC Mumbai',
  'Nariman Point Mumbai',
  'Andheri MIDC Mumbai',
  // Pune
  'Hinjewadi IT Park Pune',
  'Magarpatta City Pune',
  'EON IT Park Kharadi Pune',
  'World Trade Center Pune',
  'Panchshil Tech Park Pune',
  // Bangalore
  'Manyata Tech Park Bangalore',
  'Electronic City Bangalore',
  'Bagmane Tech Park Bangalore',
  'RMZ Ecospace Bangalore',
  'Embassy Golf Links Bangalore',
  'Prestige Tech Park Bangalore',
  // Hyderabad
  'HITEC City Hyderabad',
  'Cyberabad Hyderabad',
  'Mindspace IT Park Hyderabad',
  'DLF Cybercity Hyderabad',
  // Delhi NCR
  'Cyber City Gurugram',
  'DLF Cyber Hub Gurugram',
  'Unitech Cyber Park Gurugram',
  'Noida Special Economic Zone',
  'World Trade Tower Noida',
  'Connaught Place New Delhi',
  // Chennai
  'Tidel Park Chennai',
  'RMZ Millenia Chennai',
  'DLF IT Park Chennai',
  // Navi Mumbai / Thane
  'Belapur CBD Navi Mumbai',
  'Vashi Navi Mumbai',
  'Thane Wagle Estate',
  'Gigaplex Estate Airoli',
  // Dubai
  'Dubai Internet City',
  'Dubai Media City',
  'DIFC Dubai',
  'Dubai Silicon Oasis',
  'Business Bay Dubai',
  'Jumeirah Lake Towers Dubai',
  // Singapore
  'One Raffles Place Singapore',
  'Marina Bay Financial Centre Singapore',
  'Mapletree Business City Singapore',
  'one-north Singapore',
  // London
  'Canary Wharf London',
  'The Shard London',
  'City of London',
  'White City Place London',
  'Hammersmith London',
  // New York
  'Hudson Yards New York',
  'World Trade Center New York',
  'Midtown Manhattan New York',
  'Silicon Alley New York',
  // San Francisco
  'Financial District San Francisco',
  'South of Market San Francisco',
  'Silicon Valley California',
  // Other global
  'La Defense Paris',
  'Zuidas Amsterdam',
  'Frankfurt Financial District',
  'ADGM Abu Dhabi',
  'Bahrain Financial Harbour',
  'Bonifacio Global City Manila',
  'Ortigas Center Manila',
  'Sudirman Central Business District Jakarta',
];

// ─── Industry filter options ──────────────────────────────────────────────────
const INDUSTRIES = [
  { label: 'IT / Tech',          value: 'tech' },
  { label: 'Event Management',   value: 'events' },
  { label: 'Real Estate',        value: 'realestate' },
  { label: 'Finance & Banking',  value: 'finance' },
  { label: 'Consulting',         value: 'consulting' },
  { label: 'Manufacturing',      value: 'manufacturing' },
  { label: 'Marketing & Media',  value: 'marketing' },
  { label: 'Pharma & Health',    value: 'pharma' },
  { label: 'Logistics',          value: 'logistics' },
  { label: 'Education',          value: 'education' },
];

// ─── Tier options ─────────────────────────────────────────────────────────────
const TIERS = [
  { label: 'Tier A',  value: 'A', subtitle: 'Priority',    badge: 'bg-emerald-100 text-emerald-700' },
  { label: 'Tier B',  value: 'B', subtitle: 'Standard',    badge: 'bg-slate-100 text-slate-600' },
  { label: 'Tier C',  value: 'C', subtitle: 'Low signal',  badge: 'bg-slate-100 text-slate-400' },
];

export default function Discover() {
  // ─── Mode ──────────────────────────────────────────────────────────────────
  const [searchMode, setSearchMode]           = useState('pincode');   // 'pincode' | 'complex'

  // ─── Inputs ────────────────────────────────────────────────────────────────
  const [pincode, setPincode]                 = useState('');
  const [complexName, setComplexName]         = useState('');
  const [radiusKm, setRadiusKm]               = useState(2);
  const [suggestions, setSuggestions]         = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  // ─── Filters ───────────────────────────────────────────────────────────────
  const [selectedIndustries, setSelectedIndustries] = useState(new Set());
  const [selectedTiers, setSelectedTiers]           = useState(new Set(['A', 'B']));

  // ─── Search hint (shown below complex input) ──────────────────────────────
  const [searchHint, setSearchHint] = useState('');

  // ─── Errors ────────────────────────────────────────────────────────────────
  const [pincodeError, setPincodeError]   = useState('');
  const [complexError, setComplexError]   = useState('');

  // ─── Results ───────────────────────────────────────────────────────────────
  const [discoveredCompanies, setDiscoveredCompanies] = useState([]);
  const [step, setStep]                               = useState('input'); // input | discovering | done
  const [errorMsg, setErrorMsg]                       = useState('');
  const [runAlert, setRunAlert]                       = useState(null);

  const [slowWarning, setSlowWarning] = useState(false);
  const slowTimerRef = useRef(null);
  const queryClient  = useQueryClient();
  const suggestRef   = useRef(null);

  // ─── Close suggestions when clicking outside ──────────────────────────────
  useEffect(() => {
    const handler = (e) => {
      if (suggestRef.current && !suggestRef.current.contains(e.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // ─── Complex suggestions filter ───────────────────────────────────────────
  const handleComplexInput = (val) => {
    setComplexName(val);
    setComplexError('');
    setSearchHint(val.trim() ? `Will search: "corporate offices in ${val.trim()}"` : "");
    if (val.length >= 2) {
      const q = val.toLowerCase();
      setSuggestions(COMPLEXES.filter((s) => s.toLowerCase().includes(q)).slice(0, 8));
      setShowSuggestions(true);
    } else {
      setShowSuggestions(false);
    }
  };

  // ─── Industry chip toggle ─────────────────────────────────────────────────
  const toggleIndustry = (val) => {
    setSelectedIndustries((prev) => {
      const next = new Set(prev);
      next.has(val) ? next.delete(val) : next.add(val);
      return next;
    });
  };

  // ─── Tier checkbox toggle ─────────────────────────────────────────────────
  const toggleTier = (val) => {
    setSelectedTiers((prev) => {
      const next = new Set(prev);
      next.has(val) ? next.delete(val) : next.add(val);
      return next;
    });
  };

  // ─── Industry summary line ────────────────────────────────────────────────
  const industrySummary = useMemo(() => {
    if (selectedIndustries.size === 0) return 'All industries included';
    const labels = INDUSTRIES
      .filter((i) => selectedIndustries.has(i.value))
      .map((i) => i.label);
    return `Filtering: ${labels.join(', ')}`;
  }, [selectedIndustries]);

  // ─── Mutation ─────────────────────────────────────────────────────────────
  const discoverMutation = useMutation({
    mutationFn: async (payload) => {
      setStep('discovering');
      setErrorMsg('');
      setRunAlert(null);
      setSlowWarning(false);
      // Show slow warning after 25s (Render cold-starts can take ~30s)
      slowTimerRef.current = setTimeout(() => setSlowWarning(true), 25000);
      return apiClient.post('/discover', payload);
    },
    onSuccess: (data) => {
      clearTimeout(slowTimerRef.current);
      setSlowWarning(false);
      setDiscoveredCompanies(data.companies || []);
      setStep('done');
      
      const count = data.companies_found || 0;
      if (count === 0) {
        setRunAlert({
          type: "error",
          title: "0 Companies Discovered",
          body: `We couldn't find any corporate prospects in ${data.location_name || 'this area'}. Try a different pincode or complex.`,
          action: "none"
        });
      } else {
        setRunAlert({
          type: "success",
          title: `${count} Companies Discovered`,
          body: `We found ${count} companies in ${data.location_name || 'this area'}. Next, extract their contacts.`,
          action: "extract"
        });
      }
      
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      toast.success(`Found ${data.companies_found || 0} companies${data.location_name ? ` in ${data.location_name}` : ''}!`);
    },
    onError: (err) => {
      clearTimeout(slowTimerRef.current);
      setSlowWarning(false);
      setStep('input');
      setErrorMsg(err.message || 'Discovery failed. Please try again.');
      toast.error(err.message || 'Discovery failed. Please try again.');
    },
  });

  // ─── Submit handler ───────────────────────────────────────────────────────
  const handleDiscover = () => {
    const tiers      = Array.from(selectedTiers);
    const industries = Array.from(selectedIndustries);

    if (searchMode === 'pincode') {
      const code = pincode.trim();
      if (!code || !/^\d{6}$/.test(code)) {
        setPincodeError('Please enter a valid 6-digit pincode.');
        return;
      }
      setPincodeError('');
      discoverMutation.mutate({ pincode: code, radius_km: radiusKm, industries, tiers });
    } else {
      const name = complexName.trim();
      if (!name) {
        setComplexError('Please enter or select a business complex name.');
        return;
      }
      setComplexError('');
      discoverMutation.mutate({ complex_name: name, industries, tiers });
    }
  };

  const resetSearch = () => {
    clearTimeout(slowTimerRef.current);
    setSlowWarning(false);
    setStep('input');
    setPincode('');
    setComplexName('');
    setDiscoveredCompanies([]);
    setErrorMsg('');
    setRunAlert(null);
    setSearchHint('');
  };

  const isSearching = step === 'discovering';

  return (
    <div className="space-y-8">
      {/* ── Page title (unchanged) ─────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          {searchMode === 'pincode' ? 'Pincode Discovery' : 'Business Complex Discovery'}
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          {searchMode === 'pincode'
            ? 'Enter a 6-digit pincode to discover B2B companies in the area'
            : 'Search by business complex or area name to find corporate tenants'}
        </p>
      </div>

      {/* ── Search card ───────────────────────────────────────────────── */}
      <div className="bg-card rounded-xl border border-border p-6 space-y-6">

        {/* ── Mode toggle tabs ─────────────────────────────────────────── */}
        <div className="flex items-center gap-1 bg-muted rounded-lg p-1 w-fit">
          {[
            { key: 'pincode',  label: 'By Pincode',                    icon: MapPin },
            { key: 'complex',  label: 'By Business Complex / Area',    icon: Building },
          ].map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              type="button"
              id={`mode-tab-${key}`}
              onClick={() => { setSearchMode(key); setPincodeError(''); setComplexError(''); }}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 ${
                searchMode === key
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        {/* ── By Pincode ───────────────────────────────────────────────── */}
        {searchMode === 'pincode' && (
          <div className="space-y-2">
            <label className="text-sm font-medium">Pincode</label>
            <div className="flex gap-3">
              <Input
                id="pincode-input"
                placeholder="e.g. 400051"
                value={pincode}
                onChange={(e) => { setPincode(e.target.value); setPincodeError(''); }}
                onKeyDown={(e) => e.key === 'Enter' && handleDiscover()}
                className={`max-w-[180px] text-center text-lg font-medium h-11 ${pincodeError ? 'border-destructive' : ''}`}
                disabled={isSearching}
                maxLength={6}
              />

              {/* Radius dropdown */}
              <div className="flex flex-col gap-1">
                <select
                  id="radius-select"
                  value={radiusKm}
                  onChange={(e) => setRadiusKm(Number(e.target.value))}
                  disabled={isSearching}
                  className="h-11 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value={1}>1 km</option>
                  <option value={2}>2 km</option>
                  <option value={5}>5 km</option>
                  <option value={10}>10 km</option>
                </select>
              </div>

              <Button
                id="discover-btn"
                onClick={handleDiscover}
                disabled={isSearching || !pincode.trim()}
                className="h-11 px-6 gap-2"
              >
                {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                {isSearching ? 'Searching…' : 'Discover'}
              </Button>
            </div>
            {pincodeError && (
              <p className="flex items-center gap-1.5 text-xs text-destructive">
                <AlertCircle className="w-3.5 h-3.5" /> {pincodeError}
              </p>
            )}
          </div>
        )}

        {/* ── By Business Complex ─────────────────────────────────────── */}
        {searchMode === 'complex' && (
          <div className="space-y-2">
            <label className="text-sm font-medium">Business Complex or Area</label>
            <div className="flex gap-3">
              <div className="relative flex-1 max-w-md" ref={suggestRef}>
                <Input
                  id="complex-input"
                  placeholder="e.g. Bandra Kurla Complex, Mindspace Malad…"
                  value={complexName}
                  onChange={(e) => handleComplexInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleDiscover()}
                  className={`h-11 ${complexError ? 'border-destructive' : ''}`}
                  disabled={isSearching}
                />

                {/* Suggestions dropdown */}
                {showSuggestions && suggestions.length > 0 && (
                  <ul className="absolute z-50 mt-1 w-full rounded-md border border-border bg-popover shadow-lg max-h-52 overflow-y-auto">
                    {suggestions.map((s) => (
                      <li
                        key={s}
                        className="px-3 py-2.5 text-sm cursor-pointer hover:bg-muted transition-colors flex items-center gap-2"
                        onMouseDown={(e) => {
                          e.preventDefault(); // prevent blur before click
                          setComplexName(s);
                          setShowSuggestions(false);
                          setComplexError('');
                          setSearchHint(`Will search: "corporate offices in ${s}"`);
                        }}
                      >
                        <Building className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                        {s}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <Button
                id="discover-complex-btn"
                onClick={handleDiscover}
                disabled={isSearching || !complexName.trim()}
                className="h-11 px-6 gap-2"
              >
                {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                {isSearching ? 'Searching…' : 'Discover'}
              </Button>
            </div>
            {complexError && (
              <p className="flex items-center gap-1.5 text-xs text-destructive">
                <AlertCircle className="w-3.5 h-3.5" /> {complexError}
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              Search any business park, IT park, or commercial district worldwide. Google Maps will return corporate tenants inside it.
            </p>
            {searchHint && (
              <p className="text-xs text-muted-foreground/80 mt-1 flex items-center gap-1">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-primary/50 flex-shrink-0" />
                {searchHint}
              </p>
            )}
          </div>
        )}

        {/* ── Industry filter chips ─────────────────────────────────────── */}
        <div className="space-y-3 border-t border-border pt-5">
          <div>
            <p className="text-sm font-medium">Filter by Industry</p>
            <p className="text-xs text-muted-foreground mt-0.5">(optional — select one or more)</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {INDUSTRIES.map(({ label, value }) => {
              const active = selectedIndustries.has(value);
              return (
                <button
                  key={value}
                  type="button"
                  id={`industry-chip-${value}`}
                  onClick={() => toggleIndustry(value)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all duration-150 ${
                    active
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border bg-background text-muted-foreground hover:border-primary/40 hover:text-foreground'
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
          <p className={`text-xs ${selectedIndustries.size > 0 ? 'text-primary font-medium' : 'text-muted-foreground'}`}>
            {industrySummary}
          </p>
        </div>

        {/* ── Company Tier filter ───────────────────────────────────────── */}
        <div className="space-y-3 border-t border-border pt-5">
          <p className="text-sm font-medium">Company Tier</p>
          <div className="flex flex-wrap gap-4">
            {TIERS.map(({ label, value, subtitle, badge }) => {
              const checked = selectedTiers.has(value);
              return (
                <label
                  key={value}
                  htmlFor={`tier-${value}`}
                  className="flex items-center gap-2.5 cursor-pointer select-none"
                >
                  <input
                    type="checkbox"
                    id={`tier-${value}`}
                    checked={checked}
                    onChange={() => toggleTier(value)}
                    className="w-4 h-4 rounded border-border accent-primary cursor-pointer"
                  />
                  <span className="text-sm font-medium">{label}</span>
                  <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${badge}`}>
                    {subtitle}
                  </span>
                </label>
              );
            })}
          </div>
        </div>

        {/* Inline error fallback */}
        {errorMsg && (
          <div className="flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="w-4 h-4" />
            {errorMsg}
          </div>
        )}
      </div>

      {runAlert && (
        <RunAlert message={runAlert} onClose={() => setRunAlert(null)} />
      )}

      {/* ── Progress indicator (unchanged) ────────────────────────────── */}
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
                <p className="font-medium">
                  Discovering companies{searchMode === 'pincode' ? ` near ${pincode}` : ` in ${complexName}`}…
                </p>
                <p className="text-sm text-muted-foreground">
                  Querying Google Maps, filtering B2B businesses, saving to database
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Results (unchanged) ───────────────────────────────────────── */}
      <AnimatePresence>
        {step === 'done' && discoveredCompanies.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            <div className="flex items-center gap-3 flex-wrap">
              <CheckCircle2 className="w-5 h-5 text-emerald-500" />
              <h3 className="font-semibold">{discoveredCompanies.length} Companies Discovered</h3>
              <Button variant="outline" size="sm" onClick={resetSearch}>
                New Search
              </Button>
              <Link to="/contacts">
                <Button size="sm" className="gap-1.5">
                  <Users className="w-3.5 h-3.5" /> Extract Contacts ?
                </Button>
              </Link>
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

        {step === 'done' && discoveredCompanies.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-card rounded-xl border border-border p-12 text-center"
          >
            <div className="w-16 h-16 rounded-2xl bg-muted/50 flex items-center justify-center mx-auto mb-4">
              <Search className="w-8 h-8 text-muted-foreground" />
            </div>
            <h3 className="text-xl font-semibold">0 Companies Discovered</h3>
            <p className="text-muted-foreground mt-2 max-w-md mx-auto">
              We couldn't find any corporate prospects here. Try a different pincode or business complex.
            </p>
            <Button variant="outline" className="mt-6" onClick={resetSearch}>
              New Search
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}