// @ts-nocheck
import React from 'react';
import { AlertCircle, CheckCircle2, Info, AlertTriangle, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';

export default function RunAlert({ message, onClose }) {
  if (!message) return null;

  const { type, title, body, action } = message;

  const styles = {
    error: {
      bg: 'bg-red-50/50',
      border: 'border-red-200',
      text: 'text-red-900',
      title: 'text-red-800',
      body: 'text-red-700',
      icon: <AlertCircle className="w-5 h-5 text-red-600" />,
      btn: 'bg-red-600 hover:bg-red-700 text-white'
    },
    warning: {
      bg: 'bg-amber-50/50',
      border: 'border-amber-200',
      text: 'text-amber-900',
      title: 'text-amber-800',
      body: 'text-amber-700',
      icon: <AlertTriangle className="w-5 h-5 text-amber-600" />,
      btn: 'bg-amber-600 hover:bg-amber-700 text-white'
    },
    success: {
      bg: 'bg-emerald-50/50',
      border: 'border-emerald-200',
      text: 'text-emerald-900',
      title: 'text-emerald-800',
      body: 'text-emerald-700',
      icon: <CheckCircle2 className="w-5 h-5 text-emerald-600" />,
      btn: 'bg-emerald-600 hover:bg-emerald-700 text-white'
    },
    info: {
      bg: 'bg-blue-50/50',
      border: 'border-blue-200',
      text: 'text-blue-900',
      title: 'text-blue-800',
      body: 'text-blue-700',
      icon: <Info className="w-5 h-5 text-blue-600" />,
      btn: 'bg-blue-600 hover:bg-blue-700 text-white'
    }
  };

  const currentStyle = styles[type] || styles.info;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        className={`relative p-4 rounded-xl border flex items-start gap-3 mb-6 ${currentStyle.bg} ${currentStyle.border} ${currentStyle.text}`}
      >
        <button 
          onClick={onClose}
          className="absolute top-2 right-2 p-1 rounded-md opacity-50 hover:opacity-100 transition-opacity"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="mt-0.5">
          {currentStyle.icon}
        </div>

        <div className="flex-1">
          <h4 className={`text-sm font-semibold ${currentStyle.title}`}>
            {title}
          </h4>
          <p className={`text-sm mt-1 ${currentStyle.body}`}>
            {body}
          </p>
          
          {action === 'extract' && (
            <div className="mt-3">
              <Link to="/contacts">
                <Button size="sm" className={currentStyle.btn}>
                  Go to Contacts Extraction
                </Button>
              </Link>
            </div>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
