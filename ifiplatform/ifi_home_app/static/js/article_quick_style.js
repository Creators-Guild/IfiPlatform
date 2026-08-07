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

  // live preview only -- writes straight to the same CSS custom properties
  // the server-rendered inline style set on page load, no network round trip.
  paddingInput.addEventListener("input", () => {
    articlePage.style.setProperty("--content-side-padding", `${paddingInput.value}rem`);
    paddingValue.textContent = paddingInput.value;
  });

  fontSizeInput.addEventListener("input", () => {
    articlePage.style.setProperty("--content-font-size", `${fontSizeInput.value}rem`);
    fontSizeValue.textContent = fontSizeInput.value;
  });

  alignmentGroup.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      const align = button.dataset.align;
      alignmentGroup.dataset.value = align;
      articlePage.style.setProperty("--content-alignment", align);
      alignmentGroup.querySelectorAll("button").forEach((b) => {
        b.classList.toggle("active", b === button);
      });
    });
  });

  panel.addEventListener("submit", (event) => {
    event.preventDefault();
    statusEl.textContent = "Saving...";
    statusEl.classList.remove("is-error");

    const csrfToken = panel.querySelector("[name=csrfmiddlewaretoken]").value;

    fetch(panel.dataset.quickStyleUrl, {
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
        } else {
          statusEl.textContent = data.error || "Failed to save.";
          statusEl.classList.add("is-error");
        }
      })
      .catch(() => {
        statusEl.textContent = "Failed to save.";
        statusEl.classList.add("is-error");
      });
  });
});
