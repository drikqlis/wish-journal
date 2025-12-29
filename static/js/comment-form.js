// Comment form validation and submission handling
document.addEventListener('DOMContentLoaded', function() {
    const formMessage = document.getElementById('form-message');
    const formError = document.getElementById('form-error');
    const commentForm = document.querySelector('#comment-form form');

    if (!commentForm) {
        return; // Exit if no comment form on page
    }

    // Helper function to show a message and hide the other
    function showMessage(msgToShow, msgToHide) {
        msgToHide.classList.remove('visible');
        msgToShow.classList.add('visible');
    }

    // Form validation
    commentForm.addEventListener('submit', function(e) {
        const textarea = this.querySelector('textarea');
        const submitButton = this.querySelector('button[type="submit"]');

        if (!textarea.value || !textarea.value.trim()) {
            e.preventDefault();
            e.stopPropagation();
            textarea.style.borderColor = 'var(--error-color)';
            showMessage(formError, formMessage);
            setTimeout(() => {
                textarea.style.borderColor = '';
                formError.classList.remove('visible');
            }, 3000);
            return false;
        }

        // Remove focus from button on mobile to prevent stuck pressed state
        if (submitButton) {
            setTimeout(() => submitButton.blur(), 100);
        }
    });

    // Show success message if comment was just submitted
    // This will be triggered by setting window.showCommentSuccess in the template
    if (window.showCommentSuccess) {
        showMessage(formMessage, formError);
        setTimeout(() => formMessage.classList.remove('visible'), 3000);
    }
});
