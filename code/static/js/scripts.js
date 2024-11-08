// Přidání potvrzení před udělením "dislike"
document.addEventListener("DOMContentLoaded", function() {
    const dislikeButtons = document.querySelectorAll("button.dislike");

    dislikeButtons.forEach(button => {
        button.addEventListener("click", function(event) {
            const confirmDislike = confirm("Are you sure you want to dislike this user?");
            if (!confirmDislike) {
                event.preventDefault();
            }
        });
    });
});
