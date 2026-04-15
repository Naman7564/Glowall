/**
 * Glowall - Main JavaScript
 * Premium Tiles & Marble Showroom
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all components
    initNavigation();
    initSearch();
    initAlerts();
    initLazyLoading();
    initScrollEffects();
    initReviewCarousel();
    initPosterCarousel();
    initUserMenu();
    initMobileFilters();
    initViewToggle();
});

/**
 * Navigation
 */
function initNavigation() {
    const header = document.querySelector('.header');
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    const navLinks = navMenu?.querySelectorAll('.nav-link') || [];
    const mobileMenuQuery = window.matchMedia('(max-width: 1024px)');

    const closeMenu = () => {
        navMenu?.classList.remove('active');
        navToggle?.classList.remove('active');
        navToggle?.setAttribute('aria-expanded', 'false');
        document.body.classList.remove('nav-open');
    };

    const openMenu = () => {
        navMenu?.classList.add('active');
        navToggle?.classList.add('active');
        navToggle?.setAttribute('aria-expanded', 'true');

        if (mobileMenuQuery.matches) {
            document.body.classList.add('nav-open');
        }
    };

    const updateHeaderState = () => {
        if (window.scrollY > 16) {
            header?.classList.add('scrolled');
        } else {
            header?.classList.remove('scrolled');
        }
    };

    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function(e) {
            e.stopPropagation();

            if (navMenu.classList.contains('active')) {
                closeMenu();
            } else {
                openMenu();
            }
        });

        navLinks.forEach((link) => {
            link.addEventListener('click', function() {
                if (mobileMenuQuery.matches) {
                    closeMenu();
                }
            });
        });
    }

    document.addEventListener('click', function(e) {
        if (!e.target.closest('.navbar')) {
            closeMenu();
        }
    });

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeMenu();
        }
    });

    const handleMenuBreakpointChange = function() {
        closeMenu();
    };

    if (typeof mobileMenuQuery.addEventListener === 'function') {
        mobileMenuQuery.addEventListener('change', handleMenuBreakpointChange);
    } else {
        mobileMenuQuery.addListener(handleMenuBreakpointChange);
    }

    updateHeaderState();
    window.addEventListener('scroll', updateHeaderState, { passive: true });
}

/**
 * Search Overlay
 */
function initSearch() {
    const SEARCH_DEBOUNCE_MS = 220;
    const MIN_QUERY_LENGTH = 2;
    const header = document.querySelector('.header');
    const searchToggle = document.querySelector('.search-toggle');
    const searchOverlay = document.querySelector('.search-overlay');
    const searchClose = document.querySelector('.search-close');
    const overlayInput = searchOverlay?.querySelector('.js-search-input');
    const searchForms = document.querySelectorAll('.js-search-form');
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

    const openOverlay = () => {
        if (!searchOverlay) {
            return;
        }

        searchOverlay.hidden = false;
        searchOverlay.classList.add('active');
        searchOverlay.setAttribute('aria-hidden', 'false');
        searchToggle?.setAttribute('aria-expanded', 'true');

        const headerOffset = header ? header.getBoundingClientRect().height + 16 : 0;
        const searchTop = searchOverlay.getBoundingClientRect().top + window.scrollY - headerOffset;

        window.scrollTo({
            top: Math.max(searchTop, 0),
            behavior: prefersReducedMotion.matches ? 'auto' : 'smooth',
        });

        window.setTimeout(() => {
            overlayInput?.focus();
        }, prefersReducedMotion.matches ? 0 : 180);
    };

    const closeOverlay = () => {
        if (!searchOverlay) {
            return;
        }

        searchOverlay.classList.remove('active');
        searchOverlay.setAttribute('aria-hidden', 'true');
        searchOverlay.hidden = true;
        searchToggle?.setAttribute('aria-expanded', 'false');
    };

    const createResultItem = (result) => {
        const resultLink = document.createElement('a');
        const resultCopy = document.createElement('div');
        const resultTitle = document.createElement('span');
        const resultMeta = document.createElement('div');
        const resultArrow = document.createElement('span');
        const categoryTag = document.createElement('span');

        resultLink.className = 'search-result';
        resultLink.href = result.url || `/products/${result.slug}/`;

        resultCopy.className = 'search-result-copy';
        resultTitle.className = 'search-result-title';
        resultMeta.className = 'search-result-meta';
        resultArrow.className = 'search-result-arrow';

        resultTitle.textContent = result.name || 'View product';
        categoryTag.textContent = result.category || 'Collection';
        resultMeta.appendChild(categoryTag);

        resultArrow.innerHTML = '<i class="fas fa-arrow-right"></i>';

        resultCopy.appendChild(resultTitle);
        resultCopy.appendChild(resultMeta);
        resultLink.appendChild(resultCopy);
        resultLink.appendChild(resultArrow);

        return resultLink;
    };

    const initSearchForm = (form) => {
        const input = form.querySelector('.js-search-input');
        const clearButton = form.querySelector('.js-search-clear');
        const panel = form.querySelector('.js-search-panel');
        const resultsSection = form.querySelector('.js-search-results-section');
        const resultsList = form.querySelector('.js-search-results');
        const status = form.querySelector('.js-search-status');
        const persistentPanel = form.dataset.panelMode === 'persistent';
        const searchUrl = form.dataset.searchUrl;
        const emptyMessage = Object.prototype.hasOwnProperty.call(form.dataset, 'emptyMessage')
            ? form.dataset.emptyMessage
            : status?.textContent.trim() || '';
        let debounceTimer = null;
        let requestController = null;

        if (!input) {
            return;
        }

        const updateClearButton = () => {
            clearButton?.classList.toggle('visible', input.value.trim().length > 0);
        };

        const setStatus = (message, state = 'idle') => {
            if (!status) {
                return;
            }

            status.textContent = message;
            status.dataset.state = state;
            status.hidden = !message;
        };

        const clearResults = () => {
            if (resultsList) {
                resultsList.innerHTML = '';
            }

            if (resultsSection) {
                resultsSection.hidden = true;
            }
        };

        const cancelPendingSearch = () => {
            window.clearTimeout(debounceTimer);

            if (requestController) {
                requestController.abort();
                requestController = null;
            }
        };

        const syncPanelVisibility = () => {
            if (!panel) {
                return;
            }

            const hasResults = resultsSection ? !resultsSection.hidden : false;
            const hasStatus = status ? !status.hidden : false;
            const shouldShowPanel = persistentPanel
                ? hasResults || hasStatus
                : form.contains(document.activeElement) || hasResults;
            panel.hidden = !shouldShowPanel;
        };

        const showIdleState = () => {
            cancelPendingSearch();
            clearResults();
            setStatus(emptyMessage, 'idle');
            syncPanelVisibility();
        };

        const renderResults = (results, query) => {
            clearResults();

            if (!resultsList || !resultsSection) {
                return;
            }

            if (!results.length) {
                setStatus(`No quick matches for "${query}". Press search to browse all results.`, 'idle');
                syncPanelVisibility();
                return;
            }

            results.forEach((result) => {
                resultsList.appendChild(createResultItem(result));
            });

            resultsSection.hidden = false;
            setStatus('Select a product or press search to see the full catalog results.', 'idle');
            syncPanelVisibility();
        };

        const fetchSuggestions = async (query) => {
            if (!searchUrl) {
                return;
            }

            if (typeof AbortController === 'function') {
                requestController = new AbortController();
            } else {
                requestController = null;
            }

            try {
                const requestUrl = new URL(searchUrl, window.location.origin);
                const requestOptions = {};

                requestUrl.searchParams.set('q', query);

                if (requestController) {
                    requestOptions.signal = requestController.signal;
                }

                const response = await fetch(requestUrl.toString(), requestOptions);

                if (!response.ok) {
                    throw new Error(`Search request failed with status ${response.status}`);
                }

                const data = await response.json();

                if (input.value.trim() !== query) {
                    return;
                }

                requestController = null;
                renderResults(Array.isArray(data.results) ? data.results : [], query);
            } catch (error) {
                if (error.name === 'AbortError') {
                    return;
                }

                requestController = null;
                clearResults();
                setStatus('Suggestions are unavailable right now.', 'error');
                syncPanelVisibility();
            }
        };

        function queueSuggestions(query) {
            const normalizedQuery = query.trim();

            cancelPendingSearch();

            if (normalizedQuery.length < MIN_QUERY_LENGTH) {
                clearResults();
                setStatus(emptyMessage, 'idle');
                syncPanelVisibility();
                return;
            }

            setStatus('Searching the collection...', 'loading');
            syncPanelVisibility();
            debounceTimer = window.setTimeout(() => {
                fetchSuggestions(normalizedQuery);
            }, SEARCH_DEBOUNCE_MS);
        }

        clearButton?.addEventListener('click', function() {
            input.value = '';
            updateClearButton();
            showIdleState();
            input.focus();
        });

        input.addEventListener('focus', function() {
            if (input.value.trim().length >= MIN_QUERY_LENGTH) {
                queueSuggestions(input.value);
            } else {
                setStatus(emptyMessage, 'idle');
                syncPanelVisibility();
            }
        });

        input.addEventListener('input', function() {
            updateClearButton();
            queueSuggestions(input.value);
        });

        input.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && input.value.trim()) {
                e.stopPropagation();
                input.value = '';
                updateClearButton();
                showIdleState();
            }
        });

        form.addEventListener('focusout', function() {
            window.setTimeout(() => {
                if (persistentPanel || form.contains(document.activeElement)) {
                    return;
                }

                cancelPendingSearch();
                clearResults();

                if (!input.value.trim()) {
                    setStatus(emptyMessage, 'idle');
                }

                syncPanelVisibility();
            }, 120);
        });

        updateClearButton();

        if (persistentPanel) {
            setStatus(emptyMessage, 'idle');
            syncPanelVisibility();
        }
    };

    searchForms.forEach((form) => {
        initSearchForm(form);
    });

    if (searchToggle && searchOverlay) {
        searchToggle.addEventListener('click', function() {
            if (searchOverlay.hidden) {
                openOverlay();
            } else {
                closeOverlay();
            }
        });
    }

    if (searchClose) {
        searchClose.addEventListener('click', function() {
            closeOverlay();
        });
    }

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeOverlay();
        }
    });

    searchOverlay?.addEventListener('click', function(e) {
        if (e.target === searchOverlay) {
            closeOverlay();
        }
    });
}

/**
 * Alerts
 */
function initAlerts() {
    const alerts = document.querySelectorAll('.alert');
    
    alerts.forEach(alert => {
        const closeBtn = alert.querySelector('.alert-close');
        
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                alert.style.animation = 'slideOut 0.3s ease forwards';
                setTimeout(() => alert.remove(), 300);
            });
        }
        
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
 * Lazy Loading Images
 */
function initLazyLoading() {
    const lazyImages = document.querySelectorAll('img[loading="lazy"]');
    
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src || img.src;
                    img.classList.add('loaded');
                    observer.unobserve(img);
                }
            });
        });
        
        lazyImages.forEach(img => imageObserver.observe(img));
    }
}

/**
 * Scroll Effects
 */
function initScrollEffects() {
    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href !== '#') {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });
    
    // Animate elements on scroll
    const animateElements = document.querySelectorAll('.animate-on-scroll');
    
    if ('IntersectionObserver' in window) {
        const animateObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animated');
                }
            });
        }, { threshold: 0.1 });
        
        animateElements.forEach(el => animateObserver.observe(el));
    }
}

/**
 * Poster Carousel (Hero Section)
 */
function initPosterCarousel() {
    const carousels = document.querySelectorAll('[data-poster-carousel]');

    carousels.forEach((carousel) => {
        const track = carousel.querySelector('[data-carousel-track]');
        const slides = Array.from(carousel.querySelectorAll('[data-carousel-slide]'));
        const prevBtn = carousel.querySelector('[data-carousel-prev]');
        const nextBtn = carousel.querySelector('[data-carousel-next]');
        const dotsWrap = carousel.querySelector('[data-carousel-dots]');
        const autoplayDelay = Number(carousel.dataset.autoplayDelay || 5000);

        if (!track || slides.length === 0) {
            return;
        }

        let currentIndex = 0;
        let autoplayId = null;

        const renderDots = () => {
            if (!dotsWrap) {
                return;
            }

            dotsWrap.innerHTML = '';

            for (let index = 0; index < slides.length; index += 1) {
                const dot = document.createElement('button');
                dot.type = 'button';
                dot.className = `carousel-dot${index === currentIndex ? ' active' : ''}`;
                dot.setAttribute('aria-label', `Go to slide ${index + 1}`);
                dot.addEventListener('click', () => {
                    currentIndex = index;
                    updateCarousel();
                    restartAutoplay();
                });
                dotsWrap.appendChild(dot);
            }
        };

        const updateButtons = () => {
            const disabled = slides.length <= 1;
            if (prevBtn) {
                prevBtn.disabled = disabled;
            }
            if (nextBtn) {
                nextBtn.disabled = disabled;
            }
        };

        const updateCarousel = () => {
            const offset = slides[0].offsetWidth * currentIndex;
            track.style.transform = `translateX(-${offset}px)`;

            updateButtons();
            renderDots();
        };

        const goToNext = () => {
            currentIndex = currentIndex >= slides.length - 1 ? 0 : currentIndex + 1;
            updateCarousel();
        };

        const goToPrev = () => {
            currentIndex = currentIndex <= 0 ? slides.length - 1 : currentIndex - 1;
            updateCarousel();
        };

        const stopAutoplay = () => {
            if (autoplayId) {
                window.clearInterval(autoplayId);
                autoplayId = null;
            }
        };

        const startAutoplay = () => {
            stopAutoplay();
            if (slides.length <= 1) {
                return;
            }
            autoplayId = window.setInterval(goToNext, autoplayDelay);
        };

        const restartAutoplay = () => {
            startAutoplay();
        };

        prevBtn?.addEventListener('click', () => {
            goToPrev();
            restartAutoplay();
        });

        nextBtn?.addEventListener('click', () => {
            goToNext();
            restartAutoplay();
        });

        carousel.addEventListener('mouseenter', stopAutoplay);
        carousel.addEventListener('mouseleave', startAutoplay);

        updateCarousel();
        startAutoplay();
    });
}

/**
 * Customer Review Carousel
 */
function initReviewCarousel() {
    const carousels = document.querySelectorAll('[data-review-carousel]');

    carousels.forEach((carousel) => {
        const track = carousel.querySelector('[data-carousel-track]');
        const slides = Array.from(carousel.querySelectorAll('[data-carousel-slide]'));
        const prevBtn = carousel.querySelector('[data-carousel-prev]');
        const nextBtn = carousel.querySelector('[data-carousel-next]');
        const dotsWrap = carousel.querySelector('[data-carousel-dots]');
        const autoplayDelay = Number(carousel.dataset.autoplayDelay || 4500);

        if (!track || slides.length === 0) {
            return;
        }

        let currentIndex = 0;
        let slidesPerView = window.innerWidth <= 768 ? 1 : 3;
        let autoplayId = null;

        const getMaxIndex = () => Math.max(slides.length - slidesPerView, 0);

        const renderDots = () => {
            if (!dotsWrap) {
                return;
            }

            const dotCount = getMaxIndex() + 1;
            dotsWrap.innerHTML = '';

            for (let index = 0; index < dotCount; index += 1) {
                const dot = document.createElement('button');
                dot.type = 'button';
                dot.className = `reviews-dot${index === currentIndex ? ' active' : ''}`;
                dot.setAttribute('aria-label', `Go to review group ${index + 1}`);
                dot.addEventListener('click', () => {
                    currentIndex = index;
                    updateCarousel();
                    restartAutoplay();
                });
                dotsWrap.appendChild(dot);
            }
        };

        const updateButtons = () => {
            const disabled = getMaxIndex() === 0;
            if (prevBtn) {
                prevBtn.disabled = disabled;
            }
            if (nextBtn) {
                nextBtn.disabled = disabled;
            }
        };

        const updateCarousel = () => {
            slidesPerView = window.innerWidth <= 768 ? 1 : 3;
            currentIndex = Math.min(currentIndex, getMaxIndex());

            const firstSlide = slides[0];
            const gap = Number.parseFloat(window.getComputedStyle(track).gap || '0');
            const offset = (firstSlide.offsetWidth + gap) * currentIndex;
            track.style.transform = `translateX(-${offset}px)`;

            updateButtons();
            renderDots();
        };

        const goToNext = () => {
            const maxIndex = getMaxIndex();
            currentIndex = currentIndex >= maxIndex ? 0 : currentIndex + 1;
            updateCarousel();
        };

        const goToPrev = () => {
            const maxIndex = getMaxIndex();
            currentIndex = currentIndex <= 0 ? maxIndex : currentIndex - 1;
            updateCarousel();
        };

        const stopAutoplay = () => {
            if (autoplayId) {
                window.clearInterval(autoplayId);
                autoplayId = null;
            }
        };

        const startAutoplay = () => {
            stopAutoplay();
            if (slides.length <= slidesPerView) {
                return;
            }
            autoplayId = window.setInterval(goToNext, autoplayDelay);
        };

        const restartAutoplay = () => {
            startAutoplay();
        };

        prevBtn?.addEventListener('click', () => {
            goToPrev();
            restartAutoplay();
        });

        nextBtn?.addEventListener('click', () => {
            goToNext();
            restartAutoplay();
        });

        carousel.addEventListener('mouseenter', stopAutoplay);
        carousel.addEventListener('mouseleave', startAutoplay);
        window.addEventListener('resize', debounce(updateCarousel, 150));

        updateCarousel();
        startAutoplay();
    });
}

/**
 * Image Gallery (Product Detail)
 */
function changeImage(src) {
    const mainImage = document.getElementById('mainImage');
    if (mainImage) {
        mainImage.src = src;
        
        // Update active state
        document.querySelectorAll('.thumb-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        event.currentTarget.classList.add('active');
    }
}

/**
 * Form Validation
 */
function validateForm(form) {
    const inputs = form.querySelectorAll('[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            isValid = false;
            input.classList.add('error');
        } else {
            input.classList.remove('error');
        }
    });
    
    return isValid;
}

/**
 * Debounce Function
 */
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

/**
 * Format Currency
 */
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
}

// Add CSS animation for alerts
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

/**
 * User Menu Dropdown
 */
function initUserMenu() {
    const toggle = document.getElementById('user-menu-toggle');
    const dropdown = document.getElementById('user-dropdown');

    if (!toggle || !dropdown) return;

    toggle.addEventListener('click', function(e) {
        e.stopPropagation();
        dropdown.classList.toggle('active');
    });

    document.addEventListener('click', function(e) {
        if (!e.target.closest('#user-menu')) {
            dropdown.classList.remove('active');
        }
    });

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            dropdown.classList.remove('active');
        }
    });
}

/**
 * Mobile Filters Sidebar
 */
function initMobileFilters() {
    const filterBtn = document.getElementById('mobile-filter-btn');
    const filterSidebar = document.getElementById('filter-sidebar');
    const filterOverlay = document.getElementById('filter-overlay');
    const filterCloseBtn = document.getElementById('filter-close-btn');

    if (!filterBtn || !filterSidebar) return;

    const openFilters = () => {
        filterSidebar.classList.add('active');
        if (filterOverlay) filterOverlay.classList.add('active');
        document.body.classList.add('filter-open');
    };

    const closeFilters = () => {
        filterSidebar.classList.remove('active');
        if (filterOverlay) filterOverlay.classList.remove('active');
        document.body.classList.remove('filter-open');
    };

    filterBtn.addEventListener('click', openFilters);

    if (filterCloseBtn) {
        filterCloseBtn.addEventListener('click', closeFilters);
    }

    if (filterOverlay) {
        filterOverlay.addEventListener('click', closeFilters);
    }

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && filterSidebar.classList.contains('active')) {
            closeFilters();
        }
    });

    // Close filters on resize if viewport becomes desktop
    const mediaQuery = window.matchMedia('(min-width: 1024px)');
    const handleResize = (e) => {
        if (e.matches) {
            closeFilters();
        }
    };

    if (typeof mediaQuery.addEventListener === 'function') {
        mediaQuery.addEventListener('change', handleResize);
    } else {
        mediaQuery.addListener(handleResize);
    }
}

/**
 * View Toggle (Grid/List)
 */
function initViewToggle() {
    const viewBtns = document.querySelectorAll('.view-btn-toggle');
    const productsGrid = document.querySelector('.products-grid-modern');

    if (!viewBtns.length || !productsGrid) return;

    viewBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const view = this.dataset.view;

            viewBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            if (view === 'list') {
                productsGrid.classList.add('list-view');
            } else {
                productsGrid.classList.remove('list-view');
            }

            // Store preference in localStorage
            try {
                localStorage.setItem('glowallProductView', view);
            } catch (e) {
                // Ignore storage errors
            }
        });
    });

    // Restore saved preference
    try {
        const savedView = localStorage.getItem('glowallProductView');
        if (savedView === 'list') {
            const listBtn = document.querySelector('.view-btn-toggle[data-view="list"]');
            if (listBtn) {
                listBtn.click();
            }
        }
    } catch (e) {
        // Ignore storage errors
    }
}
