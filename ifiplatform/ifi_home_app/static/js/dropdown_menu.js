// Tap-to-toggle behavior for hover-driven menu components (the top navbar's
// .dropdown-menu, the sidebar's .sidemenu-item submenus, and the sidebar
// rail itself), shared since they all need the same fix: on touch there's
// no hover to reveal a submenu, so the first tap has to open it instead of
// navigating away. Guarded against double-init since this script is
// included from multiple partials that can appear together on the same
// page (navbar + sidemenu).
if (!window.__ifiTapToggleMenusInit) {
  window.__ifiTapToggleMenusInit = true;

  document.addEventListener("DOMContentLoaded", () => {
    if (window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
      return; // devices with real mouse hover keep the existing CSS :hover behavior
    }

    // News/Info Articles/etc. dropdown, and each sidebar item's submenu:
    // tapping the trigger toggles that one container open/closed, tapping
    // outside closes it, and only one container in the group is open at a
    // time. A .drop-option--all link inside is how a touch user actually
    // navigates, since the trigger no longer does.
    const setupTapToggle = (containerSelector, triggerSelector) => {
      const containers = document.querySelectorAll(containerSelector);

      const closeContainer = (container) => {
        container.classList.remove("is-open");
        const trigger = container.querySelector(triggerSelector);
        if (trigger) {
          trigger.setAttribute("aria-expanded", "false");
        }
      };

      containers.forEach((container) => {
        // listen on the trigger (not necessarily the inner <a>) -- the
        // navbar's trigger is a <button> wrapping an <a>, which is invalid
        // nesting where exactly which element a tap resolves to isn't
        // reliable on touch. preventDefault() during bubble still cancels
        // the inner link's navigation either way.
        const trigger = container.querySelector(triggerSelector);
        if (!trigger) {
          return;
        }
        trigger.setAttribute("aria-expanded", "false");

        trigger.addEventListener("click", (event) => {
          event.preventDefault();
          const wasOpen = container.classList.contains("is-open");
          containers.forEach(closeContainer);
          if (!wasOpen) {
            container.classList.add("is-open");
            trigger.setAttribute("aria-expanded", "true");
          }
        });
      });

      document.addEventListener("click", (event) => {
        containers.forEach((container) => {
          if (
            container.classList.contains("is-open") &&
            !container.contains(event.target)
          ) {
            closeContainer(container);
          }
        });
      });
    };

    setupTapToggle(".dropdown-menu", "button.link");
    setupTapToggle(".sidemenu-item", "a.sidemenu-option");

    // The sidebar rail itself: tapping .sidemenu-header expands it (this is
    // what makes the submenus above visible/reachable at all on touch --
    // .sidemenu-item is opacity:0 until the rail is expanded), and either
    // .sidemenu-close or tapping outside collapses it back.
    document.querySelectorAll(".sidemenu").forEach((sidemenu) => {
      const header = sidemenu.querySelector(".sidemenu-header");
      const closeButton = sidemenu.querySelector(".sidemenu-close");
      if (!header) {
        return;
      }
      header.setAttribute("aria-expanded", "false");

      const openSidemenu = () => {
        sidemenu.classList.add("is-open");
        header.setAttribute("aria-expanded", "true");
      };
      const closeSidemenu = () => {
        sidemenu.classList.remove("is-open");
        header.setAttribute("aria-expanded", "false");
      };

      header.addEventListener("click", (event) => {
        event.preventDefault();
        if (sidemenu.classList.contains("is-open")) {
          closeSidemenu();
        } else {
          openSidemenu();
        }
      });
      // .sidemenu-header is a <div role="button">, not a native button, so
      // it needs its own keyboard activation.
      header.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          header.click();
        }
      });

      if (closeButton) {
        closeButton.addEventListener("click", (event) => {
          event.preventDefault();
          closeSidemenu();
        });
      }

      document.addEventListener("click", (event) => {
        if (sidemenu.classList.contains("is-open") && !sidemenu.contains(event.target)) {
          closeSidemenu();
        }
      });
    });
  });
}
