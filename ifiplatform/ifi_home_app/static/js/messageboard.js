document.addEventListener("DOMContentLoaded", () => {
  const setupScrollbar = (slide) => {
    const body = slide.querySelector(".messageboard-body");
    const track = slide.querySelector(".messageboard-scrollbar");
    const thumb = slide.querySelector(".messageboard-scrollbar-thumb");
    if (!body || !track || !thumb) {
      return () => {};
    }

    const update = () => {
      const { scrollHeight, clientHeight, scrollTop } = body;
      if (scrollHeight <= clientHeight) {
        thumb.style.display = "none";
        return;
      }
      const trackHeight = track.clientHeight;
      const thumbHeight = Math.max((clientHeight / scrollHeight) * trackHeight, 24);
      const maxThumbTop = trackHeight - thumbHeight;
      const scrollRatio = scrollTop / (scrollHeight - clientHeight);
      thumb.style.display = "block";
      thumb.style.height = `${thumbHeight}px`;
      thumb.style.top = `${scrollRatio * maxThumbTop}px`;
    };

    body.addEventListener("scroll", update);
    if (window.ResizeObserver) {
      new ResizeObserver(update).observe(body);
    }

    let dragStartY = 0;
    let dragStartScrollTop = 0;

    const onDragMove = (event) => {
      const { scrollHeight, clientHeight } = body;
      const trackHeight = track.clientHeight;
      const thumbHeight = thumb.clientHeight;
      const maxThumbTop = trackHeight - thumbHeight;
      if (maxThumbTop <= 0) {
        return;
      }
      const deltaY = event.clientY - dragStartY;
      const scrollableHeight = scrollHeight - clientHeight;
      body.scrollTop = dragStartScrollTop + (deltaY / maxThumbTop) * scrollableHeight;
    };

    const onDragEnd = () => {
      thumb.removeEventListener("pointermove", onDragMove);
      thumb.removeEventListener("pointerup", onDragEnd);
      thumb.removeEventListener("pointercancel", onDragEnd);
    };

    // Pointer Events (not mouse-only) so the thumb is actually draggable on
    // touch, not just mouse -- previously mousedown/mousemove/mouseup never
    // fire from a finger, leaving this an inert decoration on mobile and
    // forcing users to grab the bare, small message text box directly.
    // setPointerCapture keeps move/up events targeted at the thumb even as
    // a finger drifts off it mid-drag, which listening on the thumb alone
    // wouldn't otherwise give us.
    thumb.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      dragStartY = event.clientY;
      dragStartScrollTop = body.scrollTop;
      thumb.setPointerCapture(event.pointerId);
      thumb.addEventListener("pointermove", onDragMove);
      thumb.addEventListener("pointerup", onDragEnd);
      thumb.addEventListener("pointercancel", onDragEnd);
    });

    track.addEventListener("pointerdown", (event) => {
      if (event.target === thumb) {
        return;
      }
      const trackRect = track.getBoundingClientRect();
      const clickRatio = (event.clientY - trackRect.top) / trackRect.height;
      body.scrollTop = clickRatio * (body.scrollHeight - body.clientHeight);
    });

    update();
    return update;
  };

  document.querySelectorAll(".messageboard-slide").forEach((slide) => {
    setupScrollbar(slide);
  });

  document.querySelectorAll(".messageboard").forEach((board) => {
    const slides = Array.from(board.querySelectorAll(".messageboard-slide"));
    const dots = Array.from(board.querySelectorAll(".messageboard-dot"));
    const prevButton = board.querySelector(".messageboard-prev");
    const nextButton = board.querySelector(".messageboard-next");
    if (slides.length < 2) {
      return;
    }

    let currentIndex = slides.findIndex((slide) => slide.classList.contains("active"));
    if (currentIndex < 0) {
      currentIndex = 0;
    }
    if (dots[currentIndex]) {
      dots[currentIndex].classList.add("seen");
    }
    let rafId = null;

    const showSlide = (index) => {
      currentIndex = (index + slides.length) % slides.length;
      slides.forEach((slide, i) => slide.classList.toggle("active", i === currentIndex));
      dots.forEach((dot, i) => {
        dot.classList.toggle("active", i === currentIndex);
        if (i === currentIndex) {
          dot.classList.add("seen");
        } else if (dot.classList.contains("seen")) {
          dot.style.setProperty("--progress", 100);
        }
      });
    };

    const restartAutoRotate = () => {
      if (rafId) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
      if (!board.dataset.autorotate) {
        return;
      }
      const durationSeconds = parseFloat(slides[currentIndex].dataset.duration);
      const interval = durationSeconds > 0 ? durationSeconds * 1000 : 8000;
      const activeDot = dots[currentIndex];
      if (activeDot) {
        activeDot.style.setProperty("--progress", 0);
      }
      const startTime = performance.now();

      const tick = (now) => {
        const elapsed = now - startTime;
        const percent = Math.min((elapsed / interval) * 100, 100);
        if (activeDot) {
          activeDot.style.setProperty("--progress", percent);
        }
        if (elapsed >= interval) {
          showSlide(currentIndex + 1);
          restartAutoRotate();
        } else {
          rafId = requestAnimationFrame(tick);
        }
      };
      rafId = requestAnimationFrame(tick);
    };

    if (prevButton) {
      prevButton.addEventListener("click", () => {
        showSlide(currentIndex - 1);
        restartAutoRotate();
      });
    }

    if (nextButton) {
      nextButton.addEventListener("click", () => {
        showSlide(currentIndex + 1);
        restartAutoRotate();
      });
    }

    dots.forEach((dot, i) => {
      dot.addEventListener("click", () => {
        showSlide(i);
        restartAutoRotate();
      });
    });

    restartAutoRotate();
  });
});
