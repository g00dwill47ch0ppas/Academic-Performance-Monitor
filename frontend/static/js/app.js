console.log("Student Performance Assistant Loaded.");

// Auto-dismiss flash messages after a few seconds for a cleaner UI.
document.addEventListener("DOMContentLoaded", () => {
    const flashes = document.querySelectorAll(".flash");
    flashes.forEach((el) => {
        setTimeout(() => {
            el.style.transition = "opacity 0.4s ease";
            el.style.opacity = "0";
        }, 4000);
    });
});
