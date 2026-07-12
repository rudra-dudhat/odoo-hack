import { auth } from '../services/auth.js';

export function renderHeader() {
  const user = auth.getUser();
  const userName = user ? user.name : 'Guest';
  const role = user ? user.role : 'User';

  // Attach global logout handler if not already attached
  window.handleLogout = () => {
    auth.signOut();
  };

  return `
    <header class="h-16 flex items-center justify-between px-6 border-b border-slate-700/50 glass z-10">
      <div class="flex items-center gap-4">
        <button class="text-slate-400 hover:text-white lg:hidden">
          <i data-lucide="menu" class="w-6 h-6"></i>
        </button>
        <div class="relative hidden sm:block">
          <i data-lucide="search" class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"></i>
          <input type="text" placeholder="Search anything..." class="bg-slate-800/50 border border-slate-700 rounded-full pl-10 pr-4 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500 w-64 transition-all focus:w-80" />
        </div>
      </div>
      
      <div class="flex items-center gap-4">
        <button class="relative p-2 text-slate-400 hover:text-white transition-colors rounded-full hover:bg-slate-800">
          <i data-lucide="bell" class="w-5 h-5"></i>
          <span class="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border border-slate-900"></span>
        </button>
        
        <div class="h-8 w-px bg-slate-700 mx-2"></div>
        
        <div class="flex items-center gap-3">
          <div class="text-right hidden sm:block">
            <div class="text-sm font-medium text-white leading-none mb-1">${userName}</div>
            <div class="text-xs text-slate-400 leading-none capitalize">${role}</div>
          </div>
          <div class="relative group cursor-pointer">
            <div class="w-9 h-9 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white font-bold text-sm shadow-md">
              ${userName.charAt(0)}
            </div>
            
            <div class="absolute right-0 mt-2 w-48 bg-slate-800 border border-slate-700 rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50 transform origin-top-right scale-95 group-hover:scale-100">
              <div class="py-1">
                <a href="#/profile" class="block px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 hover:text-white">Profile Settings</a>
                <button onclick="handleLogout()" class="w-full text-left block px-4 py-2 text-sm text-red-400 hover:bg-slate-700 hover:text-red-300">Sign out</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>
  `;
}
