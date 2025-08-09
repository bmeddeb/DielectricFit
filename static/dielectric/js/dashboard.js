// Notifications and confirmations are provided by shared/js/notifications.js

document.addEventListener('DOMContentLoaded', function () {
  console.log('Dashboard script loaded');
  
  // Initialize title editing
  initializeTitleEditing();

  // --- Upload Logic ---
  let uploadInput = document.getElementById('quick-upload');
  if (!uploadInput) return;
  const uploadLabel = uploadInput.parentElement;

  const handleMultipleFileSelect = (files) => {
    if (!files || files.length === 0) return;
    
    // Validate all files first
    const invalidFiles = [];
    const validFiles = [];
    
    Array.from(files).forEach(file => {
      if (!file.name.toLowerCase().endsWith('.csv')) {
        invalidFiles.push(file.name);
      } else {
        validFiles.push(file);
      }
    });
    
    if (invalidFiles.length > 0) {
      showNotification('Invalid Files', `Please select only CSV files. Invalid: ${invalidFiles.join(', ')}`, 'error');
      if (validFiles.length === 0) return;
    }
    
    if (validFiles.length === 0) return;
    
    // Show upload progress
    updateUploadProgress(0, validFiles.length);
    
    // Upload files sequentially to avoid overwhelming the server
    uploadFilesSequentially(validFiles, 0);
  };
  
  // Batch upload status element
  let batchStatusEl = null;

  function showOrUpdateBatchStatus(current, total, filename, done = false, errors = 0) {
    let container = document.getElementById('alert-container');
    if (!container) return;
    if (!batchStatusEl) {
      batchStatusEl = document.createElement('div');
      batchStatusEl.id = 'batch-upload-status';
      batchStatusEl.className = 'max-w-sm w-full bg-blue-50 text-blue-800 border border-blue-200 rounded-lg p-4 shadow-lg mb-2';
      container.appendChild(batchStatusEl);
    }
    if (done) {
      batchStatusEl.className = errors === 0 ? 'max-w-sm w-full bg-green-50 text-green-800 border border-green-200 rounded-lg p-4 shadow-lg mb-2'
                                            : 'max-w-sm w-full bg-yellow-50 text-yellow-800 border border-yellow-200 rounded-lg p-4 shadow-lg mb-2';
      batchStatusEl.innerHTML = `<div class="flex items-start"><div class="flex-1"><p class="font-medium">Upload complete</p><p class="text-sm mt-1">${total - errors} succeeded${errors ? `, ${errors} failed` : ''}</p></div></div>`;
      setTimeout(() => { if (batchStatusEl) { batchStatusEl.remove(); batchStatusEl = null; } }, 3000);
    } else {
      batchStatusEl.innerHTML = `<div class="flex items-start"><div class="flex-1"><p class="font-medium">Uploading ${current}/${total}</p><p class="text-sm mt-1 truncate">${filename}</p></div></div>`;
    }
  }

  let errorCount = 0;
  const uploadFilesSequentially = async (files, currentIndex) => {
    if (currentIndex >= files.length) {
      resetUploadUI();
      showOrUpdateBatchStatus(files.length, files.length, '', true, errorCount);
      return;
    }
    
    const file = files[currentIndex];
    const formData = new FormData();
    formData.append('file', file);
    const csrftoken = getCsrfToken();
    
    try {
      showOrUpdateBatchStatus(currentIndex + 1, files.length, file.name, false);
      const response = await fetch('/api/datasets/upload/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrftoken },
        body: formData,
      });
      
      const data = await response.json();
      
      if (data.ok) {
        // Add the new dataset card immediately
        addDatasetCard(data.dataset);
        // Update the project dataset count
        updateProjectDatasetCount();
      } else {
        console.error('Upload failed:', data.error);
        errorCount += 1;
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      errorCount += 1;
    }
    
    // Update progress and continue with next file
    updateUploadProgress(currentIndex + 1, files.length);
    setTimeout(() => uploadFilesSequentially(files, currentIndex + 1), 500);
  };
  
  function ensureProgressElements() {
    let progress = uploadLabel.querySelector('#upload-progress');
    if (!progress) {
      progress = document.createElement('div');
      progress.id = 'upload-progress';
      progress.className = 'flex flex-col items-center justify-center';
      progress.style.display = 'none';
      progress.innerHTML = `
        <svg class="w-8 h-8 mb-2 text-secondary animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <p id="upload-progress-text" class="text-sm text-secondary font-semibold">Preparing upload...</p>
        <div class="w-full bg-gray-200 rounded-full h-2 mt-2">
          <div id="upload-progress-bar" class="bg-blue-600 h-2 rounded-full transition-all duration-300" style="width: 0%"></div>
        </div>
      `;
      uploadLabel.appendChild(progress);
    }
    return progress;
  }

  const updateUploadProgress = (completed, total) => {
    const percentage = Math.round((completed / total) * 100);
    const progress = ensureProgressElements();
    const text = progress.querySelector('#upload-progress-text');
    const bar = progress.querySelector('#upload-progress-bar');
    // Hide default label content except the input and progress container
    Array.from(uploadLabel.children).forEach(child => {
      if (child === uploadInput || child === progress) return;
      child.style.display = 'none';
    });
    progress.style.display = '';
    if (text) text.textContent = `Uploading ${completed}/${total} files...`;
    if (bar) bar.style.width = `${percentage}%`;
  };

  function bindUploadInput() {
    uploadInput = document.getElementById('quick-upload');
    if (!uploadInput) return;
  uploadInput.addEventListener('change', (event) => {
    handleMultipleFileSelect(event.target.files);
  });
  }
  // Initial bind
  bindUploadInput();

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
    handleMultipleFileSelect(event.dataTransfer.files);
  });

  function resetUploadUI() {
    const progress = uploadLabel.querySelector('#upload-progress');
    // Show default content again
    Array.from(uploadLabel.children).forEach(child => {
      if (child === uploadInput || child === progress) return;
      child.style.display = '';
    });
    if (progress) {
      progress.style.display = 'none';
      const bar = progress.querySelector('#upload-progress-bar');
      const text = progress.querySelector('#upload-progress-text');
      if (bar) bar.style.width = '0%';
      if (text) text.textContent = 'Ready';
    }
    // Reset the file input so selecting the same files triggers change
    if (uploadInput) uploadInput.value = '';
  }

  // CSRF cookie helper not needed here; use getCsrfToken() from shared api.js

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
  const csrftoken = getCsrfToken();
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
  // Look for existing datasets grid
  let datasetsGrid = document.getElementById('datasets-grid');
  
  if (!datasetsGrid) {
    // No grid exists (empty state), create one
    const container = document.getElementById('datasets-container');
    const emptyState = document.getElementById('empty-state');
    
    if (container && emptyState) {
      // Hide empty state and create grid
      emptyState.style.display = 'none';
      
      datasetsGrid = document.createElement('div');
      datasetsGrid.id = 'datasets-grid';
      datasetsGrid.className = 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4';
      
      container.appendChild(datasetsGrid);
    } else {
      console.log('No datasets container found, card will appear after reload');
      return;
    }
  }

  // Remove .csv extension from name
  const displayName = dataset.name.endsWith('.csv') ? dataset.name.slice(0, -4) : dataset.name;
  
  // Create the new card HTML
  const cardHTML = `
    <div class="bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow overflow-hidden group" data-dataset-id="${dataset.id}">
      <!-- Card Header -->
      <div class="bg-gray-50 px-3 py-1.5 border-b border-gray-200">
        <div class="flex justify-between items-center">
          <div class="flex items-center flex-1 min-w-0">
            <h3 class="font-medium text-sm text-primary truncate editable-title mr-1" 
                data-dataset-id="${dataset.id}"
                data-original-name="${displayName}"
                title="${dataset.name} (Long press or click edit icon to rename)">
              <span class="title-text">${displayName}</span>
              <input type="text" class="title-input hidden w-full px-1 py-0 text-sm border border-blue-300 rounded focus:border-blue-500 focus:outline-none bg-white" 
                     value="${displayName}" 
                     onblur="cancelEditTitle(this)"
                     onkeydown="handleTitleKeydown(event, this)">
            </h3>
            <button class="edit-title-btn opacity-0 group-hover:opacity-100 hover:opacity-100 p-1 text-gray-400 hover:text-blue-600 transition-all duration-200" 
                    onclick="event.stopPropagation(); editTitle('${dataset.id}')" 
                    title="Rename dataset">
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
              </svg>
            </button>
          </div>
          <span class="px-1.5 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full whitespace-nowrap ml-2">
            ${dataset.row_count}
          </span>
        </div>
      </div>
      
      <!-- Card Body - Plot -->
      <div class="p-2 h-24 cursor-pointer" onclick="openDataset('${dataset.id}')">
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

  // Reinitialize title editing for the new card
  initializeTitleEditing();

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
  // Find the card by data-dataset-id attribute (most reliable)
  let card = document.querySelector(`[data-dataset-id="${datasetId}"]`);
  
  // If not found by data attribute, try the old method as fallback
  if (!card) {
    const cardBody = document.querySelector(`[onclick*="openDataset('${datasetId}')"]`);
    card = cardBody ? cardBody.closest('.bg-white.rounded-lg') : null;
  }
  
  if (card) {
    // If we found a non-card element (like the title), get the parent card
    const wholeCard = card.closest('.bg-white.rounded-lg') || card;
    
    // Add fade out animation
    wholeCard.style.transition = 'opacity 0.5s ease-out, transform 0.5s ease-out';
    wholeCard.style.opacity = '0';
    wholeCard.style.transform = 'scale(0.95)';
    
    setTimeout(() => {
      wholeCard.remove();
      // Update the project dataset count
      updateProjectDatasetCount();
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
                <div class="p-3 border rounded-lg hover:bg-gray-50 transition-colors ${project.is_active ? 'bg-blue-50 border-blue-200' : 'border-gray-200'}" data-project-id="${project.id}">
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
  const csrftoken = getCsrfToken();
  
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

// Dataset moving functions
function moveDataset(datasetId, datasetName) {
  // Fetch available projects for moving
  fetch('/api/projects/', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'same-origin'
  })
    .then(response => response.json())
    .then(data => {
      if (data.ok !== false && data.projects) {
        // Filter out the current active project
        const availableProjects = data.projects.filter(p => !p.is_active);
        if (availableProjects.length === 0) {
          showAlert('Info', 'No other projects available to move to', 'info');
          return;
        }
        showMoveDatasetModal(datasetId, datasetName, availableProjects);
      } else {
        showAlert('Error', 'Failed to load projects', 'error');
      }
    })
    .catch(error => {
      console.error('Error fetching projects:', error);
      showAlert('Error', 'Failed to load projects', 'error');
    });
}

function showMoveDatasetModal(datasetId, datasetName, projects) {
  const modalHTML = `
    <div id="moveDatasetModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50" onclick="closeMoveDatasetModal(event)">
      <div class="relative top-20 mx-auto p-5 border w-11/12 max-w-lg shadow-lg rounded-md bg-white" onclick="event.stopPropagation()">
        <div class="mt-3">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">Move Dataset to Project</h3>
            <button class="text-gray-400 hover:text-gray-600" onclick="closeMoveDatasetModal()">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </button>
          </div>
          
          <p class="text-sm text-gray-600 mb-4">
            Select a project to move <strong>${datasetName}</strong> to:
          </p>
          
          <div class="max-h-64 overflow-y-auto space-y-2">
            ${projects.map(project => {
              const projectNameEscaped = project.name.replace(/'/g, "\\'");
              return `
                <div class="p-3 border rounded-lg hover:bg-gray-50 transition-colors border-gray-200 cursor-pointer" 
                     onclick="confirmMoveDataset('${datasetId}', '${datasetName.replace(/'/g, "\\'")}', '${project.id}', '${projectNameEscaped}')">
                  <div class="flex justify-between items-center">
                    <div>
                      <h4 class="font-medium text-gray-900">${project.name}</h4>
                      ${project.description ? `<p class="text-sm text-gray-600 mt-1">${project.description}</p>` : ''}
                      <div class="flex items-center text-xs text-gray-500 mt-2 space-x-4">
                        <span>${project.dataset_count} datasets</span>
                        <span>${project.member_count} member${project.member_count !== 1 ? 's' : ''}</span>
                      </div>
                    </div>
                    <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                    </svg>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
          
          <div class="mt-4 pt-4 border-t border-gray-200">
            <button class="w-full px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400 transition-colors" onclick="closeMoveDatasetModal()">
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  `;
  
  // Remove existing modal if present
  const existingModal = document.getElementById('moveDatasetModal');
  if (existingModal) {
    existingModal.remove();
  }
  
  // Add modal to body
  document.body.insertAdjacentHTML('beforeend', modalHTML);
}

function closeMoveDatasetModal(event) {
  if (event && event.target !== event.currentTarget) return;
  const modal = document.getElementById('moveDatasetModal');
  if (modal) {
    modal.remove();
  }
}

function confirmMoveDataset(datasetId, datasetName, targetProjectId, targetProjectName) {
  showConfirmModal(
    `Move "${datasetName}" to project "${targetProjectName}"?`,
    () => {
      // Proceed with the move
      moveDatasetToProject(datasetId, datasetName, targetProjectId, targetProjectName);
    },
    null,
    {
      title: 'Move Dataset',
      confirmText: 'Move',
      cancelText: 'Cancel'
    }
  );
}

function moveDatasetToProject(datasetId, datasetName, targetProjectId, targetProjectName) {
  
  const csrftoken = getCsrfToken();
  
  fetch(`/api/datasets/${datasetId}/move/`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrftoken,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ target_project_id: targetProjectId })
  })
  .then(response => response.json())
  .then(data => {
    if (data.ok) {
      showAlert('Success', `Moved "${datasetName}" to "${targetProjectName}"`, 'success');
      closeMoveDatasetModal();
      // Remove the dataset card from the page
      const datasetCard = document.querySelector(`[onclick*="${datasetId}"]`);
      if (datasetCard && datasetCard.closest('.bg-white')) {
        datasetCard.closest('.bg-white').remove();
      }
    } else {
      showAlert('Error', data.error || 'Failed to move dataset', 'error');
    }
  })
  .catch(error => {
    console.error('Error moving dataset:', error);
    showAlert('Error', 'Failed to move dataset', 'error');
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
  const csrftoken = getCsrfToken();
  
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
    ? `Delete project "${projectName}"? Its ${datasetCount} dataset${datasetCount !== 1 ? 's' : ''} will be moved to your Default project.`
    : `Delete project "${projectName}"? It will be removed.`;
    
  showConfirmModal(
    message,
    () => {
      deleteProject(projectId, projectName, datasetCount);
    },
    null,
    {
      title: 'Delete Project',
      confirmText: 'Delete Project',
      cancelText: 'Cancel',
      dangerous: true
    }
  );
}

function deleteProject(projectId, projectName, datasetCount = 0) {
  const csrftoken = getCsrfToken();
  
  fetch(`/api/projects/${projectId}/delete/`, {
    method: 'DELETE',
    headers: {
      'X-CSRFToken': csrftoken
    }
  })
  .then(response => {
    if (!response.ok) {
      // Handle HTTP errors without calling response.json() twice
      return response.json().then(data => {
        throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
      }).catch(() => {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      });
    }
    return response.json();
  })
  .then(data => {
    if (data.ok) {
      const movedMsg = datasetCount > 0 ? ` and moved ${datasetCount} dataset${datasetCount !== 1 ? 's' : ''} to Default` : '';
      showAlert('Success', `Project "${projectName}" deleted${movedMsg}`, 'success');
      const modal = document.getElementById('projectSwitcherModal');
      if (modal) {
        const item = modal.querySelector(`[data-project-id="${projectId}"]`);
        if (item) item.remove();
        // Update Default project's dataset count in the modal, if present
        if (datasetCount > 0) {
          const projectRows = modal.querySelectorAll('[data-project-id]');
          projectRows.forEach(row => {
            const nameEl = row.querySelector('h4');
            if (nameEl && nameEl.textContent.trim() === 'Default') {
              const dsSpan = row.querySelector('span');
              if (dsSpan) {
                // Expecting text like "X datasets"; parse and increment
                const m = dsSpan.textContent.match(/(\d+)/);
                const current = m ? parseInt(m[1], 10) : 0;
                const next = current + datasetCount;
                dsSpan.textContent = `${next} dataset${next !== 1 ? 's' : ''}`;
              }
            }
          });
        }
        if (!modal.querySelector('[data-project-id]')) {
          closeProjectSwitcherModal();
        }
      }
    } else {
      showAlert('Error', data.error || 'Failed to delete project', 'error');
    }
  })
  .catch(error => {
    console.error('Error deleting project:', error);
    showAlert('Error', error.message || 'Failed to delete project', 'error');
  });
}

function createProject() {
  showCreateProjectModal();
}

// Helper function to update project dataset count
// updateProjectDatasetCount is provided by shared/js/datasets.js
