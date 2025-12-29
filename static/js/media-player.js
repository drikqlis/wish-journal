/**
 * Shared Media Player Module
 * Provides common functionality for audio and video players
 */

class MediaPlayerUtils {
    /**
     * Format time in seconds to MM:SS format
     */
    static formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    /**
     * Update volume icon based on volume level
     */
    static updateVolumeIcon(value, volumeIcon, volumeIconBtn) {
        if (value == 0) {
            volumeIcon.innerHTML = getIcon('volume-close');
            volumeIconBtn.setAttribute('aria-label', 'Unmute');
        } else if (value < 33) {
            volumeIcon.innerHTML = getIcon('volume-low');
            volumeIconBtn.setAttribute('aria-label', 'Mute');
        } else if (value < 66) {
            volumeIcon.innerHTML = getIcon('volume-medium');
            volumeIconBtn.setAttribute('aria-label', 'Mute');
        } else {
            volumeIcon.innerHTML = getIcon('volume-high');
            volumeIconBtn.setAttribute('aria-label', 'Mute');
        }
    }

    /**
     * Setup progress bar dragging functionality
     */
    static setupProgressDragging(mediaElement, progress, progressBar, isDraggingCallback) {
        let isDragging = false;

        const updateProgress = (e) => {
            const rect = progress.getBoundingClientRect();
            const percent = Math.max(0, Math.min(100, ((e.clientX - rect.left) / rect.width) * 100));
            progressBar.style.width = percent + '%';
            progress.style.setProperty('--progress-percent', percent + '%');
            mediaElement.currentTime = (percent / 100) * mediaElement.duration;
        };

        const startDragging = (e) => {
            isDragging = true;
            isDraggingCallback(true);
            updateProgress(e);
            e.preventDefault();
        };

        const stopDragging = () => {
            if (isDragging) {
                isDragging = false;
                isDraggingCallback(false);
            }
        };

        const handleDragging = (e) => {
            if (isDragging) {
                updateProgress(e);
            }
        };

        // Mouse events
        progress.addEventListener('mousedown', startDragging);
        document.addEventListener('mousemove', handleDragging);
        document.addEventListener('mouseup', stopDragging);

        // Touch events
        progress.addEventListener('touchstart', (e) => {
            const touch = e.touches[0];
            startDragging({ clientX: touch.clientX, preventDefault: () => e.preventDefault() });
        });

        document.addEventListener('touchmove', (e) => {
            if (isDragging && e.touches[0]) {
                handleDragging({ clientX: e.touches[0].clientX });
            }
        });

        document.addEventListener('touchend', stopDragging);

        return { isDragging: () => isDragging };
    }

    /**
     * Setup volume control functionality
     */
    static setupVolumeControl(mediaElement, volumeSlider, volumeBar, volumeIcon, volumeIconBtn) {
        let previousVolume = 100;

        // Update volume bar visual
        const updateVolumeBar = () => {
            const value = volumeSlider.value;
            volumeBar.style.width = value + '%';
            MediaPlayerUtils.updateVolumeIcon(value, volumeIcon, volumeIconBtn);
        };

        // Volume slider change
        volumeSlider.addEventListener('input', function() {
            const value = this.value;
            mediaElement.volume = value / 100;
            updateVolumeBar();

            if (value > 0) {
                previousVolume = value;
            }
        });

        // Volume icon toggle
        volumeIconBtn.addEventListener('click', function() {
            if (mediaElement.volume > 0) {
                previousVolume = volumeSlider.value;
                volumeSlider.value = 0;
                mediaElement.volume = 0;
            } else {
                volumeSlider.value = previousVolume;
                mediaElement.volume = previousVolume / 100;
            }
            updateVolumeBar();
        });

        // Initialize
        updateVolumeBar();

        return { updateVolumeBar, previousVolume };
    }

    /**
     * Setup play/pause button
     */
    static setupPlayPause(mediaElement, playBtn, playIcon) {
        playBtn.addEventListener('click', () => {
            if (mediaElement.paused) {
                mediaElement.play();
                playIcon.innerHTML = getIcon('pause');
                playBtn.setAttribute('aria-label', 'Pause');
            } else {
                mediaElement.pause();
                playIcon.innerHTML = getIcon('play');
                playBtn.setAttribute('aria-label', 'Play');
            }
        });

        // Reset icon when media ends
        mediaElement.addEventListener('ended', () => {
            playIcon.innerHTML = getIcon('play');
            playBtn.setAttribute('aria-label', 'Play');
        });
    }

    /**
     * Setup time update listeners
     */
    static setupTimeUpdate(mediaElement, progressBar, progress, currentTime, isDraggingGetter) {
        mediaElement.addEventListener('timeupdate', () => {
            if (!isDraggingGetter()) {
                const percent = (mediaElement.currentTime / mediaElement.duration) * 100;
                progressBar.style.width = percent + '%';
                progress.style.setProperty('--progress-percent', percent + '%');
                currentTime.textContent = MediaPlayerUtils.formatTime(mediaElement.currentTime);
            }
        });
    }

    /**
     * Setup duration display (tries multiple events to catch it)
     */
    static setupDurationDisplay(mediaElement, durationElement) {
        const updateDuration = () => {
            if (mediaElement.duration && !isNaN(mediaElement.duration) && isFinite(mediaElement.duration)) {
                durationElement.textContent = MediaPlayerUtils.formatTime(mediaElement.duration);
            }
        };

        mediaElement.addEventListener('loadedmetadata', updateDuration);
        mediaElement.addEventListener('durationchange', updateDuration);
        mediaElement.addEventListener('canplay', updateDuration);

        // Fallback
        if (mediaElement.readyState >= 1) {
            updateDuration();
        }
    }

    /**
     * Setup download button
     */
    static setupDownload(mediaElement, downloadBtn) {
        const mediaSrc = mediaElement.querySelector('source')?.src || mediaElement.src;
        downloadBtn.href = mediaSrc + (mediaSrc.includes('?') ? '&' : '?') + 'download=1';

        const filename = mediaSrc.split('/').pop().split('?')[0] || 'media';
        downloadBtn.setAttribute('download', filename);
    }
}

// Export for use in templates
window.MediaPlayerUtils = MediaPlayerUtils;
