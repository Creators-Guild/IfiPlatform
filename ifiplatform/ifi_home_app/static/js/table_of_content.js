document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".table_of_content-toggle").forEach((button) => {
    const layout = button.closest(".article-layout");
    if (!layout) {
      return;
    }

    button.addEventListener("click", () => {
      const collapsed = layout.classList.toggle("toc-collapsed");
      button.setAttribute("aria-expanded", String(!collapsed));
      button.textContent = collapsed
        ? button.dataset.showText
        : button.dataset.hideText;
    });
  });
});
