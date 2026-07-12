import { api } from '../services/api.js';
import { showToast } from '../components/toast.js';

export async function renderAllocations() {
  let allocationsHtml = '';
  try {
    const response = await api.get('/asset-allocations');
    const allocations = response.data || [];
    const counts = allocations.reduce((acc, allocation) => {
      acc.active += allocation.status === 'active' ? 1 : 0;
      acc.overdue += allocation.status === 'overdue' ? 1 : 0;
      return acc;
    }, { active: 0, overdue: 0 });

    if (allocations.length === 0) {
      allocationsHtml = `
        <div class="p-8 text-center text-slate-400">
          <i data-lucide="users" class="w-12 h-12 mx-auto mb-4 opacity-50"></i>
          <p>No allocations are available yet.</p>
        </div>
      `;
    } else {
      allocationsHtml = allocations.map(allocation => `
        <div class="border border-slate-700/50 rounded-lg p-4 bg-slate-800/40">
          <div class="flex items-center justify-between mb-2">
            <div class="font-medium text-white">${allocation.assetSnapshot?.name || allocation.assetId}</div>
            <span class="px-2 py-1 rounded-full text-xs font-medium ${allocation.status === 'overdue' ? 'bg-amber-500/10 text-amber-400' : 'bg-emerald-500/10 text-emerald-400'}">${allocation.status}</span>
          </div>
          <div class="text-sm text-slate-400">Assigned to ${allocation.employeeSnapshot?.fullName || allocation.employeeId}</div>
          <div class="text-xs text-slate-500 mt-2">Allocated ${allocation.allocatedAt ? new Date(allocation.allocatedAt).toLocaleDateString() : '—'}</div>
        </div>
      `).join('');
    }

    return `
      <div class="animate-slide-in">
        <div class="flex items-center justify-between mb-6">
          <h1 class="text-2xl font-outfit font-bold text-white">Asset Allocations</h1>
          <button id="btn-allocate-asset" class="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors flex items-center gap-2 shadow-lg shadow-blue-900/20">
            <i data-lucide="user-plus" class="w-4 h-4"></i>
            Allocate Asset
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div class="glass-card p-5">
            <div class="text-sm text-slate-400 font-medium mb-1">Active Allocations</div>
            <div class="text-2xl font-bold text-white">${counts.active}</div>
          </div>
          <div class="glass-card p-5 border-amber-500/30">
            <div class="text-sm text-amber-400 font-medium mb-1">Overdue Returns</div>
            <div class="text-2xl font-bold text-white">${counts.overdue}</div>
          </div>
          <div class="glass-card p-5">
            <div class="text-sm text-slate-400 font-medium mb-1">Loaded Records</div>
            <div class="text-2xl font-bold text-white">${allocations.length}</div>
          </div>
        </div>
        
        <div class="glass-panel overflow-hidden">
          <div class="p-4 border-b border-slate-700/50 flex gap-4">
            <div class="relative flex-1 max-w-md">
              <i data-lucide="search" class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"></i>
              <input type="text" placeholder="Search employee or asset..." class="w-full bg-slate-800/50 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500 transition-all" />
            </div>
          </div>
          
          <div class="p-4 grid gap-4">${allocationsHtml}</div>
        </div>
      </div>

      <div id="modal-allocate-asset" class="fixed inset-0 z-50 hidden items-center justify-center">
        <div class="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" id="modal-overlay"></div>
        <div class="glass-panel w-full max-w-lg p-6 relative z-10">
          <div class="flex items-center justify-between mb-6 border-b border-slate-700/50 pb-4">
            <h2 class="text-xl font-bold font-outfit text-white">Allocate Asset</h2>
            <button id="btn-close-modal" class="text-slate-400 hover:text-white transition-colors">
              <i data-lucide="x" class="w-5 h-5"></i>
            </button>
          </div>
          <form id="form-allocate-asset" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-slate-300 mb-1">Asset ID</label>
              <input type="text" id="allocation-asset-id" class="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 text-white" required>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-300 mb-1">Employee ID</label>
              <input type="text" id="allocation-employee-id" class="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 text-white" required>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-300 mb-1">Employee Name</label>
              <input type="text" id="allocation-employee-name" class="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 text-white">
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-300 mb-1">Notes</label>
              <textarea id="allocation-notes" class="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 text-white" rows="3"></textarea>
            </div>
            <div class="pt-4 flex justify-end gap-3 mt-6 border-t border-slate-700/50">
              <button type="button" id="btn-cancel-modal" class="px-4 py-2 rounded-lg text-sm font-medium text-slate-300 hover:bg-slate-800 transition-colors">Cancel</button>
              <button type="submit" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">Save Allocation</button>
            </div>
          </form>
        </div>
      </div>
    `;
  } catch (error) {
    console.error('Failed to load allocations', error);
    return `
      <div class="animate-slide-in">
        <div class="glass-panel p-6 text-red-400">Unable to load allocations from the backend.</div>
      </div>
    `;
  }
}

window.init_allocations = () => {
  const modal = document.getElementById('modal-allocate-asset');
  const openButton = document.getElementById('btn-allocate-asset');
  const closeButtons = [document.getElementById('btn-close-modal'), document.getElementById('btn-cancel-modal')];
  const overlay = document.getElementById('modal-overlay');
  const form = document.getElementById('form-allocate-asset');

  const openModal = () => modal.classList.remove('hidden');
  const closeModal = () => modal.classList.add('hidden');

  if (openButton) openButton.addEventListener('click', openModal);
  closeButtons.filter(Boolean).forEach(button => button.addEventListener('click', closeModal));
  if (overlay) overlay.addEventListener('click', closeModal);

  if (form) {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const payload = {
        assetId: document.getElementById('allocation-asset-id').value,
        employeeId: document.getElementById('allocation-employee-id').value,
        employeeName: document.getElementById('allocation-employee-name').value,
        notes: document.getElementById('allocation-notes').value,
      };

      try {
        await api.post('/asset-allocations', payload);
        showToast('Allocation created successfully', 'success');
        closeModal();
        window.dispatchEvent(new Event('hashchange'));
      } catch (error) {
        showToast(error.message || 'Failed to create allocation', 'error');
      }
    });
  }
};
