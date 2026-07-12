import './style.css';
import { auth } from './services/auth.js';
import { renderSidebar } from './components/sidebar.js';
import { renderHeader } from './components/header.js';
import { showToast, ToastContainer } from './components/toast.js';

// Lazy loading views conceptually (using ESM imports)
import { renderDashboard } from './views/dashboard.js';
import { renderAssets } from './views/assets.js';
import { renderAllocations } from './views/allocations.js';
import { renderBookings } from './views/bookings.js';
import { renderMaintenance } from './views/maintenance.js';
import { renderAudits } from './views/audits.js';

const routes = {
  '#/dashboard': renderDashboard,
  '#/assets': renderAssets,
  '#/allocations': renderAllocations,
  '#/bookings': renderBookings,
  '#/maintenance': renderMaintenance,
  '#/audits': renderAudits,
};

function renderLogin() {
  const app = document.getElementById('app');
  app.innerHTML = `
    <div class="flex-1 flex items-center justify-center bg-slate-900">
      <div class="glass-panel p-8 w-full max-w-md animate-slide-in">
        <div class="text-center mb-8">
          <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-500/20 text-blue-400 mb-4">
            <i data-lucide="shield-check" class="w-8 h-8"></i>
          </div>
          <h1 class="text-3xl font-outfit font-bold text-white mb-2">AssetTitan</h1>
          <p class="text-slate-400">Sign in to your account</p>
        </div>
        <form id="loginForm" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-slate-300 mb-1">Email</label>
            <input type="email" id="email" class="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500" placeholder="admin@assettitan.local" value="admin@assettitan.local" required>
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-300 mb-1">Password</label>
            <input type="password" id="password" class="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500" placeholder="••••••••" value="password" required>
          </div>
          <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors mt-6">
            Sign In
          </button>
        </form>
      </div>
    </div>
    ${ToastContainer()}
  `;

  lucide.createIcons();

  document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    try {
      await auth.signIn(email, password);
      showToast('Successfully signed in', 'success');
      window.location.hash = '#/dashboard';
    } catch (err) {
      showToast('Login failed', 'error');
    }
  });
}

function renderAppLayout(contentHTML) {
  const app = document.getElementById('app');
  app.innerHTML = `
    ${renderSidebar()}
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden bg-slate-900/50">
      ${renderHeader()}
      <main class="flex-1 overflow-y-auto p-6 scroll-smooth" id="main-content">
        ${contentHTML}
      </main>
    </div>
    ${ToastContainer()}
  `;
  lucide.createIcons();
}

function router() {
  const hash = window.location.hash || '#/dashboard';

  if (!auth.isAuthenticated() && hash !== '#/login') {
    window.location.hash = '#/login';
    return;
  }

  if (hash === '#/login') {
    renderLogin();
    return;
  }

  const renderView = routes[hash];
  
  if (renderView) {
    // Pass a container to render into, or have the view return HTML
    // We'll have views return HTML string for simplicity, or we can mount.
    // Let's have views return a promise resolving to HTML string.
    Promise.resolve(renderView()).then(html => {
      renderAppLayout(html);
      
      // Allow views to attach event listeners after render
      if (typeof window[`init_${hash.replace('#/', '')}`] === 'function') {
        window[`init_${hash.replace('#/', '')}`]();
      }
    }).catch(err => {
      console.error(err);
      renderAppLayout('<div class="text-red-400 p-4">Error loading view</div>');
    });
  } else {
    // 404
    renderAppLayout(`
      <div class="flex flex-col items-center justify-center h-full text-center">
        <i data-lucide="file-question" class="w-16 h-16 text-slate-600 mb-4"></i>
        <h2 class="text-2xl font-bold font-outfit text-white mb-2">Page Not Found</h2>
        <p class="text-slate-400">The page you're looking for doesn't exist.</p>
      </div>
    `);
  }
}

// Initialize router
window.addEventListener('hashchange', router);
window.addEventListener('DOMContentLoaded', router);
