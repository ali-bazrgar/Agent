import React from 'react';
import { Activity, Database, ShieldCheck, Terminal, BookOpen, Cpu, Code2, MessageSquare, Network, Settings, Sun, Moon } from 'lucide-react';
import { SystemHealth } from '../types';

interface NavbarProps {
  health: SystemHealth | null;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  darkMode: boolean;
  setDarkMode: (value: boolean) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ health, activeTab, setActiveTab, darkMode, setDarkMode }) => {
  const tabs = [
    ['chat', 'Chat', MessageSquare], ['overview', 'Dashboard', Activity], ['datacenter', 'Data Center', Database],
    ['knowledge_graph', 'Knowledge Graph', Network], ['learning', 'Learning', BookOpen], ['executions', 'Execution', Cpu],
    ['settings', 'Settings', Settings], ['api', 'REST API', Code2],
  ] as const;
  const healthy = health?.status === 'ok' || health?.status === 'healthy';

  return (
    <header className="app-header sticky top-0 z-50">
      <div className="w-full max-w-[1500px] mx-auto px-4 sm:px-6 xl:px-8">
        <div className="flex items-center justify-between gap-4 min-h-[68px]">
          <button onClick={() => setActiveTab('chat')} className="flex items-center gap-3 text-left shrink-0" aria-label="Open chat">
            <div className="brand-mark"><Terminal className="w-5 h-5" /></div>
            <div className="hidden sm:block">
              <div className="flex items-center gap-2"><span className="font-semibold tracking-tight text-[15px]">SuperAgent</span><span className="status-chip">LOCAL</span></div>
              <p className="muted text-[11px] mt-0.5">AI knowledge & orchestration workspace</p>
            </div>
          </button>
          <div className="flex items-center gap-2">
            <div className="hidden lg:flex items-center gap-2 status-chip">
              <span className={`status-dot ${healthy ? 'online' : 'offline'}`} />
              <span>{healthy ? 'Runtime healthy' : 'Runtime unavailable'}</span>
            </div>
            <button className="icon-button" onClick={() => setDarkMode(!darkMode)} title={darkMode ? 'Switch to light theme' : 'Switch to dark theme'} aria-label="Toggle theme">
              {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
            <div className="hidden md:flex items-center gap-1.5 text-xs muted"><ShieldCheck className="w-4 h-4" /> Local-first</div>
          </div>
        </div>
        <nav className="nav-scroll" aria-label="Primary navigation">
          {tabs.map(([id, label, Icon]) => (
            <button key={id} onClick={() => setActiveTab(id)} className={`nav-item ${activeTab === id ? 'active' : ''}`} aria-current={activeTab === id ? 'page' : undefined}>
              <Icon className="w-4 h-4" /><span>{label}</span>
            </button>
          ))}
        </nav>
      </div>
    </header>
  );
};
