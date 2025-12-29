// Initialize GLightbox for image gallery
document.addEventListener('DOMContentLoaded', function() {
    const lightbox = GLightbox({
        selector: '.glightbox',
        touchNavigation: true,
        loop: true,
        autoplayVideos: false,
        skin: 'clean',
        closeButton: true,
        cssEfects: {
            fade: { in: 'fadeIn', out: 'fadeOut' }
        }
    });
});
