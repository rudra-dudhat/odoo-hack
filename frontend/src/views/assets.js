import { api } from '../services/api.js';
import { showToast } from '../components/toast.js';

export async function renderAssets() {
  let assetsHtml = '';
  let count = 0;
  
  try {
    const response = await api.get('/assets');
    const assets = response.data || [];
    count = assets.length;
    
    if (count === 0) {
      assetsHtml = `
        <tr>
          <td colspan="5" class="px-6 py-8 text-center text-slate-400">
            No assets found in the database.
          </td>
        </tr>
      `;
    } else {
      assetsHtml = assets.map(asset => `
        <tr class="hover:bg-slate-800/30 transition-colors">
          <td class="px-6 py-4 text-slate-300 font-mono">${asset.id || asset.assetTag || 'Unknown'}</td>
          <td class="px-6 py-4 text-white font-medium">${asset.name || (asset.categorySnapshot ? asset.categorySnapshot.name : 'Unknown Asset')}</td>
          <td class="px-6 py-4 text-slate-400">${asset.categorySnapshot ? asset.categorySnapshot.name : (asset.categoryId || 'General')}</td>
          <td class="px-6 py-4">
            <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${asset.condition === 'good' || asset.condition === 'new' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'}">
              ${asset.status} (${asset.condition || 'Unknown'})
            </span>
          </td>
          <td class="px-6 py-4 text-right">
            <button class="text-slate-400 hover:text-blue-400 transition-colors p-1"><i data-lucide="eye" class="w-4 h-4"></i></button>
            <button class="text-slate-400 hover:text-white transition-colors p-1 ml-2"><i data-lucide="more-vertical" class="w-4 h-4"></i></button>
          </td>
        </tr>
      `).join('');
    }
  } catch (error) {
    console.error('Failed to load assets', error);
    assetsHtml = `
      <tr>
        <td colspan="5" class="px-6 py-8 text-center text-red-400">
          Error loading assets from the server. Is the backend running?
        </td>
      </tr>
    `;
  }

  return `
    <div class="animate-slide-in relative h-full flex flex-col">
      <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-outfit font-bold text-white">Assets</h1>
        <button id="btn-add-asset" class="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors flex items-center gap-2 shadow-lg shadow-blue-900/20 cursor-pointer">
          <i data-lucide="plus" class="w-4 h-4 pointer-events-none"></i>
          Add Asset
        </button>
      </div>
      
      <div class="glass-panel overflow-hidden flex-1 flex flex-col">
        <div class="p-4 border-b border-slate-700/50 flex gap-4">
          <div class="relative flex-1 max-w-md">
            <i data-lucide="search" class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"></i>
            <input type="text" placeholder="Search assets by name, tag, or serial..." class="w-full bg-slate-800/50 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500 transition-all" />
          </div>
        </div>
        
        <div class="overflow-x-auto flex-1">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-800/50 text-slate-400 text-xs uppercase tracking-wider border-b border-slate-700/50">
                <th class="px-6 py-4 font-medium">Asset ID</th>
                <th class="px-6 py-4 font-medium">Name</th>
                <th class="px-6 py-4 font-medium">Category</th>
                <th class="px-6 py-4 font-medium">Status (Condition)</th>
                <th class="px-6 py-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-700/50 text-sm">
              ${assetsHtml}
            </tbody>
          </table>
        </div>
        <div class="p-4 border-t border-slate-700/50 flex items-center justify-between text-sm text-slate-400">
          <span>Showing ${count} assets</span>
        </div>
      </div>
    </div>

    <!-- Add Asset Modal -->
    <div id="modal-add-asset" class="fixed inset-0 z-50 hidden items-center justify-center">
      <div class="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" id="modal-overlay"></div>
      
      <div class="glass-panel w-full max-w-lg p-6 relative z-10 animate-slide-in">
        <div class="flex items-center justify-between mb-6 border-b border-slate-700/50 pb-4">
          <h2 class="text-xl font-bold font-outfit text-white">Add New Asset</h2>
          <button id="btn-close-modal" class="text-slate-400 hover:text-white transition-colors">
            <i data-lucide="x" class="w-5 h-5"></i>
          </button>
        </div>
        
        <form id="form-add-asset" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-slate-300 mb-1">Asset Name <span class="text-red-400">*</span></label>
            <input type="text" id="asset-name" required class="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500" placeholder="e.g. MacBook Pro M3">
          </div>
          
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-slate-300 mb-1">Category <span class="text-red-400">*</span></label>
              <select id="asset-category" required class="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500">
                <option value="cat_laptops">Laptops</option>
                <option value="cat_monitors">Monitors</option>
                <option value="cat_furniture">Furniture</option>
                <option value="cat_general">General</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-300 mb-1">Condition <span class="text-red-400">*</span></label>
              <select id="asset-condition" required class="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500">
                <option value="new">New</option>
                <option value="good">Good</option>
                <option value="fair">Fair</option>
                <option value="poor">Poor</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-slate-300 mb-1">Serial Number</label>
              <input type="text" id="asset-serial" class="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500" placeholder="e.g. SN-88213X">
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-300 mb-1">Purchase Cost (USD)</label>
              <input type="number" id="asset-cost" min="0" class="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500" placeholder="0">
            </div>
          </div>
          
          <div class="pt-4 flex justify-end gap-3 mt-6 border-t border-slate-700/50">
            <button type="button" id="btn-cancel-modal" class="px-4 py-2 rounded-lg text-sm font-medium text-slate-300 hover:bg-slate-800 transition-colors">Cancel</button>
            <button type="submit" id="btn-submit-asset" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2">
              Save Asset
            </button>
          </div>
        </form>
      </div>
    </div>
  `;
}

// Attach event listeners after HTML is rendered
window.init_assets = () => {
  const modal = document.getElementById('modal-add-asset');
  const btnOpen = document.getElementById('btn-add-asset');
  const btnClose = document.getElementById('btn-close-modal');
  const btnCancel = document.getElementById('btn-cancel-modal');
  const overlay = document.getElementById('modal-overlay');
  const form = document.getElementById('form-add-asset');
  const btnSubmit = document.getElementById('btn-submit-asset');

  const openModal = () => {
    modal.classList.remove('hidden');
    modal.classList.add('flex');
  };

  const closeModal = () => {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    form.reset();
  };

  if(btnOpen) btnOpen.addEventListener('click', openModal);
  if(btnClose) btnClose.addEventListener('click', closeModal);
  if(btnCancel) btnCancel.addEventListener('click', closeModal);
  if(overlay) overlay.addEventListener('click', closeModal);

  if(form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const payload = {
        name: document.getElementById('asset-name').value,
        categoryId: document.getElementById('asset-category').value,
        categoryName: document.getElementById('asset-category').options[document.getElementById('asset-category').selectedIndex].text,
        condition: document.getElementById('asset-condition').value,
        serialNumber: document.getElementById('asset-serial').value,
        purchaseCost: document.getElementById('asset-cost').value || 0
      };

      btnSubmit.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> Saving...`;
      btnSubmit.disabled = true;

      try {
        await api.post('/assets', payload);
        showToast('Asset successfully created!', 'success');
        closeModal();
        
        // Refresh the page to show new asset
        window.dispatchEvent(new Event('hashchange'));
      } catch (error) {
        showToast(error.message || 'Failed to create asset', 'error');
        btnSubmit.innerHTML = `Save Asset`;
        btnSubmit.disabled = false;
        lucide.createIcons();
      }
    });
  }
};
