// Alerts use shared notifications.js (showNotification/showAlert).

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
