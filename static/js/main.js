/**
 * AI Study Planner - Main JavaScript
 * Premium Multi-Tenant Education Management System
 * Developer: Mohammed Usman | GitHub: issu321
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // ========== SIDEBAR TOGGLE ==========
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('show');
        });
    }
    
    // Close sidebar on mobile when clicking outside
    document.addEventListener('click', function(e) {
        if (window.innerWidth < 992 && sidebar && sidebar.classList.contains('show')) {
            if (!sidebar.contains(e.target) && !e.target.closest('.navbar-toggler')) {
                sidebar.classList.remove('show');
            }
        }
    });
    
    // ========== AUTO-DISMISS ALERTS ==========
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) bsAlert.close();
        }, 5000);
    });
    
    // ========== CONFIRM ACTIONS ==========
    document.querySelectorAll('[data-confirm]').forEach(function(el) {
        el.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm') || 'Are you sure?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
    
    // ========== FILE INPUT PREVIEW ==========
    document.querySelectorAll('input[type="file"]').forEach(function(input) {
        input.addEventListener('change', function() {
            const fileName = this.files[0]?.name || 'Choose file...';
            const label = this.closest('.input-group')?.querySelector('.file-label');
            if (label) label.textContent = fileName;
            
            // Show file size
            const fileSize = this.files[0]?.size;
            if (fileSize) {
                const sizeEl = this.closest('.input-group')?.querySelector('.file-size');
                if (sizeEl) sizeEl.textContent = formatFileSize(fileSize);
            }
        });
    });
    
    // ========== SEARCH TABLE ==========
    document.querySelectorAll('.table-search').forEach(function(input) {
        input.addEventListener('input', function() {
            const tableId = this.getAttribute('data-table');
            const table = document.getElementById(tableId);
            if (!table) return;
            
            const filter = this.value.toLowerCase();
            const rows = table.querySelectorAll('tbody tr');
            
            rows.forEach(function(row) {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            });
        });
    });
    
    // ========== TOOLTIPS ==========
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // ========== POPOVERS ==========
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // ========== ANIMATE ON SCROLL ==========
    const animateElements = document.querySelectorAll('.animate-on-scroll');
    if (animateElements.length > 0) {
        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-fade-in');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });
        
        animateElements.forEach(function(el) {
            observer.observe(el);
        });
    }
    
    // ========== TEST TIMER ==========
    const timerEl = document.getElementById('testTimer');
    if (timerEl) {
        const duration = parseInt(timerEl.getAttribute('data-duration')) || 60;
        let timeRemaining = duration * 60; // Convert to seconds
        
        function updateTimer() {
            const minutes = Math.floor(timeRemaining / 60);
            const seconds = timeRemaining % 60;
            timerEl.textContent = 
                String(minutes).padStart(2, '0') + ':' + 
                String(seconds).padStart(2, '0');
            
            if (timeRemaining <= 300) { // 5 minutes warning
                timerEl.style.background = 'var(--danger)';
                timerEl.classList.add('timer-warning');
            }
            
            if (timeRemaining <= 0) {
                clearInterval(timerInterval);
                timerEl.textContent = 'TIME UP!';
                // Auto-submit form
                const form = document.getElementById('testForm');
                if (form) {
                    form.submit();
                }
                return;
            }
            
            timeRemaining--;
        }
        
        const timerInterval = setInterval(updateTimer, 1000);
        updateTimer();
    }
    
    // ========== PROGRESS BARS ANIMATION ==========
    document.querySelectorAll('.progress-bar[data-progress]').forEach(function(bar) {
        const target = bar.getAttribute('data-progress');
        setTimeout(function() {
            bar.style.width = target + '%';
        }, 200);
    });
    
    // ========== NOTIFICATION REFRESH ==========
    function refreshNotificationCount() {
        fetch('/api/notifications/unread-count')
            .then(response => response.json())
            .then(data => {
                const badges = document.querySelectorAll('.notification-count');
                badges.forEach(function(badge) {
                    if (data.count > 0) {
                        badge.textContent = data.count;
                        badge.classList.remove('d-none');
                    } else {
                        badge.classList.add('d-none');
                    }
                });
            })
            .catch(function() {});
    }
    
    // Refresh every 60 seconds
    if (document.querySelector('.notification-count')) {
        setInterval(refreshNotificationCount, 60000);
    }
    
    // ========== FORM VALIDATION ==========
    document.querySelectorAll('form[data-validate]').forEach(function(form) {
        form.addEventListener('submit', function(e) {
            let isValid = true;
            
            form.querySelectorAll('[required]').forEach(function(field) {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('is-invalid');
                    
                    // Add error message
                    let feedback = field.nextElementSibling;
                    if (!feedback || !feedback.classList.contains('invalid-feedback')) {
                        feedback = document.createElement('div');
                        feedback.className = 'invalid-feedback';
                        field.parentNode.insertBefore(feedback, field.nextSibling);
                    }
                    feedback.textContent = 'This field is required';
                } else {
                    field.classList.remove('is-invalid');
                    field.classList.add('is-valid');
                }
            });
            
            // Password match validation
            const password = form.querySelector('[name="password"]');
            const confirmPassword = form.querySelector('[name="confirm_password"]');
            if (password && confirmPassword && password.value !== confirmPassword.value) {
                isValid = false;
                confirmPassword.classList.add('is-invalid');
            }
            
            if (!isValid) {
                e.preventDefault();
            }
        });
    });
    
    // Remove invalid state on input
    document.querySelectorAll('.form-control').forEach(function(input) {
        input.addEventListener('input', function() {
            this.classList.remove('is-invalid');
        });
    });
    
    // ========== MCQ OPTION SELECTION ==========
    document.querySelectorAll('.mcq-option').forEach(function(option) {
        option.addEventListener('click', function() {
            const name = this.querySelector('input[type="radio"]').name;
            document.querySelectorAll('input[name="' + name + '"]').forEach(function(radio) {
                radio.closest('.mcq-option').classList.remove('selected');
            });
            this.classList.add('selected');
        });
    });
    
    // ========== DYNAMIC FORM FIELDS ==========
    // Add more options for MCQ
    document.querySelectorAll('.add-option-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const container = document.getElementById(this.getAttribute('data-container'));
            const optionCount = container.querySelectorAll('.option-input').length + 1;
            
            const div = document.createElement('div');
            div.className = 'input-group mb-2 option-input';
            div.innerHTML = `
                <div class="input-group-text">
                    <input type="radio" name="correct_answer_option" value="${optionCount - 1}">
                </div>
                <input type="text" class="form-control" name="option_${optionCount}" placeholder="Option ${optionCount}" required>
                <button type="button" class="btn btn-outline-danger remove-option"><i class="fas fa-times"></i></button>
            `;
            container.appendChild(div);
            
            // Add remove handler
            div.querySelector('.remove-option').addEventListener('click', function() {
                div.remove();
            });
        });
    });
    
    // ========== CHART.JS DEFAULTS ==========
    if (typeof Chart !== 'undefined') {
        Chart.defaults.font.family = "'Inter', sans-serif";
        Chart.defaults.color = '#64748b';
        
        // Create charts if data available
        createDashboardCharts();
    }
    
    // ========== SMOOTH SCROLL ==========
    document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
        anchor.addEventListener('click', function(e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
    
});

// ========== UTILITY FUNCTIONS ==========

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
        day: 'numeric', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
    });
}

function timeAgo(dateString) {
    const date = new Date(dateString);
    const seconds = Math.floor((new Date() - date) / 1000);
    
    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + ' years ago';
    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + ' months ago';
    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + ' days ago';
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + ' hours ago';
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + ' minutes ago';
    return 'Just now';
}

function confirmAction(message, callback) {
    if (confirm(message || 'Are you sure?')) {
        callback();
    }
}

function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show shadow-sm`;
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    toastContainer.appendChild(toast);
    
    setTimeout(function() {
        const bsAlert = bootstrap.Alert.getOrCreateInstance(toast);
        if (bsAlert) bsAlert.close();
    }, 4000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.style.cssText = 'position:fixed;top:80px;right:20px;z-index:9999;max-width:350px;';
    document.body.appendChild(container);
    return container;
}

// ========== CHART FUNCTIONS ==========
function createDashboardCharts() {
    // User Growth Chart
    const userChart = document.getElementById('userGrowthChart');
    if (userChart && userChart.hasAttribute('data-labels')) {
        const labels = JSON.parse(userChart.getAttribute('data-labels'));
        const data = JSON.parse(userChart.getAttribute('data-values'));
        
        new Chart(userChart, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Users',
                    data: data,
                    borderColor: '#3b9aed',
                    backgroundColor: 'rgba(59, 154, 237, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointBackgroundColor: '#3b9aed'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
                    x: { grid: { display: false } }
                }
            }
        });
    }
    
    // Role Distribution Chart
    const roleChart = document.getElementById('roleDistributionChart');
    if (roleChart && roleChart.hasAttribute('data-values')) {
        const values = JSON.parse(roleChart.getAttribute('data-values'));
        
        new Chart(roleChart, {
            type: 'doughnut',
            data: {
                labels: ['Super Admin', 'Teachers', 'Students'],
                datasets: [{
                    data: values,
                    backgroundColor: ['#8b5cf6', '#3b9aed', '#10b981'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: { position: 'bottom', labels: { padding: 20, usePointStyle: true } }
                }
            }
        });
    }
    
    // Subject Performance Chart (for students)
    const perfChart = document.getElementById('performanceChart');
    if (perfChart && perfChart.hasAttribute('data-subjects')) {
        const subjects = JSON.parse(perfChart.getAttribute('data-subjects'));
        const scores = JSON.parse(perfChart.getAttribute('data-scores'));
        
        new Chart(perfChart, {
            type: 'bar',
            data: {
                labels: subjects,
                datasets: [{
                    label: 'Score (%)',
                    data: scores,
                    backgroundColor: scores.map(s => s >= 70 ? '#10b981' : s >= 40 ? '#f59e0b' : '#ef4444'),
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, max: 100, grid: { color: '#f1f5f9' } },
                    x: { grid: { display: false } }
                }
            }
        });
    }
}

// ========== AJAX HELPERS ==========
async function fetchJSON(url, options = {}) {
    const response = await fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        ...options
    });
    return response.json();
}

async function postForm(url, formData) {
    const response = await fetch(url, {
        method: 'POST',
        body: formData
    });
    return response;
}
