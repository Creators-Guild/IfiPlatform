// The homepage's Ifi Instagram feed:
// - "… more" / "less" opens and folds a caption in place (the button stays
//   hidden without this script);
// - album arrows and dots (without the script the strip still swipes);
// - the viewer: clicking a post opens a <dialog> at that post, which
//   scrolls vertically through all posts, one screen each. It starts with
//   the homepage's 12 and fetches the rest of the stored posts the first
//   time it opens (data-more-url);
// - on screens matching SHOW_MORE_OPENS_VIEWER, "Show more" opens the viewer
//   at the first hidden post instead of opening the rest of the list.
// Design rationale: docs/claude_context/home_instagram.md

// Where "Show more" opens the viewer instead of the rest of the list: every
// screen (user, 2026-11-15). A media query such as "(max-width: 45rem)"
// limits it to phones again.
const SHOW_MORE_OPENS_VIEWER = "all";

const hasObserver = "IntersectionObserver" in window;

// A playing video pauses once it's mostly scrolled out of view.
const offscreenVideos = hasObserver
  ? new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.intersectionRatio < 0.5 && !entry.target.paused) {
            entry.target.pause();
          }
        });
      },
      { threshold: [0, 0.5] },
    )
  : null;

// Album pictures are lazy, so the 3rd and later only started loading once
// swiped to and looked empty for a moment. When an album comes into view,
// load all of its pictures; albums nobody looks at still cost nothing.
const albumPreload = hasObserver
  ? new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.querySelectorAll("img").forEach((img) => {
            img.loading = "eager";
          });
          observer.unobserve(entry.target);
        }
      });
    })
  : null;

// Viewer card layouts above the phone breakpoint (home_instagram.css):
// "side" when the picture at full height and the text column fit next to
// each other (whole caption, no "… more"); "overlap" when the text column
// would cover at most MAX_COVER of the picture, so "… more" opens it over
// the picture's right edge; otherwise "stack", where "… more" opens below.
// Videos never overlap: the column would cover their controls.
const TEXT_COLUMN_REM = 24 + 1.25; // the CSS's text column + gap
const MAX_COVER = 0.45;
const phone = window.matchMedia("(max-width: 45rem)");

function fitCards(feed, cards) {
  const rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
  const feedStyle = getComputedStyle(feed);
  const cardStyle = getComputedStyle(cards[0]);
  const padX = parseFloat(cardStyle.paddingLeft) + parseFloat(cardStyle.paddingRight);
  const padY = parseFloat(cardStyle.paddingTop) + parseFloat(cardStyle.paddingBottom);
  const inner = feed.clientWidth - parseFloat(feedStyle.paddingLeft) - parseFloat(feedStyle.paddingRight) - padX;
  const mediaHeight = cards[0].clientHeight - padY;
  const text = TEXT_COLUMN_REM * rem;
  cards.forEach((card) => {
    let layout = "stack";
    let cover = 0;
    if (!phone.matches) {
      const [w, h] = (card.style.getPropertyValue("--ratio") || "4 / 5").split("/").map(Number);
      const media = mediaHeight * (w / h);
      if (media + text <= inner) {
        layout = "side";
      } else if (!card.querySelector(".home-instagram-video")) {
        const shown = Math.min(media, inner);
        cover = shown - (inner - text);
        layout = cover <= MAX_COVER * shown ? "overlap" : "stack";
      }
    }
    card.dataset.layout = layout;
    card.style.setProperty("--fit-cover", `${Math.max(cover, 0)}px`);
  });
}

function wireCaptions(root) {
  root.querySelectorAll(".home-instagram-more").forEach((button) => {
    const caption = button.previousElementSibling;
    if (!caption || !caption.classList.contains("home-instagram-caption")) {
      return;
    }
    button.hidden = false;
    button.setAttribute("aria-expanded", "false");
    button.addEventListener("click", () => {
      const open = caption.classList.toggle("is-expanded");
      button.textContent = open ? button.dataset.less : button.dataset.more;
      button.setAttribute("aria-expanded", String(open));
    });
  });
}

function wireAlbums(root) {
  root.querySelectorAll("[data-album]").forEach((album) => {
    if (albumPreload) {
      albumPreload.observe(album);
    }
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
}

function wireVideos(root) {
  if (offscreenVideos) {
    root.querySelectorAll(".home-instagram-video").forEach((video) => offscreenVideos.observe(video));
  }
}

function wire(root) {
  wireCaptions(root);
  wireAlbums(root);
  wireVideos(root);
}

function setUpViewer(section) {
  const viewer = section.querySelector(".home-instagram-viewer");
  if (!viewer || typeof viewer.showModal !== "function") {
    return;
  }
  const feed = viewer.querySelector(".home-instagram-viewer-feed");
  const posts = () => [...viewer.querySelectorAll(".home-instagram-viewer-post")];

  // The rest of the stored posts, fetched the first time it opens (again on
  // a later open if that failed). Same newest-first order, so the homepage's
  // indexes still point at the right cards.
  let loading = false;
  let loaded = false;
  const loadRest = () => {
    if (!viewer.dataset.moreUrl || loading || loaded) {
      return;
    }
    loading = true;
    fetch(viewer.dataset.moreUrl, { credentials: "same-origin" })
      .then((response) => {
        if (!response.ok) {
          throw new Error(response.statusText);
        }
        return response.text();
      })
      .then((html) => {
        const batch = document.createElement("template");
        batch.innerHTML = html;
        const cards = [...batch.content.children];
        feed.append(batch.content);
        loaded = true;
        cards.forEach(wire);
        fit(cards);
      })
      .catch(() => {})
      .finally(() => {
        loading = false;
      });
  };

  const scrollTo = (index, smooth) => {
    const all = posts();
    const post = all[Math.max(0, Math.min(all.length - 1, index))];
    post.scrollIntoView({ block: "center", behavior: smooth ? "smooth" : "auto" });
  };
  const currentIndex = () => {
    const top = feed.getBoundingClientRect().top;
    let best = 0;
    let distance = Infinity;
    posts().forEach((post, i) => {
      const d = Math.abs(post.getBoundingClientRect().top - top);
      if (d < distance) {
        distance = d;
        best = i;
      }
    });
    return best;
  };

  // Card sizes are only known while the dialog is open, so this runs on
  // every open, for fetched cards, and on resize.
  const fit = (cards = posts()) => {
    if (viewer.open && cards.length) {
      fitCards(feed, cards);
    }
  };
  let refit = 0;
  window.addEventListener("resize", () => {
    cancelAnimationFrame(refit);
    refit = requestAnimationFrame(() => fit());
  });

  const open = (index) => {
    viewer.showModal();
    fit();
    scrollTo(index, false);
    loadRest();
  };
  section.querySelectorAll(".home-instagram-thumb").forEach((thumb) => {
    thumb.disabled = false;
    thumb.addEventListener("click", () => open(Number(thumb.dataset.index)));
  });

  const toggle = section.querySelector(".home-instagram-toggle");
  const showMore = toggle && toggle.querySelector("summary");
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
}

document.addEventListener("DOMContentLoaded", () => {
  wire(document);
  document.querySelectorAll(".instagram_container").forEach(setUpViewer);
});
