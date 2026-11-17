// The homepage's Ifi Instagram feed:
// - "… more" / "less" opens and folds a caption in place (the button stays
//   hidden without this script);
// - album arrows and dots (without the script the strip still swipes);
// - the viewer: clicking a post opens a <dialog> at that post, which
//   scrolls vertically through all posts, one screen each. It starts with
//   the homepage's 12 and fetches the rest of the stored posts the first
//   time it opens (data-more-url);
// - on screens matching SHOW_MORE_OPENS_VIEWER, "Show more" opens the viewer
//   at the first hidden post instead of opening the rest of the list;
// - the viewer hides posts this browser has seen (switch in the pill at
//   the top, with the position and how many are hidden).
// Design rationale: docs/claude_context/home_instagram.md

// Where "Show more" opens the viewer instead of the rest of the list: every
// screen (user, 2026-11-15). A media query such as "(max-width: 45rem)"
// limits it to phones again.
const SHOW_MORE_OPENS_VIEWER = "all";

const hasObserver = "IntersectionObserver" in window;

// Viewer videos play once at least half in view and pause when scrolled
// past (user, 2026-11-15: autoplay with sound, looping). If the browser
// blocks sound, the video plays muted; muting or unmuting carries over to
// the next video.
let startMuted = false;

function autoplay(video) {
  video.muted = startMuted;
  video.play().catch((error) => {
    if (error.name === "NotAllowedError" && !video.muted) {
      video.muted = true;
      video.play().catch(() => {});
    }
  });
}

const viewerVideos = hasObserver
  ? new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const video = entry.target;
          if (entry.intersectionRatio >= 0.5) {
            if (video.paused) {
              autoplay(video);
            }
          } else if (!video.paused) {
            video.pause();
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
  const sample = cards.find((card) => !card.hidden) || cards[0];
  const cardStyle = getComputedStyle(sample);
  const padX = parseFloat(cardStyle.paddingLeft) + parseFloat(cardStyle.paddingRight);
  const padY = parseFloat(cardStyle.paddingTop) + parseFloat(cardStyle.paddingBottom);
  const inner = feed.clientWidth - parseFloat(feedStyle.paddingLeft) - parseFloat(feedStyle.paddingRight) - padX;
  const mediaHeight = sample.clientHeight - padY;
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

// Hide seen posts (user, 2026-11-17): the viewer remembers, in this browser
// only, which posts were at least half on screen for SEEN_AFTER ms, and
// hides them the next time it opens. The list is read when the viewer
// opens, so nothing vanishes while scrolling. The homepage feed shows
// every post as before.
const SEEN_KEY = "ifi-instagram-seen";
const HIDE_SEEN_KEY = "ifi-instagram-hide-seen";
const SEEN_KEPT = 500;
const SEEN_AFTER = 1000;

function readSeen() {
  try {
    const seen = JSON.parse(localStorage.getItem(SEEN_KEY));
    return Array.isArray(seen) ? seen : [];
  } catch {
    return [];
  }
}

function rememberSeen(id) {
  try {
    const seen = readSeen().filter((other) => other !== id);
    seen.push(id);
    localStorage.setItem(SEEN_KEY, JSON.stringify(seen.slice(-SEEN_KEPT)));
  } catch {
    // Storage is blocked: nothing is remembered, nothing gets hidden.
  }
}

function readHideSeen() {
  try {
    return localStorage.getItem(HIDE_SEEN_KEY) !== "off";
  } catch {
    return true;
  }
}

function saveHideSeen(on) {
  try {
    localStorage.setItem(HIDE_SEEN_KEY, on ? "on" : "off");
  } catch {
    // Storage is blocked: the switch only lasts until the page reloads.
  }
}

const seenTimers = new Map();
const seenCards = hasObserver
  ? new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const card = entry.target;
          if (entry.intersectionRatio >= 0.5) {
            if (!seenTimers.has(card)) {
              const timer = setTimeout(() => {
                seenTimers.delete(card);
                rememberSeen(card.dataset.post);
              }, SEEN_AFTER);
              seenTimers.set(card, timer);
            }
          } else if (seenTimers.has(card)) {
            clearTimeout(seenTimers.get(card));
            seenTimers.delete(card);
          }
        });
      },
      { threshold: [0, 0.5] },
    )
  : null;

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
  root.querySelectorAll(".home-instagram-video").forEach((video) => {
    video.addEventListener("volumechange", () => {
      startMuted = video.muted;
    });
    if (viewerVideos) {
      viewerVideos.observe(video);
    }
  });
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
  const end = feed.querySelector(".home-instagram-viewer-end");
  const posts = () => [...feed.querySelectorAll(".home-instagram-viewer-post[data-post]")];
  const shown = () => [...feed.querySelectorAll(".home-instagram-viewer-post:not([hidden])")];
  const watchSeen = (cards) => {
    if (seenCards) {
      cards.forEach((card) => seenCards.observe(card));
    }
  };
  watchSeen(posts());

  // The seen state of this open: what was seen when it opened, the switch,
  // and the post opened from the homepage, which is always shown.
  let hideSeen = readHideSeen();
  let seenAtOpen = new Set();
  let keep = null;
  // The pill at the top of the viewer: "1 / 211 new · 3 seen hidden" and
  // the switch (shown once anything has been seen).
  const status = viewer.querySelector(".home-instagram-viewer-status");
  const position = status.querySelector(".home-instagram-viewer-position");
  const hiddenText = status.querySelector(".home-instagram-viewer-hidden");
  const toggleLabel = status.querySelector(".home-instagram-seen-switch");
  const toggleInput = toggleLabel.querySelector("input");
  let visiblePosts = [];
  let filtering = false;
  const applySeen = () => {
    const cards = posts();
    let hiddenCount = 0;
    cards.forEach((card) => {
      card.hidden = hideSeen && card !== keep && seenAtOpen.has(card.dataset.post);
      hiddenCount += card.hidden ? 1 : 0;
      const media = card.querySelector(".home-instagram-media");
      if (!card.hidden && seenAtOpen.has(card.dataset.post)) {
        media.dataset.seen = feed.dataset.seenLabel;
      } else {
        delete media.dataset.seen;
      }
    });
    visiblePosts = cards.filter((card) => !card.hidden);
    filtering = hideSeen && hiddenCount > 0;
    hiddenText.textContent = filtering
      ? `· ${feed.dataset.hiddenCount.replace("{n}", hiddenCount)}`
      : "";
    toggleLabel.hidden = !cards.some((card) => seenAtOpen.has(card.dataset.post));
    toggleInput.checked = hideSeen;
    toggleLabel.querySelector("span").textContent = hideSeen
      ? toggleLabel.dataset.on
      : toggleLabel.dataset.off;
    status.hidden = false;
    end.hidden = !filtering;
    feed.append(end);
  };

  // The rest of the stored posts, fetched the first time it opens (again on
  // a later open if that failed). Same newest-first order, so the homepage's
  // indexes still point at the right cards.
  let loading = null;
  let loaded = false;
  const loadRest = () => {
    if (!viewer.dataset.moreUrl || loaded) {
      return Promise.resolve();
    }
    if (loading) {
      return loading;
    }
    loading = fetch(viewer.dataset.moreUrl, { credentials: "same-origin" })
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
        watchSeen(cards);
        applySeen();
        fit(cards);
        showPosition();
      })
      .catch(() => {})
      .finally(() => {
        loading = null;
      });
    return loading;
  };

  const scrollToCard = (card, smooth) => {
    if (card) {
      card.scrollIntoView({ block: "start", behavior: smooth ? "smooth" : "auto" });
    }
  };
  const currentIndex = (cards) => {
    const top = feed.getBoundingClientRect().top;
    let best = 0;
    let distance = Infinity;
    cards.forEach((post, i) => {
      const d = Math.abs(post.getBoundingClientRect().top - top);
      if (d < distance) {
        distance = d;
        best = i;
      }
    });
    return best;
  };

  const currentCard = () => {
    const cards = shown();
    return cards[currentIndex(cards)];
  };
  const showPosition = () => {
    const card = currentCard();
    if (!card) {
      return;
    }
    if (filtering) {
      const i = visiblePosts.indexOf(card);
      const n = i === -1 ? visiblePosts.length : i + 1;
      position.textContent = `${n} / ${visiblePosts.length} ${feed.dataset.new}`;
    } else if (card.dataset.index) {
      position.textContent = `${Number(card.dataset.index) + 1} / ${feed.dataset.total}`;
    }
  };
  let reposition = 0;
  feed.addEventListener(
    "scroll",
    () => {
      cancelAnimationFrame(reposition);
      reposition = requestAnimationFrame(showPosition);
    },
    { passive: true },
  );

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

  // A clicked post opens even if seen. "Show more" (fromShowMore) opens at
  // the first post from `index` on that isn't hidden, else the end card.
  const open = (index, fromShowMore = false) => {
    seenAtOpen = new Set(readSeen());
    const card = feed.querySelector(`.home-instagram-viewer-post[data-index="${index}"]`);
    keep = fromShowMore ? null : card;
    viewer.showModal();
    applySeen();
    fit();
    const firstUnseen = () => {
      const cards = posts();
      const start = Math.max(cards.indexOf(card), 0);
      return cards.slice(start).find((other) => !other.hidden) || end;
    };
    const target = fromShowMore ? firstUnseen() : card;
    scrollToCard(target, false);
    showPosition();
    // Only the 12 newest are here yet: if they're all seen, wait for the
    // rest before settling on the end card.
    loadRest().then(() => {
      if (target === end && viewer.open && currentCard() === end) {
        scrollToCard(firstUnseen(), false);
        showPosition();
      }
    });
  };

  // The switch in the pill, and "Show them anyway" on the end card.
  // Turning it on hides the current post too, if it was seen (user), and
  // moves to the next shown post; turning it off stays on the current one.
  const setHideSeen = (on, card) => {
    hideSeen = on;
    saveHideSeen(on);
    keep = null;
    applySeen();
    fit();
    const cards = posts();
    const target =
      card && card.hidden
        ? cards.slice(cards.indexOf(card)).find((other) => !other.hidden) || end
        : card;
    scrollToCard(target, false);
    showPosition();
  };
  toggleInput.addEventListener("change", () => {
    const card = currentCard();
    setHideSeen(toggleInput.checked, card === end ? null : card);
  });
  end.querySelector(".home-instagram-show-seen").addEventListener("click", () => {
    const firstHidden = posts().find((card) => card.hidden);
    setHideSeen(false, firstHidden);
  });
  section.querySelectorAll(".home-instagram-thumb").forEach((thumb) => {
    thumb.disabled = false;
    thumb.addEventListener("click", () => open(Number(thumb.dataset.index)));
  });

  // "Show more" under the heading opens the viewer from the newest post that
  // isn't hidden. With it, laptops hide the bottom "Show more" (CSS,
  // .has-viewer); phones keep both, since their posts are stacked.
  const viewAll = section.querySelector(".home-instagram-view-all");
  if (viewAll) {
    viewAll.hidden = false;
    viewAll.addEventListener("click", () => open(0, true));
    section.classList.add("has-viewer");
  }

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
      open(firstHidden === -1 ? 0 : firstHidden, true);
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
      const cards = shown();
      const next = currentIndex(cards) + (event.key === "ArrowDown" ? 1 : -1);
      scrollToCard(cards[Math.max(0, Math.min(cards.length - 1, next))], true);
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
