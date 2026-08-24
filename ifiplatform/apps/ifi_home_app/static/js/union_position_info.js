document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".position-info-widget").forEach((widget) => {
    const openButton = widget.querySelector(".position-info-button");
    const panel = widget.querySelector(".position-info-panel");
    const closeButton = widget.querySelector(".position-info-close");
    if (!openButton || !panel || !closeButton) {
      return;
    }

    const openPanel = () => {
      panel.hidden = false;
      openButton.setAttribute("aria-expanded", "true");
      closeButton.focus();
    };

    const closePanel = () => {
      panel.hidden = true;
      openButton.setAttribute("aria-expanded", "false");
    };

    openButton.addEventListener("click", (event) => {
      event.stopPropagation();
      if (panel.hidden) {
        openPanel();
      } else {
        closePanel();
      }
    });

    closeButton.addEventListener("click", closePanel);

    // No backdrop by design -- the rest of the page stays interactable, so
    // closing on an outside click means listening document-wide instead.
    document.addEventListener("click", (event) => {
      if (!panel.hidden && !panel.contains(event.target) && !widget.contains(event.target)) {
        closePanel();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !panel.hidden) {
        closePanel();
        openButton.focus();
      }
    });
  });
});
