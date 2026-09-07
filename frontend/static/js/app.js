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

// Burger menu: toggle the slide-down navigation panel.
document.addEventListener("DOMContentLoaded", () => {
    const nav = document.getElementById("siteNav");
    const toggle = document.getElementById("navToggle");
    if (!nav || !toggle) return;

    function setOpen(open) {
        nav.classList.toggle("open", open);
        toggle.setAttribute("aria-expanded", String(open));
    }

    toggle.addEventListener("click", () => {
        setOpen(!nav.classList.contains("open"));
    });

    // Close the menu after choosing a link.
    nav.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", () => setOpen(false));
    });

    // Close when clicking anywhere outside the menu.
    document.addEventListener("click", (event) => {
        if (!nav.contains(event.target)) setOpen(false);
    });

    // Close on Escape.
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") setOpen(false);
    });
});
