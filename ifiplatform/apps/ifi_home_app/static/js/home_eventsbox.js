// Mobile-only "See more events" expand/collapse (home_eventsbox.html/.css,
// home_layout.css) -- same tap-to-see-everything idea as messageboard.js's
// modal, just expanding .eventsbox_container itself full-screen in place
// instead of opening a separate dialog, so the list's own interactive bits
// (union tag toggles, sub-event toggles, links) keep working unchanged
// rather than needing to be duplicated into a clone.
document.addEventListener("DOMContentLoaded", () => {
  const container = document.querySelector(".eventsbox_container");
  const moreButton = document.querySelector(".home-eventsbox-more");
  const closeButton = document.querySelector(".home-eventsbox-close");
  if (!container || !moreButton || !closeButton) {
    return;
  }

  const expand = () => {
    container.classList.add("is-expanded");
    document.body.classList.add("eventsbox-expanded");
    container.scrollTop = 0;
    closeButton.focus();
  };

  const collapse = () => {
    container.classList.remove("is-expanded");
    document.body.classList.remove("eventsbox-expanded");
    moreButton.focus();
  };

  moreButton.addEventListener("click", expand);
  closeButton.addEventListener("click", collapse);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && container.classList.contains("is-expanded")) {
      collapse();
    }
  });
});
