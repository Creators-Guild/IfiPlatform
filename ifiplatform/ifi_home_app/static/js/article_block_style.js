document.addEventListener("DOMContentLoaded", () => {
  const panel = document.getElementById("block-style-mini-panel");
  if (!panel) {
    return;
  }

  // which fields apply to each block type, and (for alignment) which class
  // prefix + possible values that block's template actually uses to express
  // it -- styled_text and multi_column both have "alignment"-shaped
  // concepts in the model, but multi_column's is column_alignment (top/
  // center/bottom vertical layout, a different axis entirely), not left/
  // center/right text alignment, so it's deliberately left out here.
  const FIELDS_BY_TYPE = {
    styled_text: ["side_padding", "alignment", "font_size"],
    image: ["alignment", "width_rem"],
    multi_column: ["side_padding"],
    // not a StreamField block -- the title/intro/meta group above the body,
    // wrapped together so they share one trigger (see article_page.html's
    // .article-header). Saved separately via save_header_style, plain
    // ArticlePage fields rather than an ArticleBlockStyle row.
    article_header: ["title_alignment", "intro_alignment", "meta_alignment"],
  };
  const CLASS_SWAP = {
    styled_text: { alignment: { prefix: "prose--align-", values: ["left", "center", "right"] } },
    image: { alignment: { prefix: "body-image--", values: ["left", "center", "right"] } },
  };

  // .prose sitting beside a floated image (hero or body) doesn't shrink its
  // own box to the narrower wrapped-text width -- only the text itself
  // wraps, the box stays full container width, running underneath the
  // float. The trigger's CSS default (top:0.25rem; right:0.25rem, anchored
  // to that full-width box) lands near the float's far edge instead of
  // where the text actually is. Rather than trying to measure exactly
  // where text wraps (fragile with rich text markup), find any floated
  // image whose vertical range overlaps the icon's row and place the icon
  // right at that float's own edge instead -- simpler and directly targets
  // what we're actually trying to avoid overlapping. Re-run on resize
  // (float geometry changes) and once each image finishes loading (no
  // intrinsic height before then, so float geometry isn't final yet).
  const positionTextTriggers = () => {
    const floats = Array.from(
      document.querySelectorAll(".hero-image-figure, .body-image-figure")
    ).filter((el) => ["left", "right"].includes(getComputedStyle(el).float));

    document.querySelectorAll(".prose.editable-block").forEach((blockEl) => {
      const trigger = blockEl.querySelector(".block-style-trigger");
      if (!trigger) {
        return;
      }
      // a multi-column item is a flex item, which per spec establishes its
      // own formatting context -- it's never affected by a float outside
      // the grid (that's also what keeps text from spilling across
      // columns), so there's nothing to avoid in here. Without this, a
      // same-page-height float completely unrelated to this column (e.g.
      // the hero image, well above/beside the grid) could still register
      // as "overlapping" by pure Y-coordinate coincidence and shove this
      // trigger somewhere that collides with the multi-column block's own
      // trigger (top-right of the whole grid, not any one column).
      if (blockEl.closest(".multi-col-item")) {
        trigger.style.top = "";
        trigger.style.right = "";
        trigger.style.left = "";
        return;
      }
      const blockRect = blockEl.getBoundingClientRect();
      const iconRowTop = blockRect.top + 4; // roughly where the icon sits, in CSS px from the top
      const iconRowBottom = iconRowTop + 28; // icon's own height (1.75rem) plus a little slack

      const overlapping = floats.find((floatEl) => {
        const fr = floatEl.getBoundingClientRect();
        return (
          fr.top < iconRowBottom &&
          fr.bottom > iconRowTop &&
          fr.left < blockRect.right &&
          fr.right > blockRect.left
        );
      });

      if (!overlapping) {
        trigger.style.top = "";
        trigger.style.right = "";
        trigger.style.left = "";
        return;
      }

      const floatRect = overlapping.getBoundingClientRect();
      const floatSide = getComputedStyle(overlapping).float;
      trigger.style.top = "0.25rem";
      if (floatSide === "right") {
        trigger.style.right = `${Math.max(blockRect.right - floatRect.left + 8, 2)}px`;
        trigger.style.left = "auto";
      } else {
        trigger.style.left = `${Math.max(floatRect.right - blockRect.left + 8, 2)}px`;
        trigger.style.right = "auto";
      }
    });
  };

  positionTextTriggers();
  window.addEventListener("resize", positionTextTriggers);
  document.querySelectorAll(".hero-image, .body-image").forEach((img) => {
    if (img.complete) {
      return;
    }
    img.addEventListener("load", positionTextTriggers);
  });

  const targetIdInput = document.getElementById("block-style-target-id");
  const targetTypeInput = document.getElementById("block-style-target-type");
  const paddingInput = document.getElementById("block-style-padding");
  const paddingValue = document.getElementById("block-style-padding-value");
  const fontSizeInput = document.getElementById("block-style-font-size");
  const fontSizeValue = document.getElementById("block-style-font-size-value");
  const widthInput = document.getElementById("block-style-width");
  const widthValue = document.getElementById("block-style-width-value");
  const alignmentGroup = document.getElementById("block-style-alignment");
  const titleAlignmentGroup = document.getElementById("block-style-title-alignment");
  const introAlignmentGroup = document.getElementById("block-style-intro-alignment");
  const metaAlignmentGroup = document.getElementById("block-style-meta-alignment");
  const statusEl = document.getElementById("block-style-mini-panel-status");

  let currentBlockEl = null;
  let currentTrigger = null;

  const swapClass = (blockEl, blockType, field, value) => {
    const swap = (CLASS_SWAP[blockType] || {})[field];
    if (!swap) {
      return;
    }
    swap.values.forEach((v) => {
      blockEl.classList.remove(swap.prefix + v);
    });
    blockEl.classList.add(swap.prefix + value);
  };

  const wireButtonGroup = (group, field, dataAttr) => {
    group.querySelectorAll("button").forEach((button) => {
      button.addEventListener("click", () => {
        if (!currentBlockEl) {
          return;
        }
        const value = button.dataset[dataAttr];
        group.dataset.value = value;
        currentBlockEl.dataset[field] = value;
        swapClass(currentBlockEl, targetTypeInput.value, field, value);
        group.querySelectorAll("button").forEach((b) => {
          b.classList.toggle("active", b === button);
        });
        positionTextTriggers();
      });
    });
  };

  // article_header's three alignment groups aren't class-based (h1/.intro/
  // .article-meta each read their own CSS custom property, see
  // article_layout.css) -- live preview writes straight to that property on
  // the wrapper instead of swapping a class.
  const wireHeaderAlignmentGroup = (group, cssVar, datasetKey) => {
    group.querySelectorAll("button").forEach((button) => {
      button.addEventListener("click", () => {
        if (!currentBlockEl) {
          return;
        }
        const value = button.dataset.align;
        group.dataset.value = value;
        currentBlockEl.dataset[datasetKey] = value;
        currentBlockEl.style.setProperty(cssVar, value);
        group.querySelectorAll("button").forEach((b) => {
          b.classList.toggle("active", b === button);
        });
      });
    });
  };

  const closePanel = () => {
    panel.hidden = true;
    if (currentTrigger) {
      currentTrigger.classList.remove("is-open");
    }
    if (currentBlockEl) {
      currentBlockEl.classList.remove("is-editing");
    }
    currentBlockEl = null;
    currentTrigger = null;
  };

  const openPanelFor = (trigger) => {
    const blockEl = trigger.closest(".editable-block");
    if (!blockEl) {
      return;
    }
    currentBlockEl = blockEl;
    currentTrigger = trigger;
    currentBlockEl.classList.add("is-editing");

    const blockType = blockEl.dataset.blockType;
    const visibleFields = FIELDS_BY_TYPE[blockType] || [];

    panel.querySelectorAll("[data-style-field]").forEach((field) => {
      field.hidden = !visibleFields.includes(field.dataset.styleField);
    });

    targetIdInput.value = blockEl.dataset.blockId;
    targetTypeInput.value = blockType;
    statusEl.textContent = "";
    statusEl.classList.remove("is-error");

    if (visibleFields.includes("side_padding")) {
      paddingInput.value = blockEl.dataset.sidePadding;
      paddingValue.textContent = blockEl.dataset.sidePadding;
    }
    if (visibleFields.includes("font_size")) {
      fontSizeInput.value = blockEl.dataset.fontSize;
      fontSizeValue.textContent = blockEl.dataset.fontSize;
    }
    if (visibleFields.includes("width_rem")) {
      widthInput.value = blockEl.dataset.widthRem;
      widthValue.textContent = blockEl.dataset.widthRem;
    }
    if (visibleFields.includes("alignment")) {
      alignmentGroup.dataset.value = blockEl.dataset.alignment;
      alignmentGroup.querySelectorAll("button").forEach((b) => {
        b.classList.toggle("active", b.dataset.align === blockEl.dataset.alignment);
      });
    }
    [
      [titleAlignmentGroup, "title_alignment", "titleAlignment"],
      [introAlignmentGroup, "intro_alignment", "introAlignment"],
      [metaAlignmentGroup, "meta_alignment", "metaAlignment"],
    ].forEach(([group, field, datasetKey]) => {
      if (!visibleFields.includes(field)) {
        return;
      }
      group.dataset.value = blockEl.dataset[datasetKey];
      group.querySelectorAll("button").forEach((b) => {
        b.classList.toggle("active", b.dataset.align === blockEl.dataset[datasetKey]);
      });
    });

    panel.hidden = false;
    trigger.classList.add("is-open");

    const rect = trigger.getBoundingClientRect();
    const panelWidth = panel.offsetWidth || 224;
    let left = rect.right - panelWidth;
    left = Math.max(8, Math.min(left, window.innerWidth - panelWidth - 8));
    panel.style.top = `${rect.bottom + 8}px`;
    panel.style.left = `${left}px`;
  };

  document.querySelectorAll(".block-style-trigger").forEach((trigger) => {
    trigger.addEventListener("click", (event) => {
      event.stopPropagation();
      if (currentTrigger === trigger) {
        closePanel();
      } else {
        openPanelFor(trigger);
      }
    });
  });

  document.addEventListener("click", (event) => {
    if (!panel.hidden && !panel.contains(event.target)) {
      closePanel();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) {
      closePanel();
    }
  });

  paddingInput.addEventListener("input", () => {
    if (!currentBlockEl) {
      return;
    }
    currentBlockEl.style.paddingLeft = `${paddingInput.value}rem`;
    currentBlockEl.style.paddingRight = `${paddingInput.value}rem`;
    currentBlockEl.dataset.sidePadding = paddingInput.value;
    paddingValue.textContent = paddingInput.value;
    positionTextTriggers();
  });

  fontSizeInput.addEventListener("input", () => {
    if (!currentBlockEl) {
      return;
    }
    currentBlockEl.style.fontSize = `${fontSizeInput.value}rem`;
    currentBlockEl.dataset.fontSize = fontSizeInput.value;
    fontSizeValue.textContent = fontSizeInput.value;
    positionTextTriggers();
  });

  widthInput.addEventListener("input", () => {
    if (!currentBlockEl) {
      return;
    }
    currentBlockEl.style.width = `${widthInput.value}rem`;
    currentBlockEl.dataset.widthRem = widthInput.value;
    widthValue.textContent = widthInput.value;
    positionTextTriggers();
  });

  wireButtonGroup(alignmentGroup, "alignment", "align");
  wireHeaderAlignmentGroup(titleAlignmentGroup, "--title-alignment", "titleAlignment");
  wireHeaderAlignmentGroup(introAlignmentGroup, "--intro-alignment", "introAlignment");
  wireHeaderAlignmentGroup(metaAlignmentGroup, "--meta-alignment", "metaAlignment");

  const saveViaFetch = (url, payload) => {
    const csrfToken = panel.querySelector("[name=csrfmiddlewaretoken]").value;
    fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify(payload),
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
  };

  panel.addEventListener("submit", (event) => {
    event.preventDefault();
    statusEl.textContent = "Saving...";
    statusEl.classList.remove("is-error");

    const blockType = targetTypeInput.value;

    // article_header isn't a StreamField block -- it saves plain ArticlePage
    // fields via a separate endpoint, not an ArticleBlockStyle row keyed by
    // block_id.
    if (blockType === "article_header") {
      saveViaFetch(panel.dataset.headerSaveUrl, {
        title_alignment: titleAlignmentGroup.dataset.value,
        intro_alignment: introAlignmentGroup.dataset.value,
        meta_alignment: metaAlignmentGroup.dataset.value,
      });
      return;
    }

    const visibleFields = FIELDS_BY_TYPE[blockType] || [];
    saveViaFetch(panel.dataset.saveUrl, {
      block_id: targetIdInput.value,
      block_type: blockType,
      side_padding: visibleFields.includes("side_padding") ? paddingInput.value : null,
      alignment: visibleFields.includes("alignment") ? alignmentGroup.dataset.value : null,
      font_size: visibleFields.includes("font_size") ? fontSizeInput.value : null,
      width_rem: visibleFields.includes("width_rem") ? widthInput.value : null,
    });
  });
});
