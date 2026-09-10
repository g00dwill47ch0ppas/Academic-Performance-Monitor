console.log("Student Performance Assistant Loaded.");

// ---------------------------------------------------------------------------
// Flash messages: fade out after a few seconds for a cleaner UI.
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".flash").forEach((el) => {
        setTimeout(() => {
            el.style.transition = "opacity 0.4s ease";
            el.style.opacity = "0";
        }, 4000);
    });
});

// ---------------------------------------------------------------------------
// Colour scheme: the navbar button toggles light/dark and remembers the
// choice. The initial class is applied inline in <head> to avoid a flash.
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
    const root = document.documentElement;
    const toggle = document.getElementById("darkModeToggle");
    const moon = document.getElementById("themeIconMoon");
    const sun = document.getElementById("themeIconSun");
    if (!toggle) return;

    function syncThemeButton() {
        const isDark = root.classList.contains("dark-mode");
        toggle.setAttribute("aria-pressed", String(isDark));
        toggle.setAttribute("aria-label", isDark ? "Switch to light mode" : "Switch to dark mode");
        toggle.title = isDark ? "Switch to light mode" : "Switch to dark mode";
        if (moon) moon.hidden = isDark;
        if (sun) sun.hidden = !isDark;
    }

    toggle.addEventListener("click", () => {
        const isDark = root.classList.toggle("dark-mode");
        try {
            localStorage.setItem("spa-theme", isDark ? "dark" : "light");
        } catch (e) { /* storage unavailable — theme just won't persist */ }
        syncThemeButton();
    });

    syncThemeButton();
});

// ---------------------------------------------------------------------------
// Navigation sidebar (slides in from the right).
//   - opens from the navbar button, closes on the overlay, Escape or a link
//   - while open, Tab/Shift+Tab stay inside the panel (focus trap)
//   - ArrowUp/ArrowDown/Home/End move between the navigation links
//   - closing returns focus to the button that opened it
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.getElementById("navToggle");
    const sidebar = document.getElementById("navSidebar");
    const overlay = document.getElementById("navOverlay");
    const closeButton = document.getElementById("navClose");
    if (!toggle || !sidebar || !overlay) return;

    const FOCUSABLE =
        'a[href], button:not([disabled]), input:not([disabled]), select, textarea, ' +
        '[tabindex]:not([tabindex="-1"])';

    let lastFocus = null;

    function isOpen() {
        return sidebar.classList.contains("active");
    }

    function focusableItems() {
        return Array.from(sidebar.querySelectorAll(FOCUSABLE)).filter(
            (el) => el.getClientRects().length > 0
        );
    }

    function openSidebar() {
        if (isOpen()) return;
        lastFocus = document.activeElement;
        sidebar.inert = false;
        sidebar.classList.add("active");
        overlay.classList.add("active");
        document.body.classList.add("nav-open");
        toggle.setAttribute("aria-expanded", "true");
        toggle.setAttribute("aria-label", "Close navigation");

        // Move focus into the panel. The panel is only focusable once the
        // browser has applied its visible state, so fall back to the next
        // frame if the first attempt did not take.
        const links = sidebar.querySelectorAll(".settings-link");
        const target = links.length > 0 ? links[0] : closeButton;
        if (!target) return;
        const before = document.activeElement;
        target.focus();
        if (document.activeElement === before) {
            requestAnimationFrame(() => target.focus());
        }
    }

    function closeSidebar(restoreFocus) {
        if (!isOpen()) return;
        sidebar.classList.remove("active");
        overlay.classList.remove("active");
        document.body.classList.remove("nav-open");
        toggle.setAttribute("aria-expanded", "false");
        toggle.setAttribute("aria-label", "Open navigation");
        sidebar.inert = true;
        if (restoreFocus) {
            const target = lastFocus && typeof lastFocus.focus === "function" ? lastFocus : toggle;
            target.focus();
        }
        lastFocus = null;
    }

    // Keep the panel out of the tab order while it is off-screen.
    sidebar.inert = true;

    toggle.addEventListener("click", () => {
        if (isOpen()) {
            closeSidebar(false);
        } else {
            openSidebar();
        }
    });

    if (closeButton) {
        closeButton.addEventListener("click", () => closeSidebar(true));
    }

    overlay.addEventListener("click", () => closeSidebar(true));

    // Keyboard handling inside the open panel.
    sidebar.addEventListener("keydown", (event) => {
        if (!isOpen()) return;
        const items = focusableItems();
        if (items.length === 0) return;

        const first = items[0];
        const last = items[items.length - 1];
        const current = document.activeElement;
        const links = Array.from(sidebar.querySelectorAll(".settings-link"));
        const link = links.indexOf(current);

        if (event.key === "Tab") {
            if (
                (event.shiftKey && (current === first || current === sidebar)) ||
                (!event.shiftKey && current === last)
            ) {
                event.preventDefault();
                (event.shiftKey ? last : first).focus();
            }
        } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            if (link === -1 || links.length === 0) return;
            event.preventDefault();
            const step = event.key === "ArrowDown" ? 1 : -1;
            links[(link + step + links.length) % links.length].focus();
        } else if (event.key === "Home" && links.length > 0) {
            event.preventDefault();
            links[0].focus();
        } else if (event.key === "End" && links.length > 0) {
            event.preventDefault();
            links[links.length - 1].focus();
        }
    });

    // Close after choosing a navigation link (the new page takes over focus).
    sidebar.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", () => closeSidebar(false));
    });

    // Escape closes the panel from anywhere and restores focus to the button.
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeSidebar(true);
    });
});
