document.addEventListener("DOMContentLoaded", () => {
  const panel = document.getElementById("quick-style-panel");
  const articlePage = document.querySelector(".article-page");
  // shared site-wide wrapper (home_base.html), not article-specific --
  // background color paints this one instead of .article-page itself, so
  // it also covers the site's own left/right padding around the content
  // column (see article_page.html's maincontent_style block).
  const mainContent = document.querySelector(".maincontent");
  if (!panel || !articlePage || !mainContent) {
    return;
  }

  const paddingInput = document.getElementById("quick-style-padding");
  const paddingValue = document.getElementById("quick-style-padding-value");
  const fontSizeInput = document.getElementById("quick-style-font-size");
  const fontSizeValue = document.getElementById("quick-style-font-size-value");
  const alignmentGroup = document.getElementById("quick-style-alignment");
  const bgEnabledInput = document.getElementById("quick-style-bg-enabled");
  const bgColorField = document.getElementById("quick-style-bg-color-field");
  const bgColorGroup = document.getElementById("quick-style-bg-color");
  const bgCustomColorInput = document.getElementById("quick-style-bg-custom-color");
  const bgPickerInput = document.getElementById("quick-style-bg-picker");
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

  // background color -- same swatch-row + hex-chip-with-picker-button
  // control as the per-block box styling panel (article_block_style.js),
  // just for the whole article body's own background. Reimplemented here
  // rather than shared, same as the alignment buttons above already are --
  // this panel edits one fixed ArticlePage's own fields directly (server-
  // rendered initial values), not whichever block a trigger last opened.
  const applyBgColor = () => {
    if (!bgEnabledInput.checked) {
      mainContent.style.backgroundColor = "";
      return;
    }
    const color = bgColorGroup.dataset.value;
    mainContent.style.backgroundColor =
      color === "custom" ? bgCustomColorInput.value || "var(--color-bg-light)" : `var(--color-${color})`;
  };

  const normalizeHex = (value) => {
    const match = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.exec((value || "").trim());
    if (!match) {
      return null;
    }
    let hex = match[1];
    if (hex.length === 3) {
      hex = hex
        .split("")
        .map((c) => c + c)
        .join("");
    }
    return `#${hex.toLowerCase()}`;
  };

  const contrastTextColor = (hex) => {
    const int = parseInt(hex.slice(1), 16);
    const r = (int >> 16) & 255;
    const g = (int >> 8) & 255;
    const b = int & 255;
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.6 ? "#000000" : "#ffffff";
  };

  const setCustomSwatch = (hex) => {
    bgCustomColorInput.value = hex || "";
    if (hex) {
      bgCustomColorInput.style.backgroundColor = hex;
      bgCustomColorInput.style.color = contrastTextColor(hex);
    } else {
      bgCustomColorInput.style.backgroundColor = "";
      bgCustomColorInput.style.color = "";
    }
    bgPickerInput.value = hex || "#ffffff";
  };

  const selectBgSwatch = (swatch) => {
    bgColorGroup.dataset.value = swatch.dataset.color;
    bgColorGroup.querySelectorAll(".color-swatch").forEach((s) => {
      s.classList.toggle("active", s === swatch);
    });
    applyBgColor();
    window.ifiUnsavedChanges.markDirty("quickStyle");
  };

  bgColorGroup.querySelectorAll("button.color-swatch").forEach((button) => {
    button.addEventListener("click", () => selectBgSwatch(button));
  });

  // same "outer box is the button" first-click behavior as the per-block
  // box panel's own custom swatch -- while custom isn't the active choice,
  // the whole hex-chip+picker box just selects it on the first click
  // (reapplying whatever hex was already there) instead of immediately
  // focusing the text field or opening the picker.
  const customGroupEl = bgCustomColorInput.closest(".color-swatch-custom-group");
  customGroupEl.addEventListener("mousedown", (event) => {
    if (bgColorGroup.dataset.value === "custom") {
      return;
    }
    event.preventDefault();
  });
  customGroupEl.addEventListener("click", (event) => {
    if (bgColorGroup.dataset.value === "custom") {
      return;
    }
    event.preventDefault();
    selectBgSwatch(bgCustomColorInput);
  });

  bgCustomColorInput.addEventListener("input", () => {
    const hex = normalizeHex(bgCustomColorInput.value);
    if (!hex) {
      return;
    }
    setCustomSwatch(hex);
    selectBgSwatch(bgCustomColorInput);
  });

  bgPickerInput.addEventListener("input", () => {
    setCustomSwatch(bgPickerInput.value);
    selectBgSwatch(bgCustomColorInput);
  });

  bgEnabledInput.addEventListener("change", () => {
    bgColorField.hidden = !bgEnabledInput.checked;
    applyBgColor();
    window.ifiUnsavedChanges.markDirty("quickStyle");
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

    setCustomSwatch(null);
    const defaultBgButton = bgColorGroup.querySelector(
      `button[data-color="${panel.dataset.defaultBgColor}"]`
    );
    if (defaultBgButton) {
      defaultBgButton.click();
    }
    bgEnabledInput.checked = false;
    bgEnabledInput.dispatchEvent(new Event("change"));
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
        content_bg_enabled: bgEnabledInput.checked,
        content_bg_color: bgColorGroup.dataset.value,
        content_bg_custom_color: bgCustomColorInput.value,
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
