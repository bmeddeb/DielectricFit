document.addEventListener('DOMContentLoaded', function () {
  console.log('Dashboard script loaded');

  // Alert system is now available globally via window.showAlert from app.js

  // --- Upload Logic ---
  const uploadInput = document.getElementById('quick-upload');
  if (!uploadInput) return;
  const uploadLabel = uploadInput.parentElement;

  const handleFileSelect = (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.csv')) {
      showAlert('Invalid File', 'Please select a valid CSV file.', 'error');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    const csrftoken = getCookie('csrftoken');

    uploadLabel.innerHTML = `
      <svg class="w-8 h-8 mb-2 text-secondary animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <p class="text-sm text-secondary font-semibold">Processing...</p>
    `;

    fetch('/api/datasets/upload/', {
      method: 'POST',
      headers: { 'X-CSRFToken': csrftoken },
      body: formData,
    })
    .then(response => response.json())
    .then(data => {
      if (data.ok) {
        showAlert('Upload Successful', `Successfully uploaded: <strong>${data.summary.name}</strong><br>Rows: ${data.summary.row_count}`, 'success');
        resetUploadLabel();
        // Add the new dataset card immediately
        addDatasetCard(data.dataset);
        // Update the dataset count
        updateDatasetCount();
      } else {
        showAlert('Upload Failed', data.error, 'error');
        resetUploadLabel();
      }
    })
    .catch(error => {
      console.error('Error uploading file:', error);
      showAlert('Error', 'An unexpected error occurred during upload.', 'error');
      resetUploadLabel();
    });
  };

  uploadInput.addEventListener('change', (event) => {
    handleFileSelect(event.target.files[0]);
  });

  uploadLabel.addEventListener('dragover', (event) => {
    event.preventDefault();
    uploadLabel.classList.add('border-blue-500', 'bg-blue-50');
  });

  uploadLabel.addEventListener('dragleave', (event) => {
    event.preventDefault();
    uploadLabel.classList.remove('border-blue-500', 'bg-blue-50');
  });

  uploadLabel.addEventListener('drop', (event) => {
    event.preventDefault();
    uploadLabel.classList.remove('border-blue-500', 'bg-blue-50');
    handleFileSelect(event.dataTransfer.files[0]);
  });

  function resetUploadLabel() {
    uploadLabel.innerHTML = `
      <svg class="w-8 h-8 mb-2 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
      </svg>
      <p class="text-sm text-secondary font-semibold">Upload CSV</p>
      <p class="text-xs text-secondary">or drag & drop</p>
    `;
  }

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

  // Initialize placeholder charts
  const chartIds = ['dashChart1', 'dashChart2', 'dashChart3'];
  chartIds.forEach(id => {
    const ctx = document.getElementById(id);
    if (ctx) {
      new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: { 
          labels: Array.from({length: 50}, (_, i) => i),
          datasets: [{ 
            data: Array.from({length: 50}, () => Math.random() * 10 + 5),
            borderColor: 'rgb(59, 130, 246)',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            fill: true,
            tension: 0.4,
            pointRadius: 0
          }] 
        },
        options: { 
          responsive: true, 
          maintainAspectRatio: false, 
          plugins: { legend: { display: false } }, 
          scales: { 
            x: { grid: { display: false }, ticks: { display: false } }, 
            y: { grid: { color: '#e2e8f0' }, ticks: { display: false } } 
          } 
        }
      });
    }
  });

  // Initialize analysis charts
  document.querySelectorAll('[id^="chart-"]').forEach(canvas => {
    if (canvas && !canvas.chart) {
      canvas.chart = new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: {
          labels: Array.from({length: 50}, (_, i) => i),
          datasets: [{
            data: Array.from({length: 50}, () => Math.random() * 8 + 3),
            borderColor: 'rgb(16, 185, 129)',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            fill: true,
            tension: 0.4,
            pointRadius: 0
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { display: false }, ticks: { display: false } },
            y: { grid: { color: '#e2e8f0' }, ticks: { display: false } }
          }
        }
      });
    }
  });

  // Initialize dataset mini plots
  initializeDatasetPlots();
});

// Function to initialize mini plots for dataset cards
function initializeDatasetPlots() {
  document.querySelectorAll('[id^="dataset-plot-"]').forEach(canvas => {
    const datasetId = canvas.getAttribute('data-dataset-id');
    if (datasetId && !canvas.chart) {
      // Fetch data and create plot
      fetch(`/api/datasets/${datasetId}/data/`)
        .then(response => response.json())
        .then(data => {
          if (data.frequencies && data.frequencies.length > 0) {
            createDatasetPlot(canvas, data);
          } else {
            // Create placeholder if no data
            createPlaceholderPlot(canvas);
          }
        })
        .catch(error => {
          console.error('Error fetching dataset data:', error);
          createPlaceholderPlot(canvas);
        });
    }
  });
}

function createDatasetPlot(canvas, data) {
  const ctx = canvas.getContext('2d');
  
  // Create dual-axis plot for Dk and Df
  canvas.chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.frequencies,
      datasets: [
        {
          label: data.schema === 'DK_DF' ? 'Dk' : 'ε′',
          data: data.dk,
          borderColor: 'rgb(59, 130, 246)',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderWidth: 1.5,
          fill: false,
          tension: 0.4,
          pointRadius: 0,
          yAxisID: 'y'
        },
        {
          label: data.schema === 'DK_DF' ? 'Df' : 'ε″',
          data: data.df,
          borderColor: 'rgb(239, 68, 68)',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          borderWidth: 1.5,
          fill: false,
          tension: 0.4,
          pointRadius: 0,
          yAxisID: 'y1'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false }
      },
      scales: {
        x: {
          type: 'logarithmic',
          display: false
        },
        y: {
          type: 'linear',
          display: false,
          position: 'left',
        },
        y1: {
          type: 'linear',
          display: false,
          position: 'right',
          grid: {
            drawOnChartArea: false,
          },
        }
      }
    }
  });
}

function createPlaceholderPlot(canvas) {
  const ctx = canvas.getContext('2d');
  
  // Create a simple placeholder plot
  canvas.chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: Array.from({length: 20}, (_, i) => i),
      datasets: [{
        data: Array.from({length: 20}, () => Math.random() * 5 + 2),
        borderColor: 'rgb(200, 200, 200)',
        borderWidth: 1,
        fill: false,
        tension: 0.4,
        pointRadius: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false }
      },
      scales: {
        x: { display: false },
        y: { display: false }
      }
    }
  });
}

// Dataset interaction functions
function openDataset(datasetId) {
  window.location.href = `/analysis/?dataset=${datasetId}`;
}

function analyzeDataset(datasetId) {
  window.location.href = `/analysis/?dataset=${datasetId}`;
}

function deleteDataset(datasetId, datasetName) {
  // Dispatch custom event to open the modal
  window.dispatchEvent(new CustomEvent('delete-dataset', {
    detail: { id: datasetId, name: datasetName }
  }));
}

// Global function to handle the actual deletion after confirmation
window.confirmDelete = function(datasetId) {
  const csrftoken = getCookie('csrftoken');
  fetch(`/api/datasets/${datasetId}/`, {
    method: 'DELETE',
    headers: { 'X-CSRFToken': csrftoken }
  })
  .then(response => {
    if (response.ok) {
      showAlert('Success', 'Dataset deleted successfully', 'success');
      // Remove the card from the DOM immediately
      removeDatasetCard(datasetId);
    } else {
      showAlert('Error', 'Failed to delete dataset', 'error');
    }
  })
  .catch(error => {
    console.error('Error:', error);
    showAlert('Error', 'An error occurred while deleting the dataset', 'error');
  });
};

function openAnalysis(analysisId) {
  window.location.href = `/analysis/${analysisId}/`;
}

// Function to add a new dataset card to the grid
function addDatasetCard(dataset) {
  const datasetsGrid = document.querySelector('.grid.grid-cols-1.md\\:grid-cols-3.lg\\:grid-cols-4.xl\\:grid-cols-6');
  
  if (!datasetsGrid) {
    // If no datasets grid exists (empty state), reload the page
    setTimeout(() => location.reload(), 1500);
    return;
  }

  // Remove .csv extension from name
  const displayName = dataset.name.endsWith('.csv') ? dataset.name.slice(0, -4) : dataset.name;
  
  // Create the new card HTML
  const cardHTML = `
    <div class="bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow cursor-pointer overflow-hidden" onclick="openDataset('${dataset.id}')">
      <!-- Card Header -->
      <div class="bg-gray-50 px-3 py-2 border-b border-gray-200">
        <div class="flex justify-between items-center">
          <h3 class="font-medium text-sm text-primary truncate" title="${dataset.name}">
            ${displayName}
          </h3>
          <span class="px-1.5 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full whitespace-nowrap ml-1">
            ${dataset.row_count}
          </span>
        </div>
      </div>
      
      <!-- Card Body - Plot -->
      <div class="p-2 h-24">
        <canvas id="dataset-plot-${dataset.id}" data-dataset-id="${dataset.id}"></canvas>
      </div>
      
      <!-- Card Footer -->
      <div class="px-3 py-2 border-t border-gray-200 bg-gray-50">
        <div class="flex justify-between items-center">
          <p class="text-xs text-secondary">Just now</p>
          <div class="flex gap-2">
            <button class="text-blue-600 hover:text-blue-800 p-1" onclick="event.stopPropagation(); analyzeDataset('${dataset.id}')" title="Analyze">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
              </svg>
            </button>
            <button class="text-red-600 hover:text-red-800 p-1" onclick="event.stopPropagation(); deleteDataset('${dataset.id}', '${displayName}')" title="Delete">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  `;

  // Create a temporary div to hold the HTML
  const tempDiv = document.createElement('div');
  tempDiv.innerHTML = cardHTML;
  const newCard = tempDiv.firstElementChild;

  // Add the new card at the beginning of the grid (after upload card if it's in the grid)
  const firstCard = datasetsGrid.firstElementChild;
  if (firstCard && firstCard.querySelector('#quick-upload')) {
    // If the upload card is part of the grid, insert after it
    datasetsGrid.insertBefore(newCard, firstCard.nextElementSibling);
  } else {
    // Otherwise insert at the beginning
    datasetsGrid.insertBefore(newCard, firstCard);
  }

  // Initialize the plot for the new card
  setTimeout(() => {
    const canvas = document.getElementById(`dataset-plot-${dataset.id}`);
    if (canvas) {
      // Create placeholder plot initially (data will load async)
      createPlaceholderPlot(canvas);
      // Then try to load actual data
      fetch(`/api/datasets/${dataset.id}/data/`)
        .then(response => response.json())
        .then(data => {
          if (data.frequencies && data.frequencies.length > 0) {
            // Destroy placeholder and create real plot
            if (canvas.chart) {
              canvas.chart.destroy();
            }
            createDatasetPlot(canvas, data);
          }
        })
        .catch(error => {
          console.error('Error fetching dataset data for new card:', error);
        });
    }
  }, 100);

  // Add a subtle highlight animation to the new card
  newCard.style.backgroundColor = '#dbeafe'; // Light blue background
  setTimeout(() => {
    newCard.style.transition = 'background-color 2s ease-out';
    newCard.style.backgroundColor = '#ffffff'; // Fade back to white
  }, 1000);
}

// Function to update the dataset count in the KPI card
function updateDatasetCount() {
  const datasetCountElement = document.querySelector('.kpi-card p.text-2xl');
  if (datasetCountElement) {
    const currentCount = parseInt(datasetCountElement.textContent) || 0;
    datasetCountElement.textContent = currentCount + 1;
  }
}

// Function to remove dataset card from DOM when deleted
function removeDatasetCard(datasetId) {
  const card = document.querySelector(`[onclick*="openDataset('${datasetId}')"]`);
  if (card) {
    // Add fade out animation
    card.style.transition = 'opacity 0.5s ease-out, transform 0.5s ease-out';
    card.style.opacity = '0';
    card.style.transform = 'scale(0.95)';
    
    setTimeout(() => {
      card.remove();
      // Update the dataset count
      const datasetCountElement = document.querySelector('.kpi-card p.text-2xl');
      if (datasetCountElement) {
        const currentCount = parseInt(datasetCountElement.textContent) || 0;
        datasetCountElement.textContent = Math.max(0, currentCount - 1);
      }
    }, 500);
  }
}

// Project switching functions
function openProjectSwitcher() {
  fetch('/api/projects/', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'same-origin'  // Include cookies for authentication
  })
    .then(response => {
      console.log('Projects API response status:', response.status);
      if (response.status === 302) {
        throw new Error('Not authenticated - please refresh the page and log in');
      }
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      return response.json();
    })
    .then(data => {
      console.log('Projects API data:', data);
      if (data.ok === false) {
        throw new Error(data.error || 'Server returned error');
      }
      if (data.projects !== undefined) {
        showProjectSwitcherModal(data.projects);
      } else {
        console.error('No projects property in response:', data);
        showAlert('Error', 'Invalid response from server', 'error');
      }
    })
    .catch(error => {
      console.error('Error fetching projects:', error);
      showAlert('Error', `Failed to load projects: ${error.message}`, 'error');
    });
}

function showProjectSwitcherModal(projects) {
  // Create project switcher modal HTML
  const modalHTML = `
    <div id="projectSwitcherModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50" onclick="closeProjectSwitcherModal(event)">
      <div class="relative top-20 mx-auto p-5 border w-11/12 max-w-lg shadow-lg rounded-md bg-white" onclick="event.stopPropagation()">
        <div class="mt-3">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">Switch Project</h3>
            <button class="text-gray-400 hover:text-gray-600" onclick="closeProjectSwitcherModal()">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </button>
          </div>
          
          <div class="max-h-96 overflow-y-auto space-y-2">
            ${projects.map(project => {
              const projectNameEscaped = project.name.replace(/'/g, "\\'");
              const projectDescriptionEscaped = project.description ? project.description.replace(/'/g, "\\'") : '';
              
              return `
                <div class="p-3 border rounded-lg hover:bg-gray-50 transition-colors ${project.is_active ? 'bg-blue-50 border-blue-200' : 'border-gray-200'}">
                  <div class="flex justify-between items-start">
                    <div class="flex-1 cursor-pointer" onclick="switchToProject('${project.id}', '${projectNameEscaped}')">
                      <div class="flex items-center">
                        <h4 class="font-medium text-gray-900">${project.name}</h4>
                        ${project.is_active ? '<span class="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">Active</span>' : ''}
                      </div>
                      ${project.description ? `<p class="text-sm text-gray-600 mt-1">${project.description}</p>` : ''}
                      <div class="flex items-center text-xs text-gray-500 mt-2 space-x-4">
                        <span>${project.dataset_count} datasets</span>
                        <span>${project.member_count} member${project.member_count !== 1 ? 's' : ''}</span>
                        <span class="capitalize">${project.visibility}</span>
                      </div>
                    </div>
                    <div class="ml-3 flex items-center space-x-2">
                      ${!project.is_active ? `
                        <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                        </svg>
                      ` : ''}
                      ${project.name !== 'Default' ? `
                        <button class="text-red-600 hover:text-red-800 p-1" onclick="event.stopPropagation(); confirmDeleteProject('${project.id}', '${projectNameEscaped}', ${project.dataset_count})" title="Delete Project">
                          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                          </svg>
                        </button>
                      ` : ''}
                    </div>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
          
          <div class="mt-4 pt-4 border-t border-gray-200">
            <button class="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors" onclick="createProject()">
              <svg class="w-4 h-4 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
              </svg>
              Create New Project
            </button>
          </div>
        </div>
      </div>
    </div>
  `;
  
  // Remove existing modal if present
  const existingModal = document.getElementById('projectSwitcherModal');
  if (existingModal) {
    existingModal.remove();
  }
  
  // Add modal to body
  document.body.insertAdjacentHTML('beforeend', modalHTML);
}

function switchToProject(projectId, projectName) {
  const csrftoken = getCookie('csrftoken');
  
  fetch('/api/projects/switch/', {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrftoken,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ project_id: projectId })
  })
  .then(response => response.json())
  .then(data => {
    if (data.ok) {
      showAlert('Success', `Switched to project "${projectName}"`, 'success');
      closeProjectSwitcherModal();
      // Reload page to show datasets from new active project
      setTimeout(() => location.reload(), 1000);
    } else {
      showAlert('Error', data.error || 'Failed to switch project', 'error');
    }
  })
  .catch(error => {
    console.error('Error switching project:', error);
    showAlert('Error', 'Failed to switch project', 'error');
  });
}

function closeProjectSwitcherModal(event) {
  if (event && event.target.id !== 'projectSwitcherModal') {
    return;
  }
  
  const modal = document.getElementById('projectSwitcherModal');
  if (modal) {
    modal.remove();
  }
}

function showCreateProjectModal() {
  const modalHTML = `
    <div id="createProjectModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50" onclick="closeCreateProjectModal(event)">
      <div class="relative top-20 mx-auto p-5 border w-11/12 max-w-md shadow-lg rounded-md bg-white" onclick="event.stopPropagation()">
        <div class="mt-3">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">Create New Project</h3>
            <button class="text-gray-400 hover:text-gray-600" onclick="closeCreateProjectModal()">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </button>
          </div>
          
          <form id="createProjectForm" onsubmit="submitCreateProject(event)">
            <div class="mb-4">
              <label for="projectName" class="block text-sm font-medium text-gray-700 mb-2">Project Name</label>
              <input type="text" id="projectName" name="name" required maxlength="255"
                     class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                     placeholder="Enter project name">
            </div>
            
            <div class="mb-4">
              <label for="projectDescription" class="block text-sm font-medium text-gray-700 mb-2">Description (Optional)</label>
              <textarea id="projectDescription" name="description" rows="3"
                        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Describe your project..."></textarea>
            </div>
            
            <div class="mb-6">
              <label for="projectVisibility" class="block text-sm font-medium text-gray-700 mb-2">Visibility</label>
              <select id="projectVisibility" name="visibility"
                      class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="private">Private - Only you and invited members</option>
                <option value="internal">Internal - Visible to all users</option>
                <option value="public">Public - Visible to everyone</option>
              </select>
            </div>
            
            <div class="flex justify-end space-x-3">
              <button type="button" class="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors" onclick="closeCreateProjectModal()">
                Cancel
              </button>
              <button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors">
                Create Project
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `;
  
  // Remove existing modal if present
  const existingModal = document.getElementById('createProjectModal');
  if (existingModal) {
    existingModal.remove();
  }
  
  // Add modal to body
  document.body.insertAdjacentHTML('beforeend', modalHTML);
}

function closeCreateProjectModal(event) {
  if (event && event.target.id !== 'createProjectModal') {
    return;
  }
  
  const modal = document.getElementById('createProjectModal');
  if (modal) {
    modal.remove();
  }
}

function submitCreateProject(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  const csrftoken = getCookie('csrftoken');
  
  fetch('/api/projects/create/', {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrftoken,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      name: formData.get('name'),
      description: formData.get('description'),
      visibility: formData.get('visibility')
    })
  })
  .then(response => response.json())
  .then(data => {
    if (data.ok) {
      showAlert('Success', `Project "${data.project.name}" created successfully`, 'success');
      closeCreateProjectModal();
      // Reload page to show new project
      setTimeout(() => location.reload(), 1000);
    } else {
      showAlert('Error', data.error || 'Failed to create project', 'error');
    }
  })
  .catch(error => {
    console.error('Error creating project:', error);
    showAlert('Error', 'Failed to create project', 'error');
  });
}

function confirmDeleteProject(projectId, projectName, datasetCount) {
  const message = datasetCount > 0 
    ? `Are you sure you want to delete project "${projectName}"? This will also delete ${datasetCount} dataset${datasetCount !== 1 ? 's' : ''} within this project. This action cannot be undone.`
    : `Are you sure you want to delete project "${projectName}"? This action cannot be undone.`;
    
  const confirmHTML = `
    <div id="deleteProjectModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div class="relative top-20 mx-auto p-5 border w-11/12 max-w-md shadow-lg rounded-md bg-white">
        <div class="mt-3">
          <div class="flex items-center mb-4">
            <div class="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-red-100">
              <svg class="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 18.5c-.77.833.192 2.5 1.732 2.5z"></path>
              </svg>
            </div>
          </div>
          <div class="text-center">
            <h3 class="text-lg font-medium text-gray-900 mb-2">Delete Project</h3>
            <p class="text-sm text-gray-600 mb-6">${message}</p>
            <div class="flex justify-center space-x-3">
              <button class="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors" onclick="closeDeleteProjectModal()">
                Cancel
              </button>
              <button class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors" onclick="deleteProject('${projectId}', '${projectName}')">
                Delete Project
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
  
  document.body.insertAdjacentHTML('beforeend', confirmHTML);
}

function closeDeleteProjectModal() {
  const modal = document.getElementById('deleteProjectModal');
  if (modal) {
    modal.remove();
  }
}

function deleteProject(projectId, projectName) {
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
      showAlert('Success', `Project "${projectName}" deleted successfully`, 'success');
      closeDeleteProjectModal();
      closeProjectSwitcherModal();
      // Reload page to reflect changes
      setTimeout(() => location.reload(), 1000);
    } else {
      showAlert('Error', data.error || 'Failed to delete project', 'error');
    }
  })
  .catch(error => {
    console.error('Error deleting project:', error);
    showAlert('Error', 'Failed to delete project', 'error');
  });
}

function createProject() {
  showCreateProjectModal();
}

// Helper function to get CSRF token
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
