// Performance and SEO optimizations
(function() {
    'use strict';
    
    // Preload critical images
    function preloadCriticalImages() {
        const criticalImages = [
            '/static/assets/logo.webp',
            '/static/assets/og-image.png'
        ];
        
        criticalImages.forEach(src => {
            const link = document.createElement('link');
            link.rel = 'preload';
            link.as = 'image';
            link.href = src;
            document.head.appendChild(link);
        });
    }
    
    // Lazy load non-critical resources
    function initLazyLoading() {
        if ('IntersectionObserver' in window) {
            const lazyImages = document.querySelectorAll('img[data-src]');
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        imageObserver.unobserve(img);
                    }
                });
            });
            
            lazyImages.forEach(img => imageObserver.observe(img));
        }
    }
    
    // Optimize scroll performance
    let ticking = false;
    function optimizeScroll() {
        if (!ticking) {
            requestAnimationFrame(() => {
                // Scroll-based optimizations here
                ticking = false;
            });
            ticking = true;
        }
    }
    
    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            preloadCriticalImages();
            initLazyLoading();
            window.addEventListener('scroll', optimizeScroll, { passive: true });
        });
    } else {
        preloadCriticalImages();
        initLazyLoading();
        window.addEventListener('scroll', optimizeScroll, { passive: true });
    }
    
    // Service Worker registration for caching
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/sw.js')
                .then(registration => console.log('SW registered'))
                .catch(err => console.log('SW registration failed'));
        });
    }
})();