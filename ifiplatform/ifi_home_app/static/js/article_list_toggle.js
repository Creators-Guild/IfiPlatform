// Per-card expand/collapse for the homepage newsbar/articlesbar grids
// (.newsbar-layout, shared by home_newsbar.html and home_articlesbar.html --
// both load this script, hence the double-init guard). Default on load
// matches the old CSS-only behavior this replaces (every card past the
// first two starts collapsed), but now each .articlecard-toggle arrow
// (see article_card.html/articlecard.css) lets a visitor flip that one
// card between the full and .articlecard--list looks themselves.
if (!window.__ifiArticleListToggleInit) {
  window.__ifiArticleListToggleInit = true;

  document.addEventListener("DOMContentLoaded", () => {
    const setCardState = (card, collapsed) => {
      card.classList.toggle("articlecard--list", collapsed);
      const toggle = card.querySelector(".articlecard-toggle");
      if (toggle) {
        toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
      }
    };

    document.querySelectorAll(".newsbar-layout").forEach((layout) => {
      const cards = Array.from(layout.querySelectorAll(".articlecard"));
      cards.forEach((card, index) => {
        setCardState(card, index >= 2);
      });
    });

    document.querySelectorAll(".newsbar-layout .articlecard-toggle").forEach((toggle) => {
      toggle.addEventListener("click", (event) => {
        // .articlecard-toggle lives inside the card's own <a> (see
        // article_card.html's comment on that nesting tradeoff) -- without
        // this, the click would also navigate to the article itself.
        event.preventDefault();
        event.stopPropagation();

        const card = toggle.closest(".articlecard");
        if (!card) {
          return;
        }
        setCardState(card, !card.classList.contains("articlecard--list"));
      });
    });
  });
}
