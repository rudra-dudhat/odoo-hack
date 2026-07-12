import { api } from '../services/api.js';

export async function renderAudits() {
  try {
    const response = await api.get('/audit-cycles');
    const cycles = response.data || [];
    const activeCycle = cycles[0] || {};

    return `
      <div class="animate-slide-in">
        <div class="flex items-center justify-between mb-6">
          <h1 class="text-2xl font-outfit font-bold text-white">Audit Cycles</h1>
          <button class="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors flex items-center gap-2 shadow-lg shadow-blue-900/20">
            <i data-lucide="play" class="w-4 h-4"></i>
            Start New Audit
          </button>
        </div>

        <div class="glass-panel p-6 mb-6">
          <h2 class="text-lg font-medium text-white mb-4">${activeCycle.name || 'Active Cycle: No audits available'}</h2>
          
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm text-slate-400">Overall Progress</span>
            <span class="text-sm font-bold text-blue-400">${activeCycle.progress || 0}%</span>
          </div>
          <div class="w-full bg-slate-800 rounded-full h-2.5 mb-6 overflow-hidden">
            <div class="bg-blue-600 h-2.5 rounded-full" style="width: ${activeCycle.progress || 0}%"></div>
          </div>
          
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="bg-slate-800/50 rounded-lg p-3 text-center border border-slate-700/50">
              <div class="text-2xl font-bold text-white mb-1">${activeCycle.totalItems || 0}</div>
              <div class="text-xs text-slate-400 uppercase tracking-wider">Total Items</div>
            </div>
            <div class="bg-slate-800/50 rounded-lg p-3 text-center border border-slate-700/50">
              <div class="text-2xl font-bold text-emerald-400 mb-1">${activeCycle.verified || 0}</div>
              <div class="text-xs text-slate-400 uppercase tracking-wider">Verified</div>
            </div>
            <div class="bg-slate-800/50 rounded-lg p-3 text-center border border-slate-700/50">
              <div class="text-2xl font-bold text-amber-400 mb-1">${activeCycle.discrepancies || 0}</div>
              <div class="text-xs text-slate-400 uppercase tracking-wider">Discrepancies</div>
            </div>
            <div class="bg-slate-800/50 rounded-lg p-3 text-center border border-slate-700/50">
              <div class="text-2xl font-bold text-slate-300 mb-1">${activeCycle.pending || 0}</div>
              <div class="text-xs text-slate-400 uppercase tracking-wider">Pending</div>
            </div>
          </div>
        </div>
      </div>
    `;
  } catch (error) {
    console.error('Failed to load audits', error);
    return `
      <div class="animate-slide-in">
        <div class="glass-panel p-6 text-red-400">Unable to load audit cycles from the backend.</div>
      </div>
    `;
  }
}
