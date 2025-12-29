// Custom Video Player
document.addEventListener('DOMContentLoaded', function() {
    const videoElements = document.querySelectorAll('.post-content video');

    videoElements.forEach(video => {
        const wrapper = document.createElement('div');
        wrapper.className = 'video-player';

        // Get metadata from data attributes
        const title = video.getAttribute('data-title') || 'Bez tytułu';

        // Build player HTML
        let playerHTML = `
        <div class="video-player-title">${title}</div>
        <div class="video-player-fullscreen-wrapper">
            <div class="video-player-screen">
            </div>
            <div class="video-controls">
                <div class="video-progress-container">
                    <span class="video-time video-current">0:00</span>
                    <div class="video-progress media-progress">
                        <div class="video-progress-bar media-progress-bar"></div>
                    </div>
                    <span class="video-time video-duration">0:00</span>
                </div>
                <div class="video-buttons">
                    <div class="video-volume-container">
                        <button class="video-volume-icon-btn" aria-label="Mute">
                            <img src="/static/images/icons/volume-high.svg" class="video-volume-icon" alt="Volume">
                        </button>
                        <div class="video-volume-track media-volume-track">
                            <input type="range" class="video-volume media-volume-slider" min="0" max="100" value="100">
                            <div class="video-volume-bar media-volume-bar"></div>
                        </div>
                    </div>
                    <button class="video-button video-play-pause" aria-label="Play">
                        <img src="/static/images/icons/play.svg" class="video-play-icon" alt="Play">
                    </button>
                    <a class="video-button video-download" download aria-label="Download">
                        <img src="/static/images/icons/download.svg" class="video-download-icon" alt="Download">
                    </a>
                    <button class="video-button video-fullscreen" aria-label="Fullscreen">
                        <img src="/static/images/icons/fullscreen.svg" class="video-fullscreen-icon" alt="Fullscreen">
                    </button>
                </div>
            </div>
        </div>`;

        wrapper.innerHTML = playerHTML;
        video.parentNode.insertBefore(wrapper, video);

        // Move video into the screen container
        const screen = wrapper.querySelector('.video-player-screen');
        screen.appendChild(video);

        // Get fullscreen wrapper
        const fullscreenWrapper = wrapper.querySelector('.video-player-fullscreen-wrapper');

        // Get elements
        const playBtn = wrapper.querySelector('.video-play-pause');
        const playIcon = wrapper.querySelector('.video-play-icon');
        const progressBar = wrapper.querySelector('.video-progress-bar');
        const progress = wrapper.querySelector('.video-progress');
        const currentTime = wrapper.querySelector('.video-current');
        const duration = wrapper.querySelector('.video-duration');
        const volumeSlider = wrapper.querySelector('.video-volume');
        const volumeIconBtn = wrapper.querySelector('.video-volume-icon-btn');
        const volumeIcon = wrapper.querySelector('.video-volume-icon');
        const volumeBar = wrapper.querySelector('.video-volume-bar');
        const downloadBtn = wrapper.querySelector('.video-download');
        const fullscreenBtn = wrapper.querySelector('.video-fullscreen');
        const fullscreenIcon = wrapper.querySelector('.video-fullscreen-icon');
        const videoControls = wrapper.querySelector('.video-controls');

        // Touch/tap handling for showing controls in fullscreen
        let controlsHideTimer = null;

        const showControls = () => {
            videoControls.classList.add('active');

            // Clear existing timer
            if (controlsHideTimer) {
                clearTimeout(controlsHideTimer);
            }

            // Check if volume slider is revealed, if so don't start the hide timer
            const volumeContainer = wrapper.querySelector('.video-volume-container');
            if (volumeContainer && volumeContainer.classList.contains('volume-revealed')) {
                return;
            }

            // Only hide controls if video is playing
            // If paused or ended, keep controls visible
            if (!video.paused && !video.ended) {
                // Hide controls after 3 seconds of inactivity
                controlsHideTimer = setTimeout(() => {
                    videoControls.classList.remove('active');
                }, 3000);
            }
        };

        const hideControls = () => {
            videoControls.classList.remove('active');
            if (controlsHideTimer) {
                clearTimeout(controlsHideTimer);
            }
        };

        // Show controls on any interaction
        fullscreenWrapper.addEventListener('touchstart', showControls);
        fullscreenWrapper.addEventListener('click', (e) => {
            // Only trigger if not clicking on a control element
            if (e.target === fullscreenWrapper || e.target === screen || e.target === video) {
                showControls();
            }
        });
        fullscreenWrapper.addEventListener('mousemove', showControls);

        // Show controls when entering/exiting fullscreen
        const showControlsOnFullscreen = () => {
            // Always show controls briefly when toggling fullscreen
            showControls();
        };

        // Show controls initially on load
        showControls();

        // Listen for play/pause events to manage control visibility
        video.addEventListener('play', () => {
            // When video starts playing, restart the hide timer
            showControls();
        });

        video.addEventListener('pause', () => {
            // When video is paused, show controls and keep them visible
            videoControls.classList.add('active');
            if (controlsHideTimer) {
                clearTimeout(controlsHideTimer);
                controlsHideTimer = null;
            }
        });

        video.addEventListener('ended', () => {
            // When video ends, show controls and keep them visible
            videoControls.classList.add('active');
            if (controlsHideTimer) {
                clearTimeout(controlsHideTimer);
                controlsHideTimer = null;
            }
        });

        let previousVolume = 100;

        // Seek by dragging (mouse and touch)
        let isDragging = false;
        let touchUsed = false;
        const isDraggingGetter = () => isDragging;

        // Set download link using shared utility
        MediaPlayerUtils.setupDownload(video, downloadBtn);

        // Setup time update using shared utility
        MediaPlayerUtils.setupTimeUpdate(video, progressBar, progress, currentTime, isDraggingGetter);

        // Setup duration display using shared utility
        MediaPlayerUtils.setupDurationDisplay(video, duration);

        // Play/Pause
        const togglePlayPause = () => {
            // Store current scroll position
            const scrollX = window.scrollX || window.pageXOffset;
            const scrollY = window.scrollY || window.pageYOffset;

            if (video.paused) {
                video.play().catch(() => {});
                playIcon.src = '/static/images/icons/pause.svg';
                playIcon.alt = 'Pause';
                playBtn.setAttribute('aria-label', 'Pause');
            } else {
                video.pause();
                playIcon.src = '/static/images/icons/play.svg';
                playIcon.alt = 'Play';
                playBtn.setAttribute('aria-label', 'Play');
            }

            // Restore scroll position if it changed
            requestAnimationFrame(() => {
                if (window.scrollX !== scrollX || window.scrollY !== scrollY) {
                    window.scrollTo(scrollX, scrollY);
                }
            });
        };

        playBtn.addEventListener('click', togglePlayPause);
        video.addEventListener('click', togglePlayPause);

        // Make clicking on empty areas of controls also toggle play/pause
        videoControls.addEventListener('click', (e) => {
            // Only toggle if clicking on the controls container itself or progress/time elements
            // Don't toggle if clicking on buttons or interactive elements
            const isButton = e.target.closest('button, a, input');
            const isProgressBar = e.target.closest('.video-progress');

            if (!isButton && !isProgressBar) {
                togglePlayPause();
            }
        });

        // Make clicking on video screen background (letterboxing/pillarboxing) also toggle play/pause
        screen.addEventListener('click', (e) => {
            // Only toggle if clicking on the screen itself, not the video
            if (e.target === screen) {
                togglePlayPause();
            }
        });

        // Reset on end
        video.addEventListener('ended', () => {
            playIcon.src = '/static/images/icons/play.svg';
            playIcon.alt = 'Play';
            playBtn.setAttribute('aria-label', 'Play');
            progressBar.style.width = '0%';
        });

        const seek = (e) => {
            const rect = progress.getBoundingClientRect();
            const clientX = e.type.includes('touch') ?
                (e.touches && e.touches.length > 0 ? e.touches[0].clientX : e.changedTouches[0].clientX) :
                e.clientX;
            const percent = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
            const newTime = percent * video.duration;

            // Update both video time and visual progress immediately
            video.currentTime = newTime;
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
                    video.currentTime = percent * video.duration;
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
            video.volume = volumeLevel;
            volumeBar.style.width = value + '%';
            wrapper.querySelector('.video-volume-track').style.setProperty('--volume-percent', value + '%');
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

        // Detect if device has hover capability
        const hasHover = window.matchMedia('(hover: hover) and (pointer: fine)').matches;

        // Track active outside click listener for cleanup
        let outsideClickListener = null;

        // Prevent volume container interactions from triggering showControls
        const volumeContainer = wrapper.querySelector('.video-volume-container');
        volumeContainer.addEventListener('click', (e) => {
            e.stopPropagation();
        });
        volumeContainer.addEventListener('touchstart', (e) => {
            e.stopPropagation();
        });

        // Volume icon click behavior
        volumeIconBtn.addEventListener('click', (e) => {
            const volumeContainer = wrapper.querySelector('.video-volume-container');

            // On PC/hover-capable devices: always mute/unmute immediately
            if (hasHover) {
                if (video.volume > 0) {
                    updateVolume(0, false);
                } else {
                    updateVolume(previousVolume, false);
                }
                return;
            }

            // On touch devices: first tap shows slider, second tap mutes/unmutes
            e.stopPropagation();
            e.preventDefault();

            const isRevealed = volumeContainer.classList.contains('volume-revealed');

            if (!isRevealed) {
                // First tap: Show the slider
                volumeContainer.classList.add('volume-revealed');

                // Stop the controls hide timer while volume slider is open
                if (controlsHideTimer) {
                    clearTimeout(controlsHideTimer);
                    controlsHideTimer = null;
                }

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
                        // Restart the controls hide timer after volume slider is hidden
                        showControls();
                    }
                };

                // Add listener on next tick to avoid immediate trigger
                setTimeout(() => {
                    document.addEventListener('click', outsideClickListener);
                }, 10);
            } else {
                // Second tap: Mute/unmute
                if (video.volume > 0) {
                    updateVolume(0, false);
                } else {
                    updateVolume(previousVolume, false);
                }
            }

            // Remove focus from button
            setTimeout(() => volumeIconBtn.blur(), 100);
        });

        // Fullscreen functionality
        fullscreenBtn.addEventListener('click', () => {
            if (!document.fullscreenElement && !document.webkitFullscreenElement &&
                !document.mozFullScreenElement && !document.msFullscreenElement) {
                // Enter fullscreen on the wrapper (contains both video and controls)
                if (fullscreenWrapper.requestFullscreen) {
                    fullscreenWrapper.requestFullscreen();
                } else if (fullscreenWrapper.webkitRequestFullscreen) {
                    fullscreenWrapper.webkitRequestFullscreen();
                } else if (fullscreenWrapper.mozRequestFullScreen) {
                    fullscreenWrapper.mozRequestFullScreen();
                } else if (fullscreenWrapper.msRequestFullscreen) {
                    fullscreenWrapper.msRequestFullscreen();
                }
            } else {
                // Exit fullscreen
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                } else if (document.webkitExitFullscreen) {
                    document.webkitExitFullscreen();
                } else if (document.mozCancelFullScreen) {
                    document.mozCancelFullScreen();
                } else if (document.msExitFullscreen) {
                    document.msExitFullscreen();
                }
            }
        });

        // Listen for fullscreen changes to update icon
        const updateFullscreenIcon = () => {
            if (document.fullscreenElement === fullscreenWrapper || document.webkitFullscreenElement === fullscreenWrapper ||
                document.mozFullScreenElement === fullscreenWrapper || document.msFullscreenElement === fullscreenWrapper) {
                fullscreenIcon.src = '/static/images/icons/fullscreen-exit.svg';
                fullscreenIcon.alt = 'Exit Fullscreen';
                fullscreenBtn.setAttribute('aria-label', 'Exit Fullscreen');
                fullscreenWrapper.classList.add('is-fullscreen');
                showControlsOnFullscreen();
            } else {
                fullscreenIcon.src = '/static/images/icons/fullscreen.svg';
                fullscreenIcon.alt = 'Fullscreen';
                fullscreenBtn.setAttribute('aria-label', 'Fullscreen');
                fullscreenWrapper.classList.remove('is-fullscreen');
                showControlsOnFullscreen();
            }
        };

        document.addEventListener('fullscreenchange', updateFullscreenIcon);
        document.addEventListener('webkitfullscreenchange', updateFullscreenIcon);
        document.addEventListener('mozfullscreenchange', updateFullscreenIcon);
        document.addEventListener('msfullscreenchange', updateFullscreenIcon);

        // Initialize volume bar
        updateVolume(volumeSlider.value);
    });
});
