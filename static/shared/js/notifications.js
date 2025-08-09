/**
 * Notification System - Shared across all pages
 * Provides toast notifications and modal confirmations
 */

// Notification System
function showNotification(title, message, type = 'info') {
  const container = document.getElementById('alert-container');
  if (!container) return;
  
  const notificationId = 'notification-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
  
  const iconMap = {
    'success': '<svg class="w-5 h-5 text-green-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>',
    'error': '<svg class="w-5 h-5 text-red-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>',
    'warning': '<svg class="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path></svg>',
    'info': '<svg class="w-5 h-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path></svg>'
  };
  
  const colorMap = {
    'success': 'bg-green-50 text-green-800 border-green-200',
    'error': 'bg-red-50 text-red-800 border-red-200',
    'warning': 'bg-yellow-50 text-yellow-800 border-yellow-200',
    'info': 'bg-blue-50 text-blue-800 border-blue-200'
  };
  
  const notification = document.createElement('div');
  notification.id = notificationId;
  notification.className = `max-w-sm w-full ${colorMap[type] || colorMap.info} border rounded-lg p-4 shadow-lg transform transition-all duration-300 translate-x-full mb-4`;
  
  notification.innerHTML = `
    <div class="flex items-start">
      <div class="flex-shrink-0">
        ${iconMap[type] || iconMap.info}
      </div>
      <div class="ml-3 flex-1">
        <h3 class="text-sm font-medium">${title}</h3>
        <p class="text-sm mt-1">${message}</p>
      </div>
      <div class="ml-4 flex-shrink-0">
        <button onclick="dismissNotification('${notificationId}')" class="inline-flex text-gray-400 hover:text-gray-600">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>
    </div>
  `;
  
  container.appendChild(notification);
  
  // Slide in
  setTimeout(() => {
    notification.style.transform = 'translateX(0)';
  }, 100);
  
  // Auto-dismiss after 5 seconds
  setTimeout(() => {
    dismissNotification(notificationId);
  }, 5000);
}

function dismissNotification(notificationId) {
  const notification = document.getElementById(notificationId);
  if (notification) {
    notification.style.transform = 'translateX(120%)';
    setTimeout(() => {
      notification.remove();
    }, 300);
  }
}

// Backward compatibility - redirect showAlert to showNotification
function showAlert(title, message, type = 'info') {
  showNotification(title, message, type);
}

// Confirmation Modal System
function showConfirmModal(message, onConfirm, onCancel = null, options = {}) {
  const modal = document.createElement('div');
  modal.className = 'fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50';
  
  const modalId = 'confirm-modal-' + Date.now();
  modal.id = modalId;
  
  const isPrompt = !message.includes('?') && !message.includes('sure');
  const isDangerous = options.dangerous || false;
  const allowEmpty = options.allowEmpty || false;
  
  const inputField = isPrompt ? `
    <div class="mt-4">
      <input type="text" id="${modalId}-input" class="w-full px-3 py-2 border border-gray-300 rounded-md focus:border-blue-500 focus:outline-none" placeholder="Enter value..." autofocus>
    </div>
  ` : '';
  
  const confirmButtonClass = isDangerous 
    ? 'bg-red-600 hover:bg-red-700 text-white'
    : 'bg-blue-600 hover:bg-blue-700 text-white';
    
  modal.innerHTML = `
    <div class="relative top-20 mx-auto p-5 border w-11/12 max-w-md shadow-lg rounded-md bg-white">
      <div class="mt-3 text-center">
        <h3 class="text-lg font-medium text-gray-900 mb-4">${isPrompt ? 'Input Required' : 'Confirm Action'}</h3>
        <p class="text-sm text-gray-500 whitespace-pre-line">${message}</p>
        ${inputField}
        <div class="flex justify-center space-x-3 mt-6">
          <button onclick="closeConfirmModal('${modalId}', false)" class="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400 transition-colors">
            Cancel
          </button>
          <button onclick="closeConfirmModal('${modalId}', true)" class="px-4 py-2 ${confirmButtonClass} rounded-md transition-colors">
            ${isPrompt ? 'Submit' : (isDangerous ? 'Delete' : 'Confirm')}
          </button>
        </div>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  // Store callbacks for the modal
  window[`confirmCallback_${modalId}`] = onConfirm;
  window[`cancelCallback_${modalId}`] = onCancel;
  window[`isPrompt_${modalId}`] = isPrompt;
  window[`allowEmpty_${modalId}`] = allowEmpty;
  
  if (isPrompt) {
    const input = document.getElementById(modalId + '-input');
    if (input) {
      input.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
          closeConfirmModal(modalId, true);
        }
      });
      input.focus();
    }
  }
}

function closeConfirmModal(modalId, confirmed) {
  const modal = document.getElementById(modalId);
  if (!modal) return;
  
  const onConfirm = window[`confirmCallback_${modalId}`];
  const onCancel = window[`cancelCallback_${modalId}`];
  const isPrompt = window[`isPrompt_${modalId}`];
  const allowEmpty = window[`allowEmpty_${modalId}`];
  
  if (confirmed) {
    const input = document.getElementById(modalId + '-input');
    const value = input ? input.value : null;
    
    if (isPrompt && !allowEmpty && (!value || !value.trim())) {
      showNotification('Error', 'Please enter a value', 'error');
      return;
    }
    
    modal.remove();
    
    // Clean up global callbacks
    delete window[`confirmCallback_${modalId}`];
    delete window[`cancelCallback_${modalId}`];
    delete window[`isPrompt_${modalId}`];
    delete window[`allowEmpty_${modalId}`];
    
    if (onConfirm) {
      onConfirm(isPrompt ? value : true);
    }
  } else {
    modal.remove();
    
    // Clean up global callbacks
    delete window[`confirmCallback_${modalId}`];
    delete window[`cancelCallback_${modalId}`];
    delete window[`isPrompt_${modalId}`];
    delete window[`allowEmpty_${modalId}`];
    
    if (onCancel) {
      onCancel();
    }
  }
}

// Export for module systems if available
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { showNotification, showAlert, showConfirmModal, dismissNotification };
}