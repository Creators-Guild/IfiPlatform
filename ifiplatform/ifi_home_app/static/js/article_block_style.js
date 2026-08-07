document.addEventListener("DOMContentLoaded", () => {
  const panel = document.getElementById("block-style-mini-panel");
  if (!panel) {
    return;
  }

  // {block_type: {field: default_value}} -- see BLOCK_STYLE_DEFAULTS in
  // article_models.py, rendered via json_script in
  // article_block_style_mini_panel.html. Powers the "Reset to default" button.
  const defaultsScript = document.getElementById("block-style-defaults-data");
  const BLOCK_STYLE_DEFAULTS = defaultsScript ? JSON.parse(defaultsScript.textContent) : {};

  // which fields apply to each block type, and (for alignment) which class
  // prefix + possible values that block's template actually uses to express
  // it -- styled_text and multi_column both have "alignment"-shaped
  // concepts in the model, but multi_column's is column_alignment (top/
  // center/bottom vertical layout, a different axis entirely), not left/
  // center/right text alignment, so it's deliberately left out here.
  const FIELDS_BY_TYPE = {
    heading: ["side_padding", "alignment", "font_size"],
    styled_text: ["side_padding", "alignment", "font_size"],
    image: ["alignment", "width_rem", "side_padding"],
    // per-column weight fields aren't listed here -- there's a variable
    // number of them (1-4, multi_column's own min/max_num), added to this
    // at runtime in openPanelFor() based on the block actually being
    // edited (data-column-count).
    multi_column: ["side_padding", "gap"],
    // not a StreamField block -- the title/intro/meta group above the body,
    // wrapped together so they share one trigger (see article_page.html's
    // .article-header). Saved separately via save_header_style, plain
    // ArticlePage fields rather than an ArticleBlockStyle row.
    article_header: [
      "side_padding",
      "title_alignment",
      "title_font_size",
      "intro_alignment",
      "intro_font_size",
      "meta_alignment",
      "meta_font_size",
    ],
    // same fields as image, and reuses the exact same generic alignment/
    // width/padding inputs below -- also not a StreamField block though
    // (hero_image is a set of plain ArticlePage fields, see article_models.py),
    // so it needs the same special-cased save endpoint as article_header.
    hero_image: ["alignment", "width_rem", "side_padding"],
  };
  const CLASS_SWAP = {
    heading: { alignment: { prefix: "heading--align-", values: ["left", "center", "right"] } },
    styled_text: { alignment: { prefix: "prose--align-", values: ["left", "center", "right"] } },
    image: { alignment: { prefix: "body-image--", values: ["left", "center", "right"] } },
    hero_image: { alignment: { prefix: "hero-image--", values: ["left", "center", "right"] } },
  };

  // Any full-width text block (.prose, headings, the title/intro/meta
  // header) sitting beside a floated image doesn't shrink its own box to
  // the narrower wrapped-text width -- only the text itself wraps, the box
  // stays full container width, running underneath the float. The
  // trigger's CSS default (top:0.25rem; right:0.25rem, anchored to that
  // full-width box) lands near the float's far edge instead of where the
  // text actually is -- for the header specifically, that's often right
  // behind/under the hero image itself, since the header sits right above
  // it. Rather than trying to measure exactly where text wraps (fragile
  // with rich text markup), find any floated image whose vertical range
  // overlaps the icon's row and place the icon right at that float's own
  // edge instead -- simpler and directly targets what we're actually
  // trying to avoid overlapping. Re-run on resize (float geometry changes)
  // and once each image finishes loading (no intrinsic height before then,
  // so float geometry isn't final yet).
  const positionTextTriggers = () => {
    const floats = Array.from(
      document.querySelectorAll(".hero-image-figure, .body-image-figure")
    ).filter((el) => ["left", "right"].includes(getComputedStyle(el).float));

    const editableTextSelectors = [
      ".prose.editable-block",
      ".article-header.editable-block",
      "h2.editable-block",
      "h3.editable-block",
      "h4.editable-block",
      "h5.editable-block",
    ].join(", ");

    document.querySelectorAll(editableTextSelectors).forEach((blockEl) => {
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
  const titleFontSizeInput = document.getElementById("block-style-title-font-size");
  const titleFontSizeValue = document.getElementById("block-style-title-font-size-value");
  const introFontSizeInput = document.getElementById("block-style-intro-font-size");
  const introFontSizeValue = document.getElementById("block-style-intro-font-size-value");
  const metaFontSizeInput = document.getElementById("block-style-meta-font-size");
  const metaFontSizeValue = document.getElementById("block-style-meta-font-size-value");
  const gapInput = document.getElementById("block-style-gap");
  const gapValue = document.getElementById("block-style-gap-value");
  const MAX_COLUMNS = 4;
  const columnWeightInputs = Array.from({ length: MAX_COLUMNS }, (_, i) =>
    document.getElementById(`block-style-column-weight-${i}`)
  );
  const columnWeightValues = Array.from({ length: MAX_COLUMNS }, (_, i) =>
    document.getElementById(`block-style-column-weight-${i}-value`)
  );
  const statusEl = document.getElementById("block-style-mini-panel-status");

  let currentBlockEl = null;
  let currentTrigger = null;

  // one shared panel, but edits to *every* block touched since the last
  // save need to survive switching to a different block -- keyed by
  // block_id (a real block's UUID, or the fixed "article-header"/
  // "hero-image" strings for the two non-StreamField block types), each
  // value the exact {url, payload} save() would need to send for that one
  // block. Rebuilt in full on every field change (see recordPendingEdit()),
  // not just the one field that changed, since a save always POSTs a
  // block's whole set of relevant fields at once.
  const pendingEdits = new Map();

  // builds the {url, payload} save() would send for whatever block is
  // currently shown in the panel, from the panel's own current field
  // values -- reads targetTypeInput/targetIdInput/paddingInput/etc, all
  // declared above. Returns null if no block has ever been opened this
  // session (targetTypeInput.value is still "").
  const buildSaveRequest = () => {
    const blockType = targetTypeInput.value;
    if (!blockType) {
      return null;
    }

    // article_header isn't a StreamField block -- it saves plain ArticlePage
    // fields via a separate endpoint, not an ArticleBlockStyle row keyed by
    // block_id.
    if (blockType === "article_header") {
      return {
        url: panel.dataset.headerSaveUrl,
        payload: {
          title_alignment: titleAlignmentGroup.dataset.value,
          intro_alignment: introAlignmentGroup.dataset.value,
          meta_alignment: metaAlignmentGroup.dataset.value,
          header_side_padding: paddingInput.value,
          title_font_size: titleFontSizeInput.value,
          intro_font_size: introFontSizeInput.value,
          meta_font_size: metaFontSizeInput.value,
        },
      };
    }

    // hero_image isn't a StreamField block either -- plain ArticlePage
    // fields (hero_image_position/width_rem/side_padding), same reasoning
    // as article_header above.
    if (blockType === "hero_image") {
      return {
        url: panel.dataset.heroImageSaveUrl,
        payload: {
          alignment: alignmentGroup.dataset.value,
          width_rem: widthInput.value,
          side_padding: paddingInput.value,
        },
      };
    }

    const visibleFields = FIELDS_BY_TYPE[blockType] || [];
    let columnWeights = null;
    if (blockType === "multi_column") {
      // currentBlockEl can be null by the time this runs (closePanel()
      // nulls it, but a pending edit can still be flushed after that) --
      // look the block back up by id instead of relying on it.
      const blockEl =
        currentBlockEl || document.querySelector(`[data-block-id="${CSS.escape(targetIdInput.value)}"]`);
      const columnCount = parseInt(blockEl ? blockEl.dataset.columnCount : "0", 10) || 0;
      columnWeights = columnWeightInputs
        .slice(0, columnCount)
        .map((input) => parseFloat(input.value));
    }
    return {
      url: panel.dataset.saveUrl,
      payload: {
        block_id: targetIdInput.value,
        block_type: blockType,
        side_padding: visibleFields.includes("side_padding") ? paddingInput.value : null,
        alignment: visibleFields.includes("alignment") ? alignmentGroup.dataset.value : null,
        font_size: visibleFields.includes("font_size") ? fontSizeInput.value : null,
        width_rem: visibleFields.includes("width_rem") ? widthInput.value : null,
        gap: visibleFields.includes("gap") ? gapInput.value : null,
        column_weights: columnWeights,
      },
    };
  };

  // called after every live edit -- snapshots the *whole* current save
  // request for the block being edited right now, keyed by its block_id, so
  // switching to a different block afterwards doesn't lose it (see
  // pendingEdits above).
  const recordPendingEdit = () => {
    const blockId = targetIdInput.value;
    const request = buildSaveRequest();
    if (!blockId || !request) {
      return;
    }
    pendingEdits.set(blockId, request);
    window.ifiUnsavedChanges.markDirty("blockStyle");
  };

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
        recordPendingEdit();
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
        recordPendingEdit();
      });
    });
  };

  // the panel is position:fixed, so top/left are plain viewport pixels --
  // re-run on every scroll/resize while it's open (see the listeners near
  // the bottom of this file) rather than computing them once and trusting
  // some containing-block/offsetParent math to carry the panel along on
  // its own.
  const positionPanel = (trigger) => {
    const rect = trigger.getBoundingClientRect();
    const panelWidth = panel.offsetWidth || 224;
    const panelHeight = panel.offsetHeight || 0;

    let left = rect.right - panelWidth;
    left = Math.max(8, Math.min(left, window.innerWidth - panelWidth - 8));

    // default: open below the trigger. If it wouldn't fit before hitting
    // the bottom of the viewport, flip to open above it instead -- same
    // idea as the horizontal clamp above, just on the other axis and with
    // a flip instead of a slide, since sliding vertically would put the
    // panel over the trigger itself.
    let top = rect.bottom + 8;
    if (top + panelHeight > window.innerHeight - 8) {
      const above = rect.top - 8 - panelHeight;
      top = above >= 8 ? above : Math.max(8, window.innerHeight - panelHeight - 8);
    }

    panel.style.top = `${top}px`;
    panel.style.left = `${left}px`;
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
    let visibleFields = FIELDS_BY_TYPE[blockType] || [];
    if (blockType === "multi_column") {
      const columnCount = parseInt(blockEl.dataset.columnCount, 10) || 0;
      visibleFields = visibleFields.concat(
        Array.from({ length: columnCount }, (_, i) => `column_weight_${i}`)
      );
    }

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
    if (visibleFields.includes("gap")) {
      gapInput.value = blockEl.dataset.gap;
      gapValue.textContent = blockEl.dataset.gap;
    }
    if (blockType === "multi_column") {
      const weights = (blockEl.dataset.columnWeights || "")
        .split(",")
        .filter((w) => w !== "")
        .map(Number);
      weights.forEach((w, i) => {
        if (!columnWeightInputs[i]) {
          return;
        }
        columnWeightInputs[i].value = w;
        columnWeightValues[i].textContent = w;
      });
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
    [
      [titleFontSizeInput, titleFontSizeValue, "title_font_size", "titleFontSize"],
      [introFontSizeInput, introFontSizeValue, "intro_font_size", "introFontSize"],
      [metaFontSizeInput, metaFontSizeValue, "meta_font_size", "metaFontSize"],
    ].forEach(([input, valueEl, field, datasetKey]) => {
      if (!visibleFields.includes(field)) {
        return;
      }
      input.value = blockEl.dataset[datasetKey];
      valueEl.textContent = blockEl.dataset[datasetKey];
    });

    panel.hidden = false;
    trigger.classList.add("is-open");
    positionPanel(trigger);
  };

  // keep the panel anchored to its trigger while open, on both scroll
  // (capture: window scroll events don't bubble) and resize.
  const repositionIfOpen = () => {
    if (!panel.hidden && currentTrigger) {
      positionPanel(currentTrigger);
    }
  };
  window.addEventListener("scroll", repositionIfOpen, { capture: true, passive: true });
  window.addEventListener("resize", repositionIfOpen);

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

  const closeButton = document.getElementById("block-style-close");
  closeButton.addEventListener("click", (event) => {
    event.stopPropagation();
    closePanel();
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
    // article_header expresses its side padding as margin (via
    // --header-side-padding, see article_layout.css) rather than padding --
    // its border-bottom accent underline needs to move with the indent, and
    // margin does that while padding on a width:auto block wouldn't.
    if (targetTypeInput.value === "article_header") {
      currentBlockEl.style.setProperty("--header-side-padding", `${paddingInput.value}rem`);
    } else {
      currentBlockEl.style.paddingLeft = `${paddingInput.value}rem`;
      currentBlockEl.style.paddingRight = `${paddingInput.value}rem`;
    }
    currentBlockEl.dataset.sidePadding = paddingInput.value;
    paddingValue.textContent = paddingInput.value;
    positionTextTriggers();
    recordPendingEdit();
  });

  fontSizeInput.addEventListener("input", () => {
    if (!currentBlockEl) {
      return;
    }
    currentBlockEl.style.fontSize = `${fontSizeInput.value}rem`;
    currentBlockEl.dataset.fontSize = fontSizeInput.value;
    fontSizeValue.textContent = fontSizeInput.value;
    positionTextTriggers();
    recordPendingEdit();
  });

  widthInput.addEventListener("input", () => {
    if (!currentBlockEl) {
      return;
    }
    currentBlockEl.style.width = `${widthInput.value}rem`;
    currentBlockEl.dataset.widthRem = widthInput.value;
    widthValue.textContent = widthInput.value;
    positionTextTriggers();
    recordPendingEdit();
  });

  gapInput.addEventListener("input", () => {
    if (!currentBlockEl) {
      return;
    }
    currentBlockEl.style.gap = `${gapInput.value}rem`;
    currentBlockEl.dataset.gap = gapInput.value;
    gapValue.textContent = gapInput.value;
    recordPendingEdit();
  });

  // each column weight slider only ever touches its own column's flex-grow
  // (via data-col-index, see article_body_blocks.html) -- separate
  // controls for separate columns, related only by living in the same
  // multi_column block's dataset.columnWeights.
  columnWeightInputs.forEach((input, i) => {
    if (!input) {
      return;
    }
    input.addEventListener("input", () => {
      if (!currentBlockEl) {
        return;
      }
      const item = currentBlockEl.querySelector(`.multi-col-item[data-col-index="${i}"]`);
      if (item) {
        item.style.flex = `${input.value} 1 0`;
      }
      columnWeightValues[i].textContent = input.value;
      const weights = (currentBlockEl.dataset.columnWeights || "").split(",").map(Number);
      weights[i] = parseFloat(input.value);
      currentBlockEl.dataset.columnWeights = weights.join(",");
      recordPendingEdit();
    });
  });

  // title/intro/meta font size, like the header's alignment groups, write
  // straight to a CSS custom property on the wrapper (h1/.intro/.article-meta
  // each read their own, see article_layout.css/category_card.css) rather
  // than an inline font-size directly on the wrapper itself -- there's no
  // single element here that all three should apply to.
  const wireHeaderFontSizeInput = (input, valueEl, cssVar, datasetKey) => {
    input.addEventListener("input", () => {
      if (!currentBlockEl) {
        return;
      }
      currentBlockEl.style.setProperty(cssVar, `${input.value}rem`);
      currentBlockEl.dataset[datasetKey] = input.value;
      valueEl.textContent = input.value;
      recordPendingEdit();
    });
  };

  wireButtonGroup(alignmentGroup, "alignment", "align");
  wireHeaderAlignmentGroup(titleAlignmentGroup, "--title-alignment", "titleAlignment");
  wireHeaderAlignmentGroup(introAlignmentGroup, "--intro-alignment", "introAlignment");
  wireHeaderAlignmentGroup(metaAlignmentGroup, "--meta-alignment", "metaAlignment");
  wireHeaderFontSizeInput(titleFontSizeInput, titleFontSizeValue, "--title-font-size", "titleFontSize");
  wireHeaderFontSizeInput(introFontSizeInput, introFontSizeValue, "--intro-font-size", "introFontSize");
  wireHeaderFontSizeInput(metaFontSizeInput, metaFontSizeValue, "--meta-font-size", "metaFontSize");

  // pure network call, no statusEl/dirty side effects -- save() below
  // drives those centrally, since a single save() call can now flush
  // several of these in a row (one per pending block) and the status/dirty
  // state should reflect the whole batch, not each individual request.
  // Returns a Promise<{ok, error}>.
  const saveViaFetch = (url, payload) => {
    const csrfToken = panel.querySelector("[name=csrfmiddlewaretoken]").value;
    return fetch(url, {
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
      .then(({ ok, data }) =>
        ok ? { ok: true } : { ok: false, error: data.error || "Failed to save block style." }
      )
      .catch(() => ({ ok: false, error: "Failed to save block style (network error)." }));
  };

  // flushes every block in pendingEdits, one request at a time (not in
  // parallel -- see article_unsaved_changes.js's saveAll for why), so every
  // block touched since the last save gets saved, not just whichever one
  // happens to still be showing in the panel. Returns a Promise<{ok, error}>.
  // This panel has no Save button of its own -- the only way this ever runs
  // is via registerSaveHandler below, called by the global save bar/
  // unsaved-changes modal (article_unsaved_changes.js).
  const save = () => {
    const entries = Array.from(pendingEdits.entries());
    if (entries.length === 0) {
      return Promise.resolve({ ok: true });
    }

    statusEl.textContent = "Saving...";
    statusEl.classList.remove("is-error");

    return entries
      .reduce(
        (chain, [blockId, request]) =>
          chain.then((results) =>
            saveViaFetch(request.url, request.payload).then((result) => {
              if (result.ok) {
                pendingEdits.delete(blockId);
              }
              return results.concat([result]);
            })
          ),
        Promise.resolve([])
      )
      .then((results) => {
        if (pendingEdits.size === 0) {
          window.ifiUnsavedChanges.markClean("blockStyle");
        }
        const ok = results.every((r) => r.ok);
        if (!ok) {
          const error = results
            .filter((r) => !r.ok)
            .map((r) => r.error)
            .join(" ");
          statusEl.textContent = error;
          statusEl.classList.add("is-error");
          return { ok: false, error };
        }
        statusEl.textContent = "Saved";
        return { ok: true };
      });
  };

  window.ifiUnsavedChanges.registerSaveHandler(save);

  // sets each relevant field to its default and replays the same
  // input/click event each one already listens for, rather than
  // duplicating what those listeners do (live preview, dataset, class
  // swap, recordPendingEdit, all of it) a second time here.
  const resetButton = document.getElementById("block-style-reset");
  const applySlider = (input, value) => {
    if (value === undefined || !input) {
      return;
    }
    input.value = value;
    input.dispatchEvent(new Event("input"));
  };
  const applyButtonGroup = (group, value) => {
    if (value === undefined || !group) {
      return;
    }
    const button = group.querySelector(`button[data-align="${value}"]`);
    if (button) {
      button.click();
    }
  };
  resetButton.addEventListener("click", () => {
    const blockType = targetTypeInput.value;
    const defaults = BLOCK_STYLE_DEFAULTS[blockType];
    if (!blockType || !defaults) {
      return;
    }
    if (!window.confirm("Reset this block's style to its default values? Unsaved changes to it will be lost.")) {
      return;
    }

    applySlider(paddingInput, defaults.side_padding);
    applyButtonGroup(alignmentGroup, defaults.alignment);
    applySlider(fontSizeInput, defaults.font_size);
    applySlider(widthInput, defaults.width_rem);
    applySlider(gapInput, defaults.gap);

    if (blockType === "multi_column" && defaults.column_weight !== undefined) {
      const blockEl =
        currentBlockEl || document.querySelector(`[data-block-id="${CSS.escape(targetIdInput.value)}"]`);
      const columnCount = parseInt(blockEl ? blockEl.dataset.columnCount : "0", 10) || 0;
      for (let i = 0; i < columnCount; i++) {
        applySlider(columnWeightInputs[i], defaults.column_weight);
      }
    }

    applyButtonGroup(titleAlignmentGroup, defaults.title_alignment);
    applySlider(titleFontSizeInput, defaults.title_font_size);
    applyButtonGroup(introAlignmentGroup, defaults.intro_alignment);
    applySlider(introFontSizeInput, defaults.intro_font_size);
    applyButtonGroup(metaAlignmentGroup, defaults.meta_alignment);
    applySlider(metaFontSizeInput, defaults.meta_font_size);
  });
});
