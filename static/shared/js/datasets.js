/**
 * Dataset Management - Shared dataset operations
 * Handles dataset CRUD operations, title editing, and interactions
 */

// Dataset interaction functions
function openDataset(datasetId) {
  window.location.href = `/analysis/dataset/${datasetId}/`;
}

function analyzeDataset(datasetId) {
  window.location.href = `/analysis/dataset/${datasetId}/`;
}

function shareDataset(datasetId) {
  showNotification('Info', 'Share functionality coming soon', 'info');
}

function downloadDataset(datasetId) {
  window.location.href = `/api/datasets/${datasetId}/download/`;
}

// Dataset deletion with confirmation
function deleteDataset(datasetId, datasetName) {
  showConfirmModal(
    `Are you sure you want to delete "${datasetName}"? This action cannot be undone.`,
    async () => {
      try {
        const result = await ApiEndpoints.datasets.delete(datasetId);
        if (result.ok) {
          showNotification('Success', 'Dataset deleted successfully', 'success');
          // Remove the dataset card from the UI
          const datasetCard = document.querySelector(`[data-dataset-id="${datasetId}"]`);
          if (datasetCard) {
            // Check if this is the whole card or just a part of it
            const wholeCard = datasetCard.closest('.bg-white.rounded-lg') || datasetCard;
            wholeCard.style.transition = 'opacity 0.5s ease-out, transform 0.5s ease-out';
            wholeCard.style.opacity = '0';
            wholeCard.style.transform = 'scale(0.95)';
            setTimeout(() => wholeCard.remove(), 500);
          }
          // Update project dataset count
          updateProjectDatasetCount();
          
          // Refresh the page or update counters
          if (typeof updateDashboardStats === 'function') {
            updateDashboardStats();
          }
        } else {
          showNotification('Error', result.error || 'Failed to delete dataset', 'error');
        }
      } catch (error) {
        showNotification('Error', 'Failed to delete dataset', 'error');
      }
    },
    null,
    { dangerous: true }
  );
}

// Dataset moving between projects
function moveDatasetToProject(datasetId, currentProjectName) {
  // Get available projects and show selection modal
  ApiEndpoints.projects.list().then(result => {
    if (result.ok) {
      const projects = result.projects.filter(p => !p.is_active); // Exclude current project
      if (projects.length === 0) {
        showNotification('Info', 'No other projects available to move to', 'info');
        return;
      }
      
      showProjectSelectionModal(projects, (targetProjectId) => {
        moveDataset(datasetId, targetProjectId);
      });
    } else {
      showNotification('Error', 'Failed to load projects', 'error');
    }
  }).catch(error => {
    showNotification('Error', 'Failed to load projects', 'error');
  });
}

function showProjectSelectionModal(projects, onSelect) {
  const modal = document.createElement('div');
  modal.className = 'fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50';
  
  const modalId = 'project-select-' + Date.now();
  modal.id = modalId;
  
  const projectOptions = projects.map(project => 
    `<div class="cursor-pointer p-3 hover:bg-gray-50 border-b border-gray-200" onclick="selectProject('${modalId}', '${project.id}')">
      <div class="font-medium">${project.name}</div>
      <div class="text-sm text-gray-500">${project.description || 'No description'}</div>
      <div class="text-xs text-gray-400">${project.dataset_count} datasets</div>
    </div>`
  ).join('');
  
  modal.innerHTML = `
    <div class="relative top-20 mx-auto p-5 border w-11/12 max-w-md shadow-lg rounded-md bg-white">
      <div class="mt-3">
        <h3 class="text-lg font-medium text-gray-900 mb-4">Select Target Project</h3>
        <div class="max-h-60 overflow-y-auto border border-gray-200 rounded-md">
          ${projectOptions}
        </div>
        <div class="flex justify-end space-x-3 mt-6">
          <button onclick="closeProjectSelectModal('${modalId}')" class="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400 transition-colors">
            Cancel
          </button>
        </div>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  // Store callback
  window[`projectSelectCallback_${modalId}`] = onSelect;
}

function selectProject(modalId, projectId) {
  const callback = window[`projectSelectCallback_${modalId}`];
  closeProjectSelectModal(modalId);
  if (callback) {
    callback(projectId);
  }
}

function closeProjectSelectModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.remove();
  }
  delete window[`projectSelectCallback_${modalId}`];
}

async function moveDataset(datasetId, targetProjectId) {
  try {
    const result = await ApiEndpoints.datasets.move(datasetId, targetProjectId);
    if (result.ok) {
      showNotification('Success', result.message, 'success');
      // Remove dataset card from current view or refresh
      const datasetCard = document.querySelector(`[data-dataset-id="${datasetId}"]`);
      if (datasetCard) {
        datasetCard.style.opacity = '0.5';
        setTimeout(() => {
          datasetCard.remove();
          updateProjectDatasetCount();
        }, 1000);
      }
    } else {
      showNotification('Error', result.error || 'Failed to move dataset', 'error');
    }
  } catch (error) {
    showNotification('Error', 'Failed to move dataset', 'error');
  }
}

// Title editing functionality
let longPressTimer = null;
let isLongPress = false;

function initializeTitleEditing() {
  document.querySelectorAll('.editable-title').forEach(title => {
    // Remove any existing listeners to avoid duplicates
    title.removeEventListener('mousedown', handleMouseDown);
    title.removeEventListener('touchstart', handleTouchStart);
    title.removeEventListener('mouseup', handleMouseUp);
    title.removeEventListener('touchend', handleTouchEnd);
    title.removeEventListener('mouseleave', handleMouseLeave);
    title.removeEventListener('touchcancel', handleTouchCancel);
    
    // Add event listeners for long press detection
    title.addEventListener('mousedown', handleMouseDown);
    title.addEventListener('touchstart', handleTouchStart, { passive: false });
    title.addEventListener('mouseup', handleMouseUp);
    title.addEventListener('touchend', handleTouchEnd);
    title.addEventListener('mouseleave', handleMouseLeave);
    title.addEventListener('touchcancel', handleTouchCancel);
  });
}

function handleMouseDown(e) {
  startLongPress(e.currentTarget);
}

function handleTouchStart(e) {
  e.preventDefault(); // Prevent default touch behavior
  startLongPress(e.currentTarget);
}

function handleMouseUp(e) {
  cancelLongPress();
  if (!isLongPress) {
    // Normal click - do nothing, let the card onclick handle it
  }
}

function handleTouchEnd(e) {
  cancelLongPress();
  if (!isLongPress) {
    // Normal tap - do nothing
  }
}

function handleMouseLeave(e) {
  cancelLongPress();
}

function handleTouchCancel(e) {
  cancelLongPress();
}

function startLongPress(element) {
  isLongPress = false;
  longPressTimer = setTimeout(() => {
    isLongPress = true;
    enterEditMode(element);
  }, 500); // 500ms for long press
}

function cancelLongPress() {
  if (longPressTimer) {
    clearTimeout(longPressTimer);
    longPressTimer = null;
  }
  setTimeout(() => {
    isLongPress = false;
  }, 10);
}

function enterEditMode(titleElement) {
  const datasetId = titleElement.closest('.bg-white').querySelector('[onclick*="openDataset"]').getAttribute('onclick').match(/'([^']+)'/)[1];
  const currentTitle = titleElement.textContent.trim();
  
  // Create input field
  const input = document.createElement('input');
  input.type = 'text';
  input.value = currentTitle;
  input.className = 'w-full px-2 py-1 text-sm font-medium bg-white border border-blue-500 rounded focus:outline-none focus:border-blue-600';
  
  // Replace title with input
  titleElement.style.display = 'none';
  titleElement.parentNode.insertBefore(input, titleElement.nextSibling);
  
  input.focus();
  input.select();
  
  // Handle save/cancel
  input.addEventListener('blur', () => saveTitle(input, titleElement, datasetId));
  input.addEventListener('keydown', (e) => handleTitleKeydown(e, input, titleElement, datasetId));
}

function handleTitleKeydown(event, inputElement, titleElement, datasetId) {
  if (event.key === 'Enter') {
    event.preventDefault();
    saveTitle(inputElement, titleElement, datasetId);
  } else if (event.key === 'Escape') {
    event.preventDefault();
    cancelEditTitle(inputElement, titleElement);
  }
}

function cancelEditTitle(inputElement, titleElement) {
  inputElement.remove();
  titleElement.style.display = '';
}

async function saveTitle(inputElement, titleElement, datasetId) {
  const newTitle = inputElement.value.trim();
  const originalTitle = titleElement.textContent.trim();
  
  if (!newTitle || newTitle === originalTitle) {
    cancelEditTitle(inputElement, titleElement);
    return;
  }
  
  try {
    const result = await ApiEndpoints.datasets.update(datasetId, { name: newTitle });
    if (result.ok) {
      titleElement.textContent = newTitle;
      inputElement.remove();
      titleElement.style.display = '';
      showNotification('Success', 'Dataset renamed successfully', 'success');
    } else {
      showNotification('Error', result.error || 'Failed to rename dataset', 'error');
      cancelEditTitle(inputElement, titleElement);
    }
  } catch (error) {
    showNotification('Error', 'Failed to rename dataset', 'error');
    cancelEditTitle(inputElement, titleElement);
  }
}

// Click handler for edit icon
function editTitle(datasetId) {
  const titleElement = document.querySelector(`[data-dataset-id="${datasetId}"] .editable-title`);
  if (titleElement) {
    enterEditMode(titleElement);
  }
}

// Helper function to update project dataset count
function updateProjectDatasetCount() {
  const countElement = document.getElementById('project-dataset-count');
  if (countElement) {
    // Count visible dataset cards on the page (only root card divs, not child elements)
    const visibleDatasets = document.querySelectorAll('.bg-white.rounded-lg[data-dataset-id]').length;
    const countText = visibleDatasets === 1 ? '1 dataset' : `${visibleDatasets} datasets`;
    countElement.textContent = countText;
  }
}

// Export for module systems if available
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    openDataset, analyzeDataset, shareDataset, downloadDataset,
    deleteDataset, moveDatasetToProject, initializeTitleEditing, editTitle,
    updateProjectDatasetCount
  };
}