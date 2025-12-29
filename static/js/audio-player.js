// Custom Audio Player
document.addEventListener('DOMContentLoaded', function() {
    const audioElements = document.querySelectorAll('.post-content audio');

    audioElements.forEach(audio => {
        const wrapper = document.createElement('div');
        wrapper.className = 'audio-player';

        // Get metadata from data attributes
        const title = audio.getAttribute('data-title') || 'Bez tytułu';
        const artist = audio.getAttribute('data-artist') || 'Nieznany wykonawca';
        const albumArt = audio.getAttribute('data-artwork');

        // Build player HTML
        let playerHTML = '';

        if (albumArt) {
            playerHTML += `<div class="audio-album-art"><img src="${albumArt}" alt="${title}"></div>`;
        }

        playerHTML += `
        <div class="audio-player-info">
            <div class="audio-metadata">
                <div class="audio-title">${title}</div>
                <div class="audio-artist">${artist}</div>
            </div>
        </div>
        <div class="audio-controls">
            <div class="audio-progress-container">
                <span class="audio-time audio-current">0:00</span>
                <div class="audio-progress media-progress">
                    <div class="audio-progress-bar media-progress-bar"></div>
                </div>
                <span class="audio-time audio-duration">0:00</span>
            </div>
            <div class="audio-buttons">
                <div class="audio-volume-container">
                    <button class="audio-volume-icon-btn" aria-label="Mute">
                        <img src="/static/images/icons/volume-high.svg" class="audio-volume-icon" alt="Volume">
                    </button>
                    <div class="audio-volume-track media-volume-track">
                        <input type="range" class="audio-volume media-volume-slider" min="0" max="100" value="100">
                        <div class="audio-volume-bar media-volume-bar"></div>
                    </div>
                </div>
                <button class="audio-button audio-play-pause" aria-label="Play">
                    <img src="/static/images/icons/play.svg" class="audio-play-icon" alt="Play">
                </button>
                <a class="audio-button audio-download" download aria-label="Download">
                    <img src="/static/images/icons/download.svg" class="audio-download-icon" alt="Download">
                </a>
            </div>
        </div>`;

        wrapper.innerHTML = playerHTML;
        audio.parentNode.insertBefore(wrapper, audio);
        wrapper.appendChild(audio);

        // Get elements
        const playBtn = wrapper.querySelector('.audio-play-pause');
        const playIcon = wrapper.querySelector('.audio-play-icon');
        const progressBar = wrapper.querySelector('.audio-progress-bar');
        const progress = wrapper.querySelector('.audio-progress');
        const currentTime = wrapper.querySelector('.audio-current');
        const duration = wrapper.querySelector('.audio-duration');
        const volumeSlider = wrapper.querySelector('.audio-volume');
        const volumeIconBtn = wrapper.querySelector('.audio-volume-icon-btn');
        const volumeIcon = wrapper.querySelector('.audio-volume-icon');
        const volumeBar = wrapper.querySelector('.audio-volume-bar');
        const downloadBtn = wrapper.querySelector('.audio-download');

        let previousVolume = 100;

        // Set download link using shared utility
        MediaPlayerUtils.setupDownload(audio, downloadBtn);

        // Seek by dragging (mouse and touch)
        let isDragging = false;
        let touchUsed = false;
        const isDraggingGetter = () => isDragging;

        // Setup time update using shared utility
        MediaPlayerUtils.setupTimeUpdate(audio, progressBar, progress, currentTime, isDraggingGetter);

        // Setup duration display using shared utility
        MediaPlayerUtils.setupDurationDisplay(audio, duration);

        // Force load metadata
        audio.load();

        // Setup play/pause using shared utility
        MediaPlayerUtils.setupPlayPause(audio, playBtn, playIcon);

        // Reset progress on end
        audio.addEventListener('ended', () => {
            progressBar.style.width = '0%';
        });

        const seek = (e) => {
            const rect = progress.getBoundingClientRect();
            const clientX = e.type.includes('touch') ?
                (e.touches && e.touches.length > 0 ? e.touches[0].clientX : e.changedTouches[0].clientX) :
                e.clientX;
            const percent = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
            const newTime = percent * audio.duration;

            // Update both audio time and visual progress immediately
            audio.currentTime = newTime;
            progressBar.style.width = (percent * 100) + '%';
            progress.style.setProperty('--progress-percent', (percent * 100) + '%');
            currentTime.textContent = MediaPlayerUtils.formatTime(newTime);
        };

        // Seek by clicking (only for mouse, not touch)
        progress.addEventListener('click', (e) => {
            // Ignore click events that come after touch events
            if (touchUsed) {
                touchUsed = false;
                e.preventDefault();
                e.stopPropagation();
                return;
            }

            // Only process if it's a real mouse click with valid coordinates
            if (e.clientX !== undefined && e.clientX !== 0 && e.clientY !== undefined) {
                const rect = progress.getBoundingClientRect();
                const percent = (e.clientX - rect.left) / rect.width;
                if (percent >= 0 && percent <= 1) {
                    audio.currentTime = percent * audio.duration;
                }
            }
        });

        // Mouse events
        progress.addEventListener('mousedown', (e) => {
            isDragging = true;
            seek(e);
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (isDragging) {
                seek(e);
            }
        });

        document.addEventListener('mouseup', () => {
            isDragging = false;
        });

        // Touch events
        progress.addEventListener('touchstart', (e) => {
            touchUsed = true;
            isDragging = true;
            seek(e);
            e.preventDefault();
        });

        document.addEventListener('touchmove', (e) => {
            if (isDragging) {
                seek(e);
                e.preventDefault();
            }
        }, { passive: false });

        document.addEventListener('touchend', () => {
            isDragging = false;
        });

        // Volume control
        const updateVolume = (value, savePrevious = true) => {
            const volumeLevel = value / 100;
            audio.volume = volumeLevel;
            volumeBar.style.width = value + '%';
            wrapper.querySelector('.audio-volume-track').style.setProperty('--volume-percent', value + '%');
            volumeSlider.value = value;

            // Save previous volume (but not if it's 0)
            if (savePrevious && value > 0) {
                previousVolume = value;
            }

            // Update volume icon using shared utility
            MediaPlayerUtils.updateVolumeIcon(value, volumeIcon, volumeIconBtn);
        };

        volumeSlider.addEventListener('input', (e) => {
            updateVolume(e.target.value);
        });

        // Detect if device has hover capability (check both hover and pointer media queries)
        const hasHover = window.matchMedia('(hover: hover) and (pointer: fine)').matches;

        // Track active outside click listener for cleanup
        let outsideClickListener = null;

        // Volume icon click behavior
        volumeIconBtn.addEventListener('click', (e) => {
            const volumeContainer = wrapper.querySelector('.audio-volume-container');
            const volumeTrack = wrapper.querySelector('.audio-volume-track');

            // On PC/hover-capable devices: always mute/unmute immediately
            if (hasHover) {
                if (audio.volume > 0) {
                    updateVolume(0, false);
                } else {
                    updateVolume(previousVolume, false);
                }
                return;
            }

            // On touch devices: first tap shows slider, second tap mutes/unmutes
            // Always prevent propagation to stop outside click handler
            e.stopPropagation();

            // Check if slider is currently revealed by checking the class
            const isRevealed = volumeContainer.classList.contains('volume-revealed');

            if (!isRevealed) {
                // First tap: Show the slider
                volumeContainer.classList.add('volume-revealed');

                // Remove old listener if it exists
                if (outsideClickListener) {
                    document.removeEventListener('click', outsideClickListener);
                }

                // Hide when tapping outside
                outsideClickListener = function(e) {
                    if (!volumeContainer.contains(e.target)) {
                        volumeContainer.classList.remove('volume-revealed');
                        document.removeEventListener('click', outsideClickListener);
                        outsideClickListener = null;
                    }
                };

                // Add listener on next tick to avoid immediate trigger
                setTimeout(() => {
                    document.addEventListener('click', outsideClickListener);
                }, 10);
            } else {
                // Second tap: Mute/unmute (slider is already visible)
                if (audio.volume > 0) {
                    updateVolume(0, false);
                } else {
                    updateVolume(previousVolume, false);
                }
            }

            // Remove focus from button to prevent stuck visual states
            setTimeout(() => volumeIconBtn.blur(), 100);
        });

        // Initialize volume bar
        updateVolume(volumeSlider.value);
    });
});
