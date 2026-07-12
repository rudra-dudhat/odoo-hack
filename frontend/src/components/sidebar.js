export function renderSidebar() {
  const currentHash = window.location.hash || '#/dashboard';
  
  const navItems = [
    { name: 'Dashboard', hash: '#/dashboard', icon: 'layout-dashboard' },
    { name: 'Assets', hash: '#/assets', icon: 'monitor-smartphone' },
    { name: 'Allocations', hash: '#/allocations', icon: 'users' },
    { name: 'Bookings', hash: '#/bookings', icon: 'calendar' },
    { name: 'Maintenance', hash: '#/maintenance', icon: 'wrench' },
    { name: 'Audits', hash: '#/audits', icon: 'clipboard-check' },
  ];

  const renderNavItems = () => navItems.map(item => {
    const isActive = currentHash.startsWith(item.hash);
    return `
      <a href="${item.hash}" class="flex items-center gap-3 px-4 py-3 rounded-lg mb-1 transition-colors ${isActive ? 'bg-blue-600/20 text-blue-400' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'}">
        <i data-lucide="${item.icon}" class="w-5 h-5"></i>
        <span class="font-medium">${item.name}</span>
      </a>
    `;
  }).join('');

  return `
    <aside class="w-64 flex-shrink-0 glass-panel border-y-0 border-l-0 rounded-none h-full flex flex-col z-20">
      <div class="p-6 flex items-center gap-3 border-b border-slate-700/50">
        <div class="w-8 h-8 rounded-lg bg-blue-500 flex items-center justify-center text-white">
          <i data-lucide="box" class="w-5 h-5"></i>
        </div>
        <span class="font-outfit text-xl font-bold text-white tracking-wide">AssetTitan</span>
      </div>
      <nav class="flex-1 px-4 py-6 overflow-y-auto">
        <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4 px-4">Menu</div>
        ${renderNavItems()}
      </nav>
      <div class="p-4 border-t border-slate-700/50">
        <div class="bg-slate-800/50 rounded-lg p-4">
          <div class="text-sm text-slate-400 mb-2">Need help?</div>
          <button class="w-full bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium py-2 rounded transition-colors">
            Contact Support
          </button>
        </div>
      </div>
    </aside>
  `;
}
