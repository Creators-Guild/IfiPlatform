document.addEventListener("DOMContentLoaded", () => {
  const panel = document.getElementById("quick-style-panel");
  const articlePage = document.querySelector(".article-page");
  if (!panel || !articlePage) {
    return;
  }

  const paddingInput = document.getElementById("quick-style-padding");
  const paddingValue = document.getElementById("quick-style-padding-value");
  const fontSizeInput = document.getElementById("quick-style-font-size");
  const fontSizeValue = document.getElementById("quick-style-font-size-value");
  const alignmentGroup = document.getElementById("quick-style-alignment");
  const statusEl = document.getElementById("quick-style-status");
  const minimizeButton = document.getElementById("quick-style-minimize");
  const MINIMIZED_KEY = "ifiQuickStyleMinimized";

  const applyMinimized = (isMinimized) => {
    panel.classList.toggle("is-minimized", isMinimized);
    minimizeButton.setAttribute("aria-expanded", String(!isMinimized));
    minimizeButton.textContent = isMinimized ? "+" : "−";
  };

  applyMinimized(localStorage.getItem(MINIMIZED_KEY) === "true");

  minimizeButton.addEventListener("click", () => {
    const isMinimized = !panel.classList.contains("is-minimized");
    localStorage.setItem(MINIMIZED_KEY, String(isMinimized));
    applyMinimized(isMinimized);
  });

  // live preview only -- writes straight to the same CSS custom properties
  // the server-rendered inline style set on page load, no network round trip.
  paddingInput.addEventListener("input", () => {
    articlePage.style.setProperty("--content-side-padding", `${paddingInput.value}rem`);
    paddingValue.textContent = paddingInput.value;
    window.ifiUnsavedChanges.markDirty("quickStyle");
  });

  fontSizeInput.addEventListener("input", () => {
    articlePage.style.setProperty("--content-font-size", `${fontSizeInput.value}rem`);
    fontSizeValue.textContent = fontSizeInput.value;
    window.ifiUnsavedChanges.markDirty("quickStyle");
  });

  alignmentGroup.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      const align = button.dataset.align;
      alignmentGroup.dataset.value = align;
      articlePage.style.setProperty("--content-alignment", align);
      alignmentGroup.querySelectorAll("button").forEach((b) => {
        b.classList.toggle("active", b === button);
      });
      window.ifiUnsavedChanges.markDirty("quickStyle");
    });
  });

  // sets each field to its default and replays the same input/click each
  // one already listens for, rather than duplicating what those listeners
  // do -- same trick as article_block_style.js's own reset button.
  const resetButton = document.getElementById("quick-style-reset");
  resetButton.addEventListener("click", () => {
    if (!window.confirm("Reset the global style to its default values? Unsaved changes will be lost.")) {
      return;
    }

    paddingInput.value = panel.dataset.defaultPadding;
    paddingInput.dispatchEvent(new Event("input"));

    fontSizeInput.value = panel.dataset.defaultFontSize;
    fontSizeInput.dispatchEvent(new Event("input"));

    const defaultAlignButton = alignmentGroup.querySelector(
      `button[data-align="${panel.dataset.defaultAlignment}"]`
    );
    if (defaultAlignButton) {
      defaultAlignButton.click();
    }
  });

  // returns a Promise<{ok, error}> -- this panel has no Save button of its
  // own, so the only way this ever runs is via registerSaveHandler below,
  // called by the global save bar/unsaved-changes modal (article_unsaved_
  // changes.js). The error string travels with the result so those can show
  // what actually went wrong even though this panel might not be visible
  // at the time.
  const save = () => {
    statusEl.textContent = "Saving...";
    statusEl.classList.remove("is-error");

    const csrfToken = panel.querySelector("[name=csrfmiddlewaretoken]").value;

    return fetch(panel.dataset.quickStyleUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({
        content_side_padding: paddingInput.value,
        content_alignment: alignmentGroup.dataset.value,
        content_font_size: fontSizeInput.value,
      }),
    })
      .then((response) =>
        response.json().then((data) => ({ ok: response.ok, data }))
      )
      .then(({ ok, data }) => {
        if (ok) {
          statusEl.textContent = "Saved";
          window.ifiUnsavedChanges.markClean("quickStyle");
          return { ok: true };
        }
        const error = data.error || "Failed to save global style.";
        statusEl.textContent = error;
        statusEl.classList.add("is-error");
        return { ok: false, error };
      })
      .catch(() => {
        const error = "Failed to save global style (network error).";
        statusEl.textContent = error;
        statusEl.classList.add("is-error");
        return { ok: false, error };
      });
  };

  // no Save button of its own -- registered here so the global floating
  // save bar (article_save_bar.html) can trigger it instead.
  window.ifiUnsavedChanges.registerSaveHandler(save);
});
