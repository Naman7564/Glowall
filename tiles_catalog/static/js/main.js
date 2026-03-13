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
});

/**
 * Navigation
 */
function initNavigation() {
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    
    // Mobile menu toggle
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
            this.classList.toggle('active');
        });
    }
    
    // Close menu on click outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.navbar')) {
            navMenu?.classList.remove('active');
            navToggle?.classList.remove('active');
        }
    });
    
    // Header scroll effect
    const header = document.querySelector('.header');
    let lastScroll = 0;
    
    window.addEventListener('scroll', function() {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll > 100) {
            header?.classList.add('scrolled');
        } else {
            header?.classList.remove('scrolled');
        }
        
        lastScroll = currentScroll;
    });
}

/**
 * Search Overlay
 */
function initSearch() {
    const searchToggle = document.querySelector('.search-toggle');
    const searchOverlay = document.querySelector('.search-overlay');
    const searchClose = document.querySelector('.search-close');
    const searchInput = document.querySelector('.search-input');
    
    if (searchToggle && searchOverlay) {
        searchToggle.addEventListener('click', function() {
            searchOverlay.classList.add('active');
            searchInput?.focus();
        });
    }
    
    if (searchClose) {
        searchClose.addEventListener('click', function() {
            searchOverlay?.classList.remove('active');
        });
    }
    
    // Close on escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            searchOverlay?.classList.remove('active');
        }
    });
    
    // Close on overlay click
    searchOverlay?.addEventListener('click', function(e) {
        if (e.target === searchOverlay) {
            searchOverlay.classList.remove('active');
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
