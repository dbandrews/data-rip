// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Function to check if the grid is available
    function checkGridReady() {
        const gridOut = document.querySelector('#ag-grid-out');
        if (gridOut && gridOut.gridOptions && gridOut.gridOptions.api) {
            setupGridTracking();
            return true;
        }
        return false;
    }

    // Function to set up grid tracking
    function setupGridTracking() {
        // Get grid API
        const gridOut = document.querySelector('#ag-grid-out');
        const api = gridOut.gridOptions.api;
        
        // Define function to calculate summaries
        window.updateColumnSummaries = function() {
            try {
                const columnIds = api.getColumnDefs().map(col => col.field);
                const summaries = {};
                
                columnIds.forEach(colId => {
                    let checkedCount = 0;
                    let totalCount = 0;
                    
                    api.forEachNode(node => {
                        if (node.data && node.data[colId] === true) {
                            checkedCount++;
                        }
                        totalCount++;
                    });
                    
                    if (totalCount > 0) {
                        summaries[colId] = {
                            checked: checkedCount,
                            total: totalCount,
                            fraction: checkedCount / totalCount
                        };
                    }
                });
                
                // Update the hidden div with the summaries
                const summariesDiv = document.getElementById('js-column-summaries');
                if (summariesDiv) {
                    summariesDiv.textContent = JSON.stringify(summaries);
                }
            } catch (e) {
                console.error('Error updating summaries:', e);
            }
        };
        
        // Listen for cell value changes
        api.addEventListener('cellValueChanged', function() {
            window.updateColumnSummaries();
        });
        
        // Also update on model updated
        api.addEventListener('modelUpdated', function() {
            window.updateColumnSummaries();
        });
        
        // Set up custom checkbox renderer
        class CheckboxRenderer {
            init(params) {
                this.params = params;
                this.eGui = document.createElement('div');
                this.eGui.className = 'checkbox-cell';
                
                this.checkbox = document.createElement('input');
                this.checkbox.type = 'checkbox';
                this.checkbox.className = 'cell-checkbox';
                this.checkbox.checked = params.value === true;
                
                this.valueSpan = document.createElement('span');
                this.valueSpan.className = 'cell-value';
                
                // Get original value if it exists
                const origKey = '_orig_' + params.column.colId;
                const origValue = params.data && params.data[origKey] !== undefined ? 
                    params.data[origKey] : 
                    (params.value !== true && params.value !== false ? params.value : '');
                
                this.valueSpan.textContent = origValue !== null && origValue !== undefined ? origValue : '';
                
                // Checkbox change handler
                this.checkbox.addEventListener('change', () => {
                    params.setValue(this.checkbox.checked);
                    window.updateColumnSummaries();
                });
                
                this.eGui.appendChild(this.checkbox);
                this.eGui.appendChild(this.valueSpan);
            }
            
            getGui() {
                return this.eGui;
            }
            
            refresh(params) {
                this.checkbox.checked = params.value === true;
                return true;
            }
        }
        
        // Register renderer
        window.CheckboxRenderer = CheckboxRenderer;
        
        // Register with ag-Grid
        agGrid.Grid.setComponents({
            CheckboxRenderer: CheckboxRenderer
        });
        
        // Initial update
        window.updateColumnSummaries();
        
        console.log('Grid tracking initialized successfully!');
    }

    // Check for grid immediately
    if (!checkGridReady()) {
        // If not ready, check periodically
        const interval = setInterval(function() {
            if (checkGridReady()) {
                clearInterval(interval);
            }
        }, 200);
    }
    
    // Set up MutationObserver to detect grid initialization
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes && mutation.addedNodes.length > 0) {
                for (let i = 0; i < mutation.addedNodes.length; i++) {
                    const node = mutation.addedNodes[i];
                    if (node.id === 'ag-grid-out' || 
                        (node.querySelectorAll && node.querySelectorAll('#ag-grid-out').length > 0)) {
                        setTimeout(checkGridReady, 100);
                    }
                }
            }
        });
    });
    
    observer.observe(document.body, { childList: true, subtree: true });
});