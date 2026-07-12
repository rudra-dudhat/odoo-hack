import { api } from '../services/api.js';
import { showToast } from '../components/toast.js';

export async function renderMaintenance() {
  let requestsHtml = '';
  try {
    const response = await api.get('/maintenance-requests');
    const requests = response.data || [];

    if (requests.length === 0) {
      requestsHtml = `
        <div class="p-8 text-center text-slate-400">
          <i data-lucide="wrench" class="w-12 h-12 mx-auto mb-4 opacity-50"></i>
          <p>No maintenance requests have been created yet.</p>
        </div>
      `;
    } else {
      requestsHtml = requests.map(request => `
        <div class="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
          <div class="flex items-start justify-between mb-3">
            <span class="px-2 py-0.5 rounded text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">${request.priority || 'medium'}</span>
            <span class="text-xs text-slate-400">${request.status || 'pending'}</span>
          </div>
          <h3 class="font-medium text-white mb-1">${request.title || 'Maintenance Request'}</h3>
          <p class="text-sm text-slate-400 mb-4 line-clamp-2">${request.description || 'No additional notes provided.'}</p>
          <div class="flex items-center justify-between mt-auto">
            <div class="flex items-center gap-2 text-xs text-slate-400">
              <i data-lucide="box" class="w-3 h-3"></i> ${request.assetId || 'Unknown'}
            </div>
            <div class="text-xs text-slate-500">${request.createdAt ? new Date(request.createdAt).toLocaleDateString() : '—'}</div>
          </div>
        </div>
      `).join('');
    }

    return `
      <div class="animate-slide-in">
        <div class="flex items-center justify-between mb-6">
          <h1 class="text-2xl font-outfit font-bold text-white">Maintenance Logs</h1>
          <button id="btn-create-request" class="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors flex items-center gap-2 shadow-lg shadow-blue-900/20">
            <i data-lucide="plus" class="w-4 h-4"></i>
            Create Request
          </button>
        </div>

        <div class="glass-panel overflow-hidden mb-6">
          <div class="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">${requestsHtml}</div>
        </div>
      </div>

      <div id="modal-maintenance-request" class="fixed inset-0 z-50 hidden items-center justify-center">
        <div class="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" id="modal-overlay"></div>
        <div class="glass-panel w-full max-w-lg p-6 relative z-10">
          <div class="flex items-center justify-between mb-6 border-b border-slate-700/50 pb-4">
            <h2 class="text-xl font-bold font-outfit text-white">New Maintenance Request</h2>
            <button id="btn-close-modal" class="text-slate-400 hover:text-white transition-colors">
              <i data-lucide="x" class="w-5 h-5"></i>
            </button>
          </div>
          <form id="form-maintenance-request" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-slate-300 mb-1">Asset ID</label>
              <input type="text" id="maintenance-asset-id" class="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 text-white" required>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-300 mb-1">Title</label>
              <input type="text" id="maintenance-title" class="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 text-white" required>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-300 mb-1">Priority</label>
              <select id="maintenance-priority" class="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 text-white">
                <option value="high">High</option>
                <option value="medium" selected>Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-300 mb-1">Description</label>
              <textarea id="maintenance-description" class="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 text-white" rows="3"></textarea>
            </div>
            <div class="pt-4 flex justify-end gap-3 mt-6 border-t border-slate-700/50">
              <button type="button" id="btn-cancel-modal" class="px-4 py-2 rounded-lg text-sm font-medium text-slate-300 hover:bg-slate-800 transition-colors">Cancel</button>
              <button type="submit" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">Save Request</button>
            </div>
          </form>
        </div>
      </div>
    `;
  } catch (error) {
    console.error('Failed to load maintenance requests', error);
    return `
      <div class="animate-slide-in">
        <div class="glass-panel p-6 text-red-400">Unable to load maintenance requests from the backend.</div>
      </div>
    `;
  }
}

window.init_maintenance = () => {
  const modal = document.getElementById('modal-maintenance-request');
  const openButton = document.getElementById('btn-create-request');
  const closeButtons = [document.getElementById('btn-close-modal'), document.getElementById('btn-cancel-modal')];
  const overlay = document.getElementById('modal-overlay');
  const form = document.getElementById('form-maintenance-request');

  const openModal = () => modal.classList.remove('hidden');
  const closeModal = () => modal.classList.add('hidden');

  if (openButton) openButton.addEventListener('click', openModal);
  closeButtons.filter(Boolean).forEach(button => button.addEventListener('click', closeModal));
  if (overlay) overlay.addEventListener('click', closeModal);

  if (form) {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const payload = {
        assetId: document.getElementById('maintenance-asset-id').value,
        title: document.getElementById('maintenance-title').value,
        priority: document.getElementById('maintenance-priority').value,
        description: document.getElementById('maintenance-description').value,
      };

      try {
        await api.post('/maintenance-requests', payload);
        showToast('Maintenance request created successfully', 'success');
        closeModal();
        window.dispatchEvent(new Event('hashchange'));
      } catch (error) {
        showToast(error.message || 'Failed to create maintenance request', 'error');
      }
    });
  }
};
