// Tap-to-toggle behavior for hover-driven menu components (the top navbar's
// .dropdown-menu, the sidebar's .sidemenu-item submenus, and the sidebar
// rail itself), shared since they all need the same fix: on touch there's
// no hover to reveal a submenu, so the first tap has to open it instead of
// navigating away. Guarded against double-init since this script is
// included from multiple partials that can appear together on the same
// page (navbar + sidemenu).
if (!window.__ifiTapToggleMenusInit) {
  window.__ifiTapToggleMenusInit = true;

  // News/Info Articles/etc. dropdown, and each sidebar item's submenu:
  // tapping the trigger toggles that one container open/closed, tapping
  // outside closes it, and only one container in the group is open at a
  // time. A .drop-option--all link inside is how a touch user actually
  // navigates, since the trigger no longer does. Defined outside the
  // DOMContentLoaded handler below since .profile-dropdown needs it
  // unconditionally (click-only, no hover reveal ever), not just gated to
  // touch devices like the rest of this file.
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

  document.addEventListener("DOMContentLoaded", () => {
    // .profile-dropdown opts out of the hover-reveal .dropdown-menu
    // otherwise gets (see topheader_bar.css) -- click-only on every device,
    // so it's wired up here regardless of hover capability.
    setupTapToggle(".profile-dropdown", "button.link");

    // Its .drop-content is position:fixed (see topheader_bar.css -- .nav_links
    // has overflow-x:auto, which per the CSS overflow spec forces
    // overflow-y:auto too, clipping a position:absolute panel), which means
    // it no longer sits relative to the button automatically. Position it
    // from the button's actual on-screen location instead of a guessed
    // fixed offset, so it lands directly under the icon (not overlapping
    // it) regardless of header height, zoom, or viewport width.
    document.querySelectorAll(".profile-dropdown").forEach((dropdown) => {
      const trigger = dropdown.querySelector("button.link");
      const panel = dropdown.querySelector(".drop-content");
      if (!trigger || !panel) {
        return;
      }
      const positionPanel = () => {
        const rect = trigger.getBoundingClientRect();
        panel.style.top = `${rect.bottom + 8}px`;
        panel.style.right = `${window.innerWidth - rect.right}px`;
      };
      trigger.addEventListener("click", positionPanel);
      window.addEventListener("resize", positionPanel);
    });

    if (window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
      return; // devices with real mouse hover keep the existing CSS :hover behavior
    }

    setupTapToggle(".dropdown-menu:not(.profile-dropdown)", "button.link");
    setupTapToggle(".sidemenu-item", "a.sidemenu-option");
    // Homepage events box: an event's highlighted sub-events (home_
    // eventsbox.html/.css), same in-flow expand-in-place pattern as
    // .sidemenu-item above rather than a floating .dropdown-menu -- it
    // lives inside .eventsbox_container, which scrolls (overflow-y:auto),
    // and a position:absolute/fixed panel there either gets clipped or (if
    // fixed) drifts away from its trigger on scroll. Expanding in normal
    // flow sidesteps that entirely: it just grows the row, same as any
    // other in-flow content would.
    setupTapToggle(".home-eventsbox-subevents", "button.home-eventsbox-subevents-toggle");

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
      // On mobile .sidemenu.is-open sets an explicit height (100dvh, see
      // sidemenu.css) so the overlay covers the full screen; removing
      // "is-open" reverts that back to the short, content-sized height
      // instantly, while width takes ~0.2s to animate back down to 56px.
      // Left alone, that gap showed a still-wide-but-already-short box for
      // a moment -- the same "too short" sidemenu look the hover fix
      // addressed, just appearing on close instead. A CSS transition-delay
      // on height was tried first, but height animating to/from 'auto'
      // isn't reliably interpolable, so mobile browsers didn't consistently
      // honor the delay. Locking the current pixel height as an inline
      // style (which beats the class-based height rule regardless of
      // specificity) and only releasing it once the width transition has
      // actually finished sidesteps that unreliability entirely. Harmless
      // on non-mobile/hover-incapable devices too (e.g. a touch tablet
      // above the 480px breakpoint): there .sidemenu.is-open never sets an
      // explicit height, so the locked value just matches the unchanged
      // content height and the lock/release is a no-op.
      const closeSidemenu = () => {
        const lockedHeight = sidemenu.getBoundingClientRect().height;
        sidemenu.style.height = `${lockedHeight}px`;
        sidemenu.classList.remove("is-open");
        header.setAttribute("aria-expanded", "false");

        // Reset any submenu (.sidemenu-item) left open, not just the rail
        // itself -- without this, an item tapped open earlier stayed
        // "open" internally even while hidden by the collapsed rail, so
        // reopening the rail would fade it back in already-expanded, and
        // that same reopening tap -- being outside every .sidemenu-item --
        // would immediately trigger setupTapToggle's own outside-click
        // closer on it too, producing a visible flash-open-then-collapse
        // right as the rail opened. Closing the whole menu now always
        // starts the next open from a clean state.
        sidemenu.querySelectorAll(".sidemenu-item.is-open").forEach((item) => {
          item.classList.remove("is-open");
          const trigger = item.querySelector("a.sidemenu-option");
          if (trigger) {
            trigger.setAttribute("aria-expanded", "false");
          }
        });

        let released = false;
        const releaseHeight = () => {
          if (released) {
            return;
          }
          released = true;
          sidemenu.style.height = "";
          sidemenu.removeEventListener("transitionend", onTransitionEnd);
        };
        const onTransitionEnd = (event) => {
          if (event.target === sidemenu && event.propertyName === "width") {
            releaseHeight();
          }
        };
        sidemenu.addEventListener("transitionend", onTransitionEnd);
        // fallback in case width didn't actually change (so no
        // transitionend fires) -- matches sidemenu.css's 0.2s width
        // transition, with slack for timing jitter.
        window.setTimeout(releaseHeight, 300);
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
