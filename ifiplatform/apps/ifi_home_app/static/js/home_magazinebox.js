// Arrows and progress bar for the homepage's >OUTPUT box. Without this
// script the covers still swipe (CSS scroll-snap); the controls stay hidden.
// Design rationale: docs/claude_context/home_magazinebox.md
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-magazinebox]").forEach((box) => {
    const strip = box.querySelector(".home-magazinebox-strip");
    const slides = [...strip.children];
    if (slides.length < 2) {
      return;
    }
    const controls = box.querySelector(".home-magazinebox-controls");
    const bar = box.querySelector(".home-magazinebox-bar");
    const row = box.querySelector(".home-magazinebox-segments");
    const segments = [...row.children];
    const [newer, older] = box.querySelectorAll(".home-magazinebox-arrow");
    controls.hidden = false;

    const currentIndex = () => Math.round(strip.scrollLeft / strip.clientWidth);
    const goTo = (index) => {
      const target = Math.max(0, Math.min(slides.length - 1, index));
      strip.scrollTo({ left: target * strip.clientWidth });
    };

    // Keeps the current segment centred, but never slides the row past its
    // own ends; when every segment fits, the row is simply centred.
    const slideBar = (index) => {
      const barWidth = bar.clientWidth;
      const rowWidth = row.scrollWidth;
      let shift = (barWidth - rowWidth) / 2;
      if (rowWidth > barWidth) {
        const segment = segments[index];
        const centre = segment.offsetLeft - row.offsetLeft + segment.offsetWidth / 2;
        shift = Math.min(0, Math.max(barWidth - rowWidth, barWidth / 2 - centre));
      }
      bar.classList.toggle("has-more-before", shift < 0);
      bar.classList.toggle("has-more-after", shift > barWidth - rowWidth);
      row.style.transform = `translateX(${shift}px)`;
    };

    let shown = -1;
    const update = (force = false) => {
      const index = currentIndex();
      if (index === shown && !force) {
        return;
      }
      shown = index;
      segments.forEach((segment, i) => {
        segment.setAttribute("aria-current", i === index ? "true" : "false");
      });
      newer.disabled = index === 0;
      older.disabled = index === slides.length - 1;
      slideBar(index);
    };

    newer.addEventListener("click", () => goTo(currentIndex() - 1));
    older.addEventListener("click", () => goTo(currentIndex() + 1));
    segments.forEach((segment, i) => segment.addEventListener("click", () => goTo(i)));
    strip.addEventListener("scroll", () => requestAnimationFrame(() => update()), {
      passive: true,
    });
    window.addEventListener("resize", () => update(true));
    update(true);
  });
});
