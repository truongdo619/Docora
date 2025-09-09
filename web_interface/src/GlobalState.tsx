// src/GlobalState.tsx
import React, { createContext, useEffect, useMemo, useState, ReactNode } from 'react';
// import defaultSettings from '../settings.json';

type BratOutput = any; // tighten this when you have a shape

export type DomainSettingsMap = Record<string, AppSettings>;


// Shape of your settings.json (add more fields as needed)
export interface AppSettings {
  apiBaseUrl?: string;
  bratBaseUrl?: string; // e.g. "/js/client" or full URL
  [key: string]: any;
}

interface GlobalContextType {
  bratOutput: BratOutput | null;
  documentId: string | null;
  updateId: number;
  fileName: string | null;

  settings: AppSettings;
  setSettings: (s: AppSettings) => void;

  
  // multi-domain settings (fetched from backend)
  domainSettings: DomainSettingsMap;
  setDomainSettings: (m: DomainSettingsMap) => void;
  supportedDomains: string[];
  setSupportedDomains: (ds: string[]) => void;

  // which domain is currently active
  currentDomain: string | null;
  setCurrentDomain: (d: string | null) => void;

  setBratOutput: (bratOutput: BratOutput) => void;
  setDocumentId: (documentId: string | null) => void;
  setUpdateId: (updateId: number) => void;
  setFileName: (fileName: string | null) => void;
}

export const GlobalContext = createContext<GlobalContextType | undefined>(undefined);

interface GlobalProviderProps {
  children: ReactNode;
}

export const GlobalProvider: React.FC<GlobalProviderProps> = ({ children }) => {
  const [bratOutput, setBratOutput] = useState<BratOutput | null>(null);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [updateId, setUpdateId] = useState<number>(-1);
  const [fileName, setFileName] = useState<string | null>(null);


  // Active settings (start with bundled defaults; can be overridden by per-domain)
  const [settings, setSettings] = useState<AppSettings>({});

  // Multi-domain
  const [domainSettings, setDomainSettings] = useState<DomainSettingsMap>({});
  const [supportedDomains, setSupportedDomains] = useState<string[]>([]);
  const [currentDomain, setCurrentDomain] = useState<string | null>(null);

  // Utility to load a script once
  const loadScript = (url: string) =>
    new Promise<void>((resolve, reject) => {
      // If already present, resolve immediately
      if (document.querySelector(`script[src="${url}"]`)) {
        resolve();
        return;
      }
      const script = document.createElement('script');
      script.src = url;
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error(`Failed to load script: ${url}`));
      document.body.appendChild(script);
    });

  useEffect(() => {
    // Load BRAT assets based on settings
    const bratBase = settings.bratBaseUrl || 'https://www.jaist.ac.jp/is/labs/nguyen-lab/systems/docora/assets/js/client';
    const scripts = [
      `${bratBase}/lib/jquery.min.js`,
      `${bratBase}/lib/jquery.svg.min.js`,
      `${bratBase}/lib/jquery.svgdom.min.js`,
      `${bratBase}/src/configuration.js`,
      `${bratBase}/src/util.js`,
      `${bratBase}/src/annotation_log.js`,
      `${bratBase}/lib/webfont.js`,
      `${bratBase}/src/dispatcher.js`,
      `${bratBase}/src/url_monitor.js`,
      `${bratBase}/src/visualizer.js`,
    ];

    let cancelled = false;
    const loadAll = async () => {
      try {
        await scripts.reduce(
          (p, url) => p.then(() => (cancelled ? Promise.resolve() : loadScript(url))),
          Promise.resolve()
        );
      } catch (e) {
        // Optional: surface this via a toast/logger
        // console.error(e);
      }
    };
    loadAll();
    return () => {
      cancelled = true;
    };
  }, [settings.bratBaseUrl]); // re-run only if the base URL changes


  // auto-apply per-domain settings when currentDomain changes
  useEffect(() => {
    if (!currentDomain) return;
    const domainCfg = domainSettings[currentDomain];
    if (domainCfg) {
      setSettings((prev) => ({ ...prev, ...domainCfg }));
    }
  }, [currentDomain, domainSettings]);

  const value = useMemo<GlobalContextType>(
    () => ({
      bratOutput,
      documentId,
      updateId,
      fileName,

      settings,
      setSettings,

      domainSettings,
      setDomainSettings,
      supportedDomains,
      setSupportedDomains,

      currentDomain,
      setCurrentDomain,

      setBratOutput,
      setDocumentId,
      setUpdateId,
      setFileName,
    }),
    [
      bratOutput,
      documentId,
      updateId,
      fileName,
      settings,
      domainSettings,
      supportedDomains,
      currentDomain,
    ]
  );

  return <GlobalContext.Provider value={value}>{children}</GlobalContext.Provider>;
};
