/**
 * Glowall - Admin Dashboard JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    initSidebar();
    initDropdowns();
    initAlerts();
    initForms();
    initBarFill();
    initModernFileUpload();
});

/**
 * Sidebar
 */
function initSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    const submenuToggles = document.querySelectorAll('.nav-item.has-submenu');
    
    // Toggle sidebar on mobile
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('active');
        });
    }
    
    // Close sidebar on click outside (mobile)
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 768) {
            if (!e.target.closest('.sidebar') && !e.target.closest('.sidebar-toggle')) {
                sidebar?.classList.remove('active');
            }
        }
    });
    
    // Submenu toggles
    submenuToggles.forEach(item => {
        const link = item.querySelector('.nav-link');
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Close other submenus
            submenuToggles.forEach(other => {
                if (other !== item) {
                    other.classList.remove('open');
                }
            });
            
            item.classList.toggle('open');
        });
    });
    
    // Open active submenu
    const activeSubmenu = document.querySelector('.nav-item.has-submenu .submenu a.active');
    if (activeSubmenu) {
        activeSubmenu.closest('.nav-item.has-submenu').classList.add('open');
    }
}

/**
 * Dropdowns
 */
function initDropdowns() {
    const userMenu = document.querySelector('.user-menu');
    
    if (userMenu) {
        const userBtn = userMenu.querySelector('.user-btn');
        const dropdown = userMenu.querySelector('.user-dropdown');

        if (!userBtn || !dropdown) {
            return;
        }

        const closeDropdown = () => {
            dropdown.classList.remove('active');
            userBtn.setAttribute('aria-expanded', 'false');
        };
        
        userBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            const isOpen = dropdown.classList.toggle('active');
            userBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        });
        
        dropdown.addEventListener('click', function(e) {
            e.stopPropagation();
        });

        document.addEventListener('click', function() {
            closeDropdown();
        });

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeDropdown();
            }
        });
    }
}

/**
 * Alerts
 */
function initAlerts() {
    const alerts = document.querySelectorAll('.alert');
    
    alerts.forEach(alert => {
        const closeBtn = alert.querySelector('.alert-close');
        
        closeBtn?.addEventListener('click', function() {
            alert.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => alert.remove(), 300);
        });
        
        // Auto dismiss after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.style.animation = 'slideOut 0.3s ease forwards';
                setTimeout(() => alert.remove(), 300);
            }
        }, 5000);
    });
}

/**
 * Forms
 */
function initForms() {
    // File input preview
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const preview = this.parentElement.querySelector('.image-preview');
            
            if (preview && this.files && this.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    preview.innerHTML = '<img src="' + e.target.result + '">';
                };
                reader.readAsDataURL(this.files[0]);
            }
        });
    });
    
    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('error');
                } else {
                    field.classList.remove('error');
                }
            });
            
            if (!isValid) {
                e.preventDefault();
            }
        });
    });
    
    // Collapsible sections
    const collapsibles = document.querySelectorAll('.collapsible .section-toggle');
    collapsibles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            this.closest('.collapsible').classList.toggle('collapsed');
        });
    });
}

/**
 * Bar Fill Animation
 */
function initBarFill() {
    const barFills = document.querySelectorAll('.bar-fill[data-width]');
    
    barFills.forEach(bar => {
        const width = bar.getAttribute('data-width');
        bar.style.width = width + '%';
    });
}

/**
 * Modern File Upload
 */
function initModernFileUpload() {
    const uploadAreas = document.querySelectorAll('.file-upload-area');
    
    uploadAreas.forEach(area => {
        const input = area.querySelector('.file-upload-input');
        const preview = area.closest('.file-upload-wrapper').querySelector('.file-preview');
        const previewImage = preview?.querySelector('.file-preview-image img');
        const previewName = preview?.querySelector('.file-preview-name');
        const previewSize = preview?.querySelector('.file-preview-size span');
        const removeBtn = preview?.querySelector('.btn-remove');
        
        if (!input) return;
        
        // Drag & Drop events
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            area.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            area.addEventListener(eventName, () => {
                area.classList.add('dragover');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            area.addEventListener(eventName, () => {
                area.classList.remove('dragover');
            }, false);
        });
        
        // Handle dropped files
        area.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                input.files = files;
                handleFileSelect(files[0]);
            }
        }, false);
        
        // Handle file selection via click
        input.addEventListener('change', (e) => {
            if (input.files && input.files[0]) {
                handleFileSelect(input.files[0]);
            }
        });
        
        // Handle file selection
        function handleFileSelect(file) {
            if (!file.type.startsWith('image/')) {
                alert('Please select an image file.');
                return;
            }
            
            // Show preview
            const reader = new FileReader();
            reader.onload = (e) => {
                if (previewImage) {
                    previewImage.src = e.target.result;
                }
                if (previewName) {
                    previewName.textContent = file.name;
                }
                if (previewSize) {
                    previewSize.textContent = formatFileSize(file.size);
                }
                if (preview) {
                    preview.classList.add('visible');
                }
                area.classList.add('has-file');
            };
            reader.readAsDataURL(file);
        }
        
        // Remove file
        if (removeBtn) {
            removeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                input.value = '';
                if (preview) {
                    preview.classList.remove('visible');
                }
                area.classList.remove('has-file');
                if (previewImage) {
                    previewImage.src = '';
                }
                if (previewName) {
                    previewName.textContent = '';
                }
            });
        }
    });
}

/**
 * Format file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Get CSRF Token
 */
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

/**
 * Toggle Product Featured
 */
function toggleFeatured(productId) {
    fetch(`/admin/products/${productId}/toggle-featured/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        }
    })
    .catch(error => console.error('Error:', error));
}

/**
 * Toggle Product Available
 */
function toggleAvailable(productId) {
    fetch(`/admin/products/${productId}/toggle-available/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        }
    })
    .catch(error => console.error('Error:', error));
}

/**
 * Confirm Delete
 */
function confirmDelete(message) {
    return confirm(message || 'Are you sure you want to delete this item?');
}

// Add CSS animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    .form-control.error {
        border-color: #dc2626;
    }
`;
document.head.appendChild(style);
