// The homepage's Ifi Instagram feed:
// - "… more" / "less" opens and folds a caption in place (the button stays
//   hidden without this script);
// - album arrows and dots (without the script the strip still swipes);
// - the viewer: clicking a post opens a <dialog> at that post, which
//   scrolls vertically through all posts, one screen each;
// - on screens matching SHOW_MORE_OPENS_VIEWER, "Show more" opens the viewer
//   at the first hidden post instead of opening the rest of the list.
// Design rationale: docs/claude_context/home_instagram.md

// Where "Show more" opens the viewer instead of the rest of the list: every
// screen (user, 2026-11-15). A media query such as "(max-width: 45rem)"
// limits it to phones again.
const SHOW_MORE_OPENS_VIEWER = "all";

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".home-instagram-more").forEach((button) => {
    const caption = button.previousElementSibling;
    if (!caption || !caption.classList.contains("home-instagram-caption")) {
      return;
    }
    button.hidden = false;
    button.addEventListener("click", () => {
      const open = caption.classList.toggle("is-expanded");
      button.textContent = open ? button.dataset.less : button.dataset.more;
      button.setAttribute("aria-expanded", String(open));
    });
    button.setAttribute("aria-expanded", "false");
  });

  // A playing video pauses once it's mostly scrolled out of view, in the
  // viewer and in the phone feed alike.
  if ("IntersectionObserver" in window) {
    const offscreen = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.intersectionRatio < 0.5 && !entry.target.paused) {
            entry.target.pause();
          }
        });
      },
      { threshold: [0, 0.5] },
    );
    document.querySelectorAll(".home-instagram-video").forEach((video) => offscreen.observe(video));
  }

  // Album pictures are lazy, so the 3rd and later only started loading once
  // swiped to and looked empty for a moment. When an album comes into view,
  // load all of its pictures; albums nobody looks at still cost nothing.
  if ("IntersectionObserver" in window) {
    const preload = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.querySelectorAll("img").forEach((img) => {
            img.loading = "eager";
          });
          observer.unobserve(entry.target);
        }
      });
    });
    document.querySelectorAll("[data-album]").forEach((album) => preload.observe(album));
  }

  document.querySelectorAll("[data-album]").forEach((album) => {
    const strip = album.querySelector(".home-instagram-album-strip");
    const dots = [...album.querySelectorAll(".home-instagram-album-dots i")];
    const [previous, next] = album.querySelectorAll(".home-instagram-album-nav");
    const current = () => Math.round(strip.scrollLeft / Math.max(strip.clientWidth, 1));
    const update = () => {
      const index = current();
      dots.forEach((dot, i) => dot.classList.toggle("is-current", i === index));
      previous.disabled = index === 0;
      next.disabled = index === dots.length - 1;
    };
    previous.hidden = false;
    next.hidden = false;
    previous.addEventListener("click", () => strip.scrollBy({ left: -strip.clientWidth }));
    next.addEventListener("click", () => strip.scrollBy({ left: strip.clientWidth }));
    strip.addEventListener("scroll", () => requestAnimationFrame(update), { passive: true });
    update();
  });

  document.querySelectorAll(".instagram_container").forEach((section) => {
    const viewer = section.querySelector(".home-instagram-viewer");
    if (!viewer || typeof viewer.showModal !== "function") {
      return;
    }
    const feed = viewer.querySelector(".home-instagram-viewer-feed");
    const posts = [...viewer.querySelectorAll(".home-instagram-viewer-post")];

    const scrollTo = (index, smooth) => {
      const post = posts[Math.max(0, Math.min(posts.length - 1, index))];
      post.scrollIntoView({ block: "center", behavior: smooth ? "smooth" : "auto" });
    };
    const currentIndex = () => {
      const top = feed.getBoundingClientRect().top;
      let best = 0;
      let distance = Infinity;
      posts.forEach((post, i) => {
        const d = Math.abs(post.getBoundingClientRect().top - top);
        if (d < distance) {
          distance = d;
          best = i;
        }
      });
      return best;
    };

    const open = (index) => {
      viewer.showModal();
      scrollTo(index, false);
    };
    section.querySelectorAll(".home-instagram-thumb").forEach((thumb) => {
      thumb.disabled = false;
      thumb.addEventListener("click", () => open(Number(thumb.dataset.index)));
    });

    const showMore = section.querySelector(".home-instagram-toggle summary");
    const toggle = section.querySelector(".home-instagram-toggle");
    if (showMore) {
      showMore.addEventListener("click", (event) => {
        if (toggle.open || !window.matchMedia(SHOW_MORE_OPENS_VIEWER).matches) {
          return;
        }
        event.preventDefault();
        const feedPosts = [...section.querySelectorAll(".home-instagram-post")];
        const firstHidden = feedPosts.findIndex((post) => post.offsetParent === null);
        open(firstHidden === -1 ? 0 : firstHidden);
      });
    }
    viewer.querySelector(".home-instagram-viewer-close").addEventListener("click", () => viewer.close());
    viewer.addEventListener("click", (event) => {
      if (event.target === viewer || event.target === feed) {
        viewer.close();
      }
    });
    viewer.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        scrollTo(currentIndex() + (event.key === "ArrowDown" ? 1 : -1), true);
      }
    });
    viewer.addEventListener("close", () => {
      viewer.querySelectorAll("video").forEach((video) => video.pause());
    });
  });
});
