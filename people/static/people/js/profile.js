// Profile Page JavaScript
document.addEventListener('DOMContentLoaded', function() {
  console.log('Profile script loaded');
  
  // Load projects on page load
  loadProjects();
  
  // Set up search functionality
  const searchInput = document.getElementById('project-search');
  if (searchInput) {
    searchInput.addEventListener('input', debounce(handleSearch, 300));
  }
  
  // Set up account edit form
  const accountEditForm = document.getElementById('accountEditForm');
  if (accountEditForm) {
    accountEditForm.addEventListener('submit', handleAccountUpdate);
  }

  // Inline account edit controls (if present)
  const accountCard = document.getElementById('account-card');
  if (accountCard) {
    // Ensure initial state is view mode
    toggleAccountEdit(false);
  }
});

// Debounce function for search
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Account Information Functions
function editAccountInfo() {
  const modal = document.getElementById('accountEditModal');
  modal.classList.remove('hidden');
}

function closeAccountEditModal() {
  const modal = document.getElementById('accountEditModal');
  modal.classList.add('hidden');
}

function handleAccountUpdate(event) {
  event.preventDefault();
  
  const formData = new FormData(event.target);
  const data = Object.fromEntries(formData.entries());
  
  // Update display immediately for better UX
  document.getElementById('display-first-name').textContent = data.first_name || '-';
  document.getElementById('display-last-name').textContent = data.last_name || '-';
  document.getElementById('display-email').textContent = data.email;
  document.getElementById('display-phone').textContent = data.phone || 'Not provided';
  document.getElementById('display-timezone').textContent = data.timezone;
  
  // Send to server
  const csrftoken = getCookie('csrftoken');
  fetch('/api/profile/update/', {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrftoken,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  })
  .then(response => response.json())
  .then(data => {
    if (data.ok) {
      showNotification('Success', 'Profile updated successfully', 'success');
      closeAccountEditModal();
    } else {
      showNotification('Error', data.error || 'Failed to update profile', 'error');
    }
  })
  .catch(error => {
    console.error('Error updating profile:', error);
    showNotification('Error', 'Failed to update profile', 'error');
  });
}

// Inline edit toggle
function toggleAccountEdit(force) {
  const card = document.getElementById('account-card');
  if (!card) return;
  const next = typeof force === 'boolean' ? force : !card.classList.contains('is-editing');
  card.classList.toggle('is-editing', next);
  card.querySelectorAll('.js-view').forEach(el => el.classList.toggle('hidden', next));
  card.querySelectorAll('.js-edit').forEach(el => el.classList.toggle('hidden', !next));
}

// Save inline without modal
function saveAccountInline() {
  const data = {
    first_name: document.getElementById('input-first-name')?.value || '',
    last_name: document.getElementById('input-last-name')?.value || '',
    email: document.getElementById('input-email')?.value || '',
    timezone: document.getElementById('input-timezone')?.value || ''
  };
  // include phone in payload
  data.phone = document.getElementById('input-phone')?.value || '';

  // Optimistic UI update
  document.getElementById('display-first-name').textContent = data.first_name || '-';
  document.getElementById('display-last-name').textContent = data.last_name || '-';
  document.getElementById('display-email').textContent = data.email || '';
  const phone = data.phone || 'Not provided';
  document.getElementById('display-phone').textContent = phone;
  const tz = document.getElementById('input-timezone')?.value || 'UTC (GMT+0)';
  document.getElementById('display-timezone').textContent = tz;

  const csrftoken = getCookie('csrftoken');
  fetch('/api/profile/update/', {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrftoken,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  })
  .then(r => r.json())
  .then(res => {
    if (res.ok) {
      showNotification('Success', 'Profile updated successfully', 'success');
      toggleAccountEdit(false);
    } else {
      showNotification('Error', res.error || 'Failed to update profile', 'error');
    }
  })
  .catch(err => {
    console.error('Inline profile update error', err);
    showNotification('Error', 'Failed to update profile', 'error');
  });
}

// timezone selection is handled by the Alpine dropdown component globally

// Project Management Functions
function loadProjects() {
  const projectsList = document.getElementById('projects-list');
  
  fetch('/api/profile/projects/', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'same-origin'
  })
  .then(response => response.json())
  .then(data => {
    if (data.ok) {
      renderProjects(data.projects);
    } else {
      projectsList.innerHTML = `
        <div class="flex items-center justify-center py-8">
          <div class="text-center">
            <svg class="mx-auto h-12 w-12 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            <p class="mt-2 text-sm text-red-500">${data.error || 'Failed to load projects'}</p>
          </div>
        </div>
      `;
    }
  })
  .catch(error => {
    console.error('Error loading projects:', error);
    projectsList.innerHTML = `
      <div class="flex items-center justify-center py-8">
        <div class="text-center">
          <svg class="mx-auto h-12 w-12 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          <p class="mt-2 text-sm text-red-500">Failed to load projects</p>
        </div>
      </div>
    `;
  });
}

function renderProjects(projects) {
  const projectsList = document.getElementById('projects-list');
  
  if (projects.length === 0) {
    projectsList.innerHTML = `
      <div class="flex items-center justify-center py-8">
        <div class="text-center">
          <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
          </svg>
          <h3 class="mt-2 text-sm font-medium text-gray-900">No projects</h3>
          <p class="mt-1 text-sm text-gray-500">Get started by creating your first project.</p>
          <div class="mt-6">
            <button onclick="createNewProject()" class="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors">
              <svg class="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
              </svg>
              Create Project
            </button>
          </div>
        </div>
      </div>
    `;
    return;
  }
  
  const projectsHTML = projects.map(project => `
    <div class="border border-gray-200 rounded-lg overflow-hidden project-card" data-project-id="${project.id}">
      <!-- Project Header -->
      <div class="px-4 py-3 bg-gray-50 border-b border-gray-200">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <button onclick="toggleProject('${project.id}')" class="text-gray-400 hover:text-gray-600">
              <svg class="w-4 h-4 project-toggle" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
              </svg>
            </button>
            <div>
              <h3 class="font-medium text-gray-900">${project.name}</h3>
              ${project.description ? `<p class="text-sm text-gray-500">${project.description}</p>` : ''}
            </div>
            ${project.is_active ? '<span class="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">Active</span>' : ''}
          </div>
          <div class="flex items-center space-x-2">
            <span class="text-sm text-gray-500">${project.dataset_count} datasets</span>
            <div class="relative">
              <button onclick="showProjectMenu('${project.id}', event)" class="p-1 text-gray-400 hover:text-gray-600">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"></path>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Project Datasets (Collapsible) -->
      <div class="project-datasets hidden" id="datasets-${project.id}">
        <div class="p-4">
          ${project.datasets && project.datasets.length > 0 ? renderDatasets(project.datasets, project.id) : 
            `<div class="text-center py-4">
              <p class="text-sm text-gray-500">No datasets in this project</p>
              <button onclick="uploadToProject('${project.id}')" class="mt-2 px-3 py-1 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors">
                Upload Dataset
              </button>
            </div>`
          }
        </div>
      </div>
    </div>
  `).join('');
  
  projectsList.innerHTML = projectsHTML;
}

function renderDatasets(datasets, projectId) {
  return `
    <div class="space-y-2">
      <div class="flex items-center justify-between">
        <h4 class="text-sm font-medium text-gray-700">Datasets</h4>
        <button onclick="uploadToProject('${projectId}')" class="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded hover:bg-blue-200 transition-colors">
          <svg class="w-3 h-3 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
          </svg>
          Upload
        </button>
      </div>
      <div class="grid grid-cols-1 gap-2">
        ${datasets.map(dataset => `
          <div class="flex items-center justify-between p-2 bg-gray-50 rounded dataset-item" data-dataset-id="${dataset.id}">
            <div class="flex items-center space-x-3">
              <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V7a2 2 0 012-2h10a2 2 0 012 2v8a2 2 0 01-2 2z"></path>
              </svg>
              <div>
                <p class="text-sm font-medium text-gray-900">${dataset.name}</p>
                <p class="text-xs text-gray-500">${dataset.created_at} • ${dataset.row_count} rows</p>
              </div>
            </div>
            <div class="flex items-center space-x-1">
              <button onclick="previewDataset('${dataset.id}')" class="p-1 text-blue-600 hover:text-blue-800" title="Preview">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                </svg>
              </button>
              <button onclick="downloadDataset('${dataset.id}')" class="p-1 text-green-600 hover:text-green-800" title="Download">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
              </button>
              <button onclick="shareDataset('${dataset.id}')" class="p-1 text-purple-600 hover:text-purple-800" title="Share">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z"></path>
                </svg>
              </button>
              <button onclick="confirmDeleteDataset('${dataset.id}', '${dataset.name}', '${projectId}')" class="p-1 text-red-600 hover:text-red-800" title="Delete">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                </svg>
              </button>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

// Project interaction functions
function toggleProject(projectId) {
  const datasetsDiv = document.getElementById(`datasets-${projectId}`);
  const toggleIcon = document.querySelector(`[onclick="toggleProject('${projectId}')"] svg`);
  
  if (datasetsDiv.classList.contains('hidden')) {
    datasetsDiv.classList.remove('hidden');
    toggleIcon.style.transform = 'rotate(90deg)';
  } else {
    datasetsDiv.classList.add('hidden');
    toggleIcon.style.transform = 'rotate(0deg)';
  }
}

function createNewProject() {
  // Use modal instead of prompt
  showConfirmModal('Enter project name:', (projectName) => {
    if (!projectName.trim()) {
      showNotification('Error', 'Project name is required', 'error');
      return;
    }
    
    showConfirmModal('Enter project description (optional):', (projectDescription) => {
      createProjectWithDetails(projectName.trim(), projectDescription.trim() || '');
    }, null, { allowEmpty: true });
  });
}

function createProjectWithDetails(projectName, projectDescription) {
  
  const csrftoken = getCookie('csrftoken');
  fetch('/api/projects/create/', {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrftoken,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      name: projectName,
      description: projectDescription,
      visibility: 'private'
    })
  })
  .then(response => response.json())
  .then(data => {
    if (data.ok) {
      showNotification('Success', `Project "${projectName}" created successfully`, 'success');
      loadProjects(); // Reload projects list
    } else {
      showNotification('Error', data.error || 'Failed to create project', 'error');
    }
  })
  .catch(error => {
    console.error('Error creating project:', error);
    showNotification('Error', 'Failed to create project', 'error');
  });
}

function showProjectMenu(projectId, event) {
  // Simple context menu using confirm modals
  showConfirmModal('Select action:\n1. Rename Project\n2. Archive Project\n3. Delete Project\n\nEnter number (1-3):', (action) => {
    switch(action) {
      case '1':
        renameProject(projectId);
        break;
      case '2':
        archiveProject(projectId);
        break;
      case '3':
        confirmDeleteProject(projectId);
        break;
      default:
        showNotification('Info', 'Invalid selection', 'info');
        return;
    }
  });
}

function renameProject(projectId) {
  showConfirmModal('Enter new project name:', (newName) => {
    if (!newName.trim()) {
      showNotification('Error', 'Project name is required', 'error');
      return;
    }
    
    updateProjectName(projectId, newName.trim());
  });
}

function updateProjectName(projectId, newName) {
  
  const csrftoken = getCookie('csrftoken');
  fetch(`/api/projects/${projectId}/update/`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrftoken,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ name: newName })
  })
  .then(response => response.json())
  .then(data => {
    if (data.ok) {
      showNotification('Success', 'Project renamed successfully', 'success');
      loadProjects();
    } else {
      showNotification('Error', data.error || 'Failed to rename project', 'error');
    }
  })
  .catch(error => {
    console.error('Error renaming project:', error);
    showNotification('Error', 'Failed to rename project', 'error');
  });
}

function archiveProject(projectId) {
  showNotification('Info', 'Archive functionality coming soon', 'info');
}

function confirmDeleteProject(projectId) {
  showConfirmModal(
    'Are you sure you want to delete this project? This will also delete all datasets in the project. This action cannot be undone.',
    () => { deleteProject(projectId); },
    null,
    { dangerous: true }
  );
}

function deleteProject(projectId) {
  const csrftoken = getCookie('csrftoken');
  fetch(`/api/projects/${projectId}/delete/`, {
    method: 'DELETE',
    headers: {
      'X-CSRFToken': csrftoken
    }
  })
  .then(response => response.json())
  .then(data => {
    if (data.ok) {
      showNotification('Success', 'Project deleted successfully', 'success');
      loadProjects();
    } else {
      showNotification('Error', data.error || 'Failed to delete project', 'error');
    }
  })
  .catch(error => {
    console.error('Error deleting project:', error);
    showNotification('Error', 'Failed to delete project', 'error');
  });
}

// Dataset functions
function uploadToProject(projectId) {
  showNotification('Info', 'Upload functionality coming soon', 'info');
}

function previewDataset(datasetId) {
  window.open(`/analysis/dataset/${datasetId}/`, '_blank');
}

function downloadDataset(datasetId) {
  window.location.href = `/api/datasets/${datasetId}/download/`;
}

function shareDataset(datasetId) {
  showNotification('Info', 'Share functionality coming soon', 'info');
}

function confirmDeleteDataset(datasetId, datasetName, projectId) {
  showConfirmModal(
    `Are you sure you want to delete dataset "${datasetName}"? This action cannot be undone.`,
    () => { deleteDataset(datasetId, projectId); },
    null,
    { dangerous: true }
  );
}

function deleteDataset(datasetId, projectId) {
  const csrftoken = getCookie('csrftoken');
  fetch(`/api/datasets/${datasetId}/`, {
    method: 'DELETE',
    headers: {
      'X-CSRFToken': csrftoken
    }
  })
  .then(response => response.json())
  .then(data => {
    if (data.ok) {
      showNotification('Success', 'Dataset deleted successfully', 'success');
      loadProjects(); // Reload to update counts
    } else {
      showNotification('Error', data.error || 'Failed to delete dataset', 'error');
    }
  })
  .catch(error => {
    console.error('Error deleting dataset:', error);
    showNotification('Error', 'Failed to delete dataset', 'error');
  });
}

// Search functionality
function handleSearch(event) {
  const searchTerm = event.target.value.toLowerCase();
  const projectCards = document.querySelectorAll('.project-card');
  
  projectCards.forEach(card => {
    const projectName = card.querySelector('h3').textContent.toLowerCase();
    const projectDescription = card.querySelector('p') ? card.querySelector('p').textContent.toLowerCase() : '';
    const datasetItems = card.querySelectorAll('.dataset-item');
    
    let hasMatchingDataset = false;
    datasetItems.forEach(item => {
      const datasetName = item.querySelector('.text-sm.font-medium').textContent.toLowerCase();
      const matches = datasetName.includes(searchTerm);
      item.style.display = matches || searchTerm === '' ? 'flex' : 'none';
      if (matches) hasMatchingDataset = true;
    });
    
    const projectMatches = projectName.includes(searchTerm) || projectDescription.includes(searchTerm);
    card.style.display = (projectMatches || hasMatchingDataset || searchTerm === '') ? 'block' : 'none';
  });
}

// Security functions
function changePassword() {
  showNotification('Info', 'Password change functionality coming soon', 'info');
}

function downloadAccountData() {
  showNotification('Info', 'Data export functionality coming soon', 'info');
}

function confirmLogout() {
  showConfirmModal(
    'Are you sure you want to logout?',
    () => { window.location.href = '/logout/'; }
  );
}

function confirmDeleteAccount() {
  showConfirmModal(
    'Type "DELETE" to confirm account deletion:',
    (confirmation) => {
      if (confirmation === 'DELETE') {
        showNotification('Info', 'Account deletion functionality coming soon', 'info');
      } else {
        showNotification('Error', 'Confirmation text must be exactly "DELETE"', 'error');
      }
    },
    null,
    { dangerous: true }
  );
}

// Utility functions
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Notification and Modal Functions (from dashboard.js)
function showNotification(title, message, type = 'info') {
  const notificationId = 'notification-' + Date.now();
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
  notification.className = `fixed top-4 right-4 max-w-sm w-full ${colorMap[type] || colorMap.info} border rounded-lg p-4 shadow-lg z-50 transform transition-all duration-300 translate-x-full`;
  
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
        <button onclick="document.getElementById('${notificationId}').remove()" class="inline-flex text-gray-400 hover:text-gray-600">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>
    </div>
  `;
  
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.style.transform = 'translateX(0)';
  }, 100);
  
  setTimeout(() => {
    if (document.getElementById(notificationId)) {
      notification.style.transform = 'translateX(full)';
      setTimeout(() => notification.remove(), 300);
    }
  }, 5000);
}

function showConfirmModal(message, onConfirm, onCancel = null, options = {}) {
  const modalId = 'confirm-modal-' + Date.now();
  const isPrompt = !message.includes('?') && !message.includes('sure');
  const isDangerous = options.dangerous || false;
  const allowEmpty = options.allowEmpty || false;
  
  const modal = document.createElement('div');
  modal.id = modalId;
  modal.className = 'fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50';
  
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
  
  window.closeConfirmModal = function(modalId, confirmed) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    
    if (confirmed) {
      const input = document.getElementById(modalId + '-input');
      const value = input ? input.value : null;
      
      if (isPrompt && !allowEmpty && (!value || !value.trim())) {
        showNotification('Error', 'Please enter a value', 'error');
        return;
      }
      
      modal.remove();
      if (onConfirm) {
        onConfirm(isPrompt ? value : true);
      }
    } else {
      modal.remove();
      if (onCancel) {
        onCancel();
      }
    }
    
    delete window.closeConfirmModal;
  };
  
  if (isPrompt) {
    const input = document.getElementById(modalId + '-input');
    if (input) {
      input.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
          window.closeConfirmModal(modalId, true);
        }
      });
      input.focus();
    }
  }
}
