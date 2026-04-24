import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function PipelineChart({ companies }) {
  const statusCounts = {
    discovered: 0,
    contacts_found: 0,
    pitched: 0,
    emailed: 0,
    replied: 0,
    converted: 0,
  };

  companies.forEach(c => {
    if (statusCounts[c.status] !== undefined) {
      statusCounts[c.status]++;
    }
  });

  const data = [
    { name: 'Discovered', value: statusCounts.discovered, fill: 'hsl(217, 91%, 60%)' },
    { name: 'Contacts', value: statusCounts.contacts_found, fill: 'hsl(262, 83%, 58%)' },
    { name: 'Pitched', value: statusCounts.pitched, fill: 'hsl(43, 96%, 56%)' },
    { name: 'Emailed', value: statusCounts.emailed, fill: 'hsl(162, 63%, 41%)' },
    { name: 'Replied', value: statusCounts.replied, fill: 'hsl(217, 91%, 70%)' },
    { name: 'Converted', value: statusCounts.converted, fill: 'hsl(162, 63%, 51%)' },
  ];

  return (
    <div className="bg-card rounded-xl border border-border p-6">
      <h3 className="font-semibold text-base mb-4">Pipeline Overview</h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} barSize={32} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }} axisLine={false} tickLine={false} />
          <Tooltip 
            contentStyle={{ 
              background: 'hsl(var(--card))', 
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
              fontSize: '13px'
            }} 
          />
          <Bar dataKey="value" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}