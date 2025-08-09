// Global Alert System
window.showAlert = function(title, message, type = 'success', duration = 5000) {
  const alertContainer = document.getElementById('alert-container');
  const alertTemplate = document.getElementById('alert-template');
  
  if (!alertContainer || !alertTemplate) return;
  
  // Clone the template
  const alertElement = alertTemplate.content.cloneNode(true);
  const alertBox = alertElement.querySelector('.alert-box');
  
  // Set the content
  alertElement.querySelector('.alert-title').textContent = title;
  alertElement.querySelector('.alert-message').innerHTML = message;
  
  // Set the appropriate icon and colors based on type
  const iconContainer = alertElement.querySelector('.alert-icon');
  let borderColor, iconHtml;
  
  switch(type) {
    case 'success':
      borderColor = 'border-green-500';
      iconHtml = `<svg class="h-6 w-6 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>`;
      break;
    case 'error':
      borderColor = 'border-red-500';
      iconHtml = `<svg class="h-6 w-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>`;
      break;
    case 'warning':
      borderColor = 'border-yellow-500';
      iconHtml = `<svg class="h-6 w-6 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
      </svg>`;
      break;
    case 'info':
    default:
      borderColor = 'border-blue-500';
      iconHtml = `<svg class="h-6 w-6 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>`;
  }
  
  // Apply styling
  alertBox.classList.add(borderColor);
  iconContainer.innerHTML = iconHtml;
  
  // Add to container
  const alertDiv = document.createElement('div');
  alertDiv.appendChild(alertElement);
  alertContainer.appendChild(alertDiv);
  
  // Initialize Alpine component
  if (window.Alpine) {
    Alpine.initTree(alertDiv);
  }
  
  // Auto-remove after duration
  if (duration > 0) {
    setTimeout(() => {
      alertDiv.remove();
    }, duration);
  }
};

document.addEventListener('DOMContentLoaded', function() {
  const sidebarHeader = document.getElementById('sidebar-header');
  const sidebar = document.querySelector('aside');
  const sidebarElementsToHide = sidebar ? sidebar.querySelectorAll('.logo-text, nav span') : [];
  const toggleIcon = document.getElementById('toggle-icon');

  function toggleSidebar() {
    if (!sidebar) return;
    sidebar.classList.toggle('w-64');
    sidebar.classList.toggle('w-20');
    sidebarElementsToHide.forEach(el => {
      el.classList.toggle('opacity-0');
      el.classList.toggle('max-w-0');
      el.classList.toggle('invisible');
    });
    if (toggleIcon) toggleIcon.classList.toggle('rotate-180');
  }

  if (sidebarHeader) sidebarHeader.addEventListener('click', toggleSidebar);
});