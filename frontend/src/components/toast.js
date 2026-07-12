export function ToastContainer() {
  return `<div id="toast-container" class="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none"></div>`;
}

export function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  const typeStyles = {
    success: 'bg-emerald-500/10 border-emerald-500/50 text-emerald-400',
    error: 'bg-red-500/10 border-red-500/50 text-red-400',
    warning: 'bg-amber-500/10 border-amber-500/50 text-amber-400',
    info: 'bg-blue-500/10 border-blue-500/50 text-blue-400',
  };

  const icons = {
    success: 'check-circle',
    error: 'alert-circle',
    warning: 'alert-triangle',
    info: 'info',
  };

  toast.className = `glass flex items-center gap-3 px-4 py-3 rounded-lg border shadow-lg transform transition-all duration-300 translate-y-4 opacity-0 pointer-events-auto ${typeStyles[type] || typeStyles.info}`;
  
  toast.innerHTML = `
    <i data-lucide="${icons[type] || icons.info}" class="w-5 h-5 flex-shrink-0"></i>
    <p class="text-sm font-medium text-white">${message}</p>
    <button class="ml-auto text-slate-400 hover:text-white focus:outline-none" onclick="this.parentElement.remove()">
      <i data-lucide="x" class="w-4 h-4"></i>
    </button>
  `;

  container.appendChild(toast);
  
  // Initialize icons for the new toast
  lucide.createIcons({ root: toast });

  // Animate in
  requestAnimationFrame(() => {
    toast.classList.remove('translate-y-4', 'opacity-0');
  });

  // Auto remove after 3s
  setTimeout(() => {
    toast.classList.add('opacity-0', 'scale-95');
    setTimeout(() => {
      toast.remove();
    }, 300);
  }, 3000);
}
