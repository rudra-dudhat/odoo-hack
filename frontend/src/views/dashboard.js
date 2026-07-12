import { api } from '../services/api.js';

export async function renderDashboard() {
  try {
    const response = await api.get('/dashboard');
    const summary = response || {};

    return `
      <div class="animate-slide-in">
        <h1 class="text-2xl font-outfit font-bold text-white mb-6">Dashboard</h1>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div class="glass-card p-6 glass-card-hover">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-slate-400 font-medium">Total Assets</h3>
              <div class="p-2 bg-blue-500/20 text-blue-400 rounded-lg">
                <i data-lucide="boxes" class="w-5 h-5"></i>
              </div>
            </div>
            <div class="text-3xl font-bold text-white">${summary.totalAssets ?? 0}</div>
            <div class="text-sm text-emerald-400 mt-2 flex items-center gap-1">
              <i data-lucide="trending-up" class="w-4 h-4"></i>
              <span>Live from Firestore</span>
            </div>
          </div>

          <div class="glass-card p-6 glass-card-hover">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-slate-400 font-medium">Active Allocations</h3>
              <div class="p-2 bg-indigo-500/20 text-indigo-400 rounded-lg">
                <i data-lucide="users" class="w-5 h-5"></i>
              </div>
            </div>
            <div class="text-3xl font-bold text-white">${summary.activeAllocations ?? 0}</div>
            <div class="text-sm text-slate-400 mt-2">Current active assignments</div>
          </div>

          <div class="glass-card p-6 glass-card-hover border-amber-500/30">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-amber-400 font-medium">Overdue Allocations</h3>
              <div class="p-2 bg-amber-500/20 text-amber-400 rounded-lg">
                <i data-lucide="wrench" class="w-5 h-5"></i>
              </div>
            </div>
            <div class="text-3xl font-bold text-white">${summary.overdueAllocations ?? 0}</div>
            <div class="text-sm text-amber-400 mt-2 flex items-center gap-1">
              <i data-lucide="alert-circle" class="w-4 h-4"></i>
              <span>${summary.openMaintenanceRequests ?? 0} open maintenance requests</span>
            </div>
          </div>

          <div class="glass-card p-6 glass-card-hover">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-slate-400 font-medium">Today's Bookings</h3>
              <div class="p-2 bg-purple-500/20 text-purple-400 rounded-lg">
                <i data-lucide="calendar-check" class="w-5 h-5"></i>
              </div>
            </div>
            <div class="text-3xl font-bold text-white">${summary.bookingsToday ?? 0}</div>
            <div class="text-sm text-slate-400 mt-2">Shared resources</div>
          </div>
        </div>

        <div class="glass-panel p-6 border-red-500/30 mb-8 flex items-start gap-4">
          <div class="p-3 bg-red-500/20 text-red-400 rounded-full mt-1">
            <i data-lucide="alert-triangle" class="w-6 h-6"></i>
          </div>
          <div>
            <h3 class="text-lg font-semibold text-white mb-1">Operations Snapshot</h3>
            <p class="text-slate-300 mb-3">There are ${summary.openMaintenanceRequests ?? 0} open maintenance requests and ${summary.overdueAllocations ?? 0} overdue allocations to follow up on.</p>
            <button class="bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/50 px-4 py-2 rounded-lg text-sm font-medium transition-colors">
              Refresh Data
            </button>
          </div>
        </div>
      </div>
    `;
  } catch (error) {
    console.error('Failed to load dashboard', error);
    return `
      <div class="animate-slide-in">
        <h1 class="text-2xl font-outfit font-bold text-white mb-6">Dashboard</h1>
        <div class="glass-panel p-6 text-red-400">Unable to load dashboard data from the backend.</div>
      </div>
    `;
  }
}
