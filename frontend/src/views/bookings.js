import { api } from '../services/api.js';
import { showToast } from '../components/toast.js';

export async function renderBookings() {
  let bookingsHtml = '';
  try {
    const response = await api.get('/resource-bookings');
    const bookings = response.data || [];

    if (bookings.length === 0) {
      bookingsHtml = `
        <div class="p-8 text-center text-slate-400">
          <i data-lucide="calendar-clock" class="w-12 h-12 mx-auto mb-4 opacity-50"></i>
          <p>No bookings have been created yet.</p>
        </div>
      `;
    } else {
      bookingsHtml = bookings.map(booking => `
        <div class="border border-slate-700/50 rounded-lg p-4 bg-slate-800/40">
          <div class="flex items-center justify-between mb-2">
            <div class="font-medium text-white">${booking.resourceName || booking.resourceId}</div>
            <span class="px-2 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400">${booking.status}</span>
          </div>
          <div class="text-sm text-slate-400">Booked by ${booking.bookedByName || booking.bookedBy}</div>
          <div class="text-xs text-slate-500 mt-2">${booking.startTime || '—'} → ${booking.endTime || '—'}</div>
        </div>
      `).join('');
    }

    return `
      <div class="animate-slide-in">
        <div class="flex items-center justify-between mb-6">
          <h1 class="text-2xl font-outfit font-bold text-white">Shared Resource Bookings</h1>
          <button id="btn-new-booking" class="bg-purple-600 hover:bg-purple-700 text-white font-medium py-2 px-4 rounded-lg transition-colors flex items-center gap-2 shadow-lg shadow-purple-900/20">
            <i data-lucide="calendar-plus" class="w-4 h-4"></i>
            New Booking
          </button>
        </div>
        
        <div class="glass-panel p-6">
          <div class="grid gap-4">${bookingsHtml}</div>
        </div>
      </div>

      <div id="modal-new-booking" class="fixed inset-0 z-50 hidden items-center justify-center">
        <div class="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" id="modal-overlay"></div>
        <div class="glass-panel w-full max-w-lg p-6 relative z-10">
          <div class="flex items-center justify-between mb-6 border-b border-slate-700/50 pb-4">
            <h2 class="text-xl font-bold font-outfit text-white">Create Booking</h2>
            <button id="btn-close-modal" class="text-slate-400 hover:text-white transition-colors">
              <i data-lucide="x" class="w-5 h-5"></i>
            </button>
          </div>
          <form id="form-new-booking" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-slate-300 mb-1">Resource Name</label>
              <input type="text" id="booking-resource-name" class="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 text-white" required>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-300 mb-1">Booked By</label>
              <input type="text" id="booking-booked-by" class="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 text-white" required>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-slate-300 mb-1">Start Time</label>
                <input type="datetime-local" id="booking-start" class="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 text-white" required>
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-300 mb-1">End Time</label>
                <input type="datetime-local" id="booking-end" class="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 text-white" required>
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-300 mb-1">Notes</label>
              <textarea id="booking-notes" class="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 text-white" rows="3"></textarea>
            </div>
            <div class="pt-4 flex justify-end gap-3 mt-6 border-t border-slate-700/50">
              <button type="button" id="btn-cancel-modal" class="px-4 py-2 rounded-lg text-sm font-medium text-slate-300 hover:bg-slate-800 transition-colors">Cancel</button>
              <button type="submit" class="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">Save Booking</button>
            </div>
          </form>
        </div>
      </div>
    `;
  } catch (error) {
    console.error('Failed to load bookings', error);
    return `
      <div class="animate-slide-in">
        <div class="glass-panel p-6 text-red-400">Unable to load bookings from the backend.</div>
      </div>
    `;
  }
}

window.init_bookings = () => {
  const modal = document.getElementById('modal-new-booking');
  const openButton = document.getElementById('btn-new-booking');
  const closeButtons = [document.getElementById('btn-close-modal'), document.getElementById('btn-cancel-modal')];
  const overlay = document.getElementById('modal-overlay');
  const form = document.getElementById('form-new-booking');

  const openModal = () => modal.classList.remove('hidden');
  const closeModal = () => modal.classList.add('hidden');

  if (openButton) openButton.addEventListener('click', openModal);
  closeButtons.filter(Boolean).forEach(button => button.addEventListener('click', closeModal));
  if (overlay) overlay.addEventListener('click', closeModal);

  if (form) {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const payload = {
        resourceName: document.getElementById('booking-resource-name').value,
        bookedByName: document.getElementById('booking-booked-by').value,
        startTime: document.getElementById('booking-start').value,
        endTime: document.getElementById('booking-end').value,
        notes: document.getElementById('booking-notes').value,
      };

      try {
        await api.post('/resource-bookings', payload);
        showToast('Booking created successfully', 'success');
        closeModal();
        window.dispatchEvent(new Event('hashchange'));
      } catch (error) {
        showToast(error.message || 'Failed to create booking', 'error');
      }
    });
  }
};
