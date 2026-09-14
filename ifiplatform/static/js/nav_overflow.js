// Waits for stylesheets before measuring: docs/claude_context/css_loading.md
const stylesheetsReady = () =>
  Promise.all(
    [...document.querySelectorAll('link[rel="stylesheet"]')]
      .filter((link) => !link.sheet)
      .map(
        (link) =>
          new Promise((resolve) => {
            // on error too, so one 404 sheet can't leave the nav unmeasured
            link.addEventListener("load", resolve, { once: true });
            link.addEventListener("error", resolve, { once: true });
          }),
      ),
  );

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".header-bar").forEach((headerBar) => {
    const logoBox = headerBar.querySelector(".ifiplatform-logo-box");
    const navLinks = headerBar.querySelector(".nav_links");
    if (!logoBox || !navLinks) {
      return;
    }

    const check = () => {
      // Check against the *full-label* layout, regardless of which mode
      // is currently showing -- checking the live element directly would
      // create a feedback loop, since switching modes changes its own
      // size (short labels always "fit", so it would immediately flip
      // back to full labels, which might not fit, flipping back again,
      // and so on). Removing the class before measuring and toggling it
      // after doesn't cause a visible flash -- the browser doesn't paint
      // mid-script, only after this returns.
      headerBar.classList.remove("nav-compact");

      // Rather than approximating the browser's own flex-wrap decision
      // with a separate width calculation (which can disagree with it by
      // a few pixels, leaving a visible window where full labels have
      // already wrapped onto their own line), just ask the browser
      // directly whether they're still on the same flex line.
      //
      // Comparing X position doesn't work: margin-left:auto still pushes
      // nav_links toward the right edge even once it's wrapped onto its
      // own row, so its left edge can end up right of the logo's right
      // edge regardless of whether it actually wrapped. The reliable
      // signal is the Y axis -- two items share a flex line only if their
      // vertical extents overlap, no matter their individual heights or
      // horizontal position.
      const logoRect = logoBox.getBoundingClientRect();
      const navRect = navLinks.getBoundingClientRect();
      const sameLine = navRect.top < logoRect.bottom && navRect.bottom > logoRect.top;

      headerBar.classList.toggle("nav-compact", !sameLine);
    };

    // not check() directly: DOMContentLoaded doesn't wait for stylesheets
    stylesheetsReady().then(check);

    if (window.ResizeObserver) {
      new ResizeObserver(check).observe(headerBar);
    } else {
      window.addEventListener("resize", check);
    }
  });
});
