document.addEventListener("DOMContentLoaded", () => {
  const panel = document.getElementById("block-style-mini-panel");
  if (!panel) {
    return;
  }

  // the global font-size multiplier (see article_quick_style.js), read
  // live off .article-page's own data attribute so per-block font-size
  // edits in this panel stay visually consistent with whatever multiplier
  // is currently active (including an unsaved one still being dragged in
  // the Global editor panel) -- never written here, only read.
  const articlePageEl = document.querySelector(".article-page");
  const currentFontSizeMultiplier = () => {
    const value = parseFloat(articlePageEl && articlePageEl.dataset.fontSizeMultiplier);
    return Number.isNaN(value) ? 1 : value;
  };

  // {block_type: {field: default_value}} -- see BLOCK_STYLE_DEFAULTS in
  // article_models.py, rendered via json_script in
  // article_block_style_mini_panel.html. Powers the "Reset to default" button.
  const defaultsScript = document.getElementById("block-style-defaults-data");
  const BLOCK_STYLE_DEFAULTS = defaultsScript ? JSON.parse(defaultsScript.textContent) : {};

  // {block_type: display name} -- shown as the panel's own title (see
  // openPanelFor below) so it's clear at a glance which kind of block is
  // currently open, since this one shared panel's fields otherwise look
  // the same regardless of what's being edited.
  const BLOCK_TYPE_LABELS = {
    heading: "Heading",
    paragraph: "Paragraph",
    image: "Image",
    image_caption: "Image title/caption",
    multi_column: "Multi-column",
    column: "Column",
    article_header: "Header",
    title: "Title",
    meta: "Meta",
    intro: "Intro",
    hero_image: "Hero image",
    toc_icon: "TOC icon",
    article_card: "Article card",
    category_card: "Category card",
    union_card: "Student union card",
    tool_card: "Tool card",
  };

  // which fields apply to each block type, and (for alignment) which class
  // prefix + possible values that block's template actually uses to express
  // it -- paragraph and multi_column both have "alignment"-shaped
  // concepts in the model, but multi_column's is column_alignment (top/
  // center/bottom vertical layout, a different axis entirely), not left/
  // center/right text alignment, so it's deliberately left out here.
  const FIELDS_BY_TYPE = {
    heading: ["side_padding", "alignment", "exclude_from_global_alignment", "font_size", "text_color"],
    paragraph: ["side_padding", "alignment", "exclude_from_global_alignment", "font_size", "text_color"],
    image: ["alignment", "exclude_from_global_alignment", "width_rem", "side_padding"],
    // article/category/union/tool cards -- width/height (a fixed-design
    // card, not built from editable text/box parts like everything else
    // here; height 0 = auto), plus, for article_card only, list_style
    // (compact list row instead of a full card -- see .articlecard--list
    // in articlecard.css) and fixed_ratio (whether its image keeps its
    // normal 8:5 ratio or lets "Height" size it directly instead -- see
    // .articlecard--unlocked-ratio).
    article_card: ["width_rem", "height_rem", "list_style", "fixed_ratio"],
    category_card: ["width_rem", "height_rem"],
    union_card: ["width_rem", "height_rem"],
    tool_card: ["width_rem", "height_rem"],
    // an image's own title (alt_text)/caption, boxed together as one unit
    // (its own <figcaption>, see article_image_block.html) -- box plus its
    // own side padding, same shape as "column" below.
    image_caption: ["side_padding"],
    // per-column weight fields aren't listed here -- there's a variable
    // number of them (1-4, multi_column's own min/max_num), added to this
    // at runtime in openPanelFor() based on the block actually being
    // edited (data-column-count).
    multi_column: ["side_padding", "gap"],
    // a multi_column sub-column -- not a block type of its own in the
    // StreamField, just a ListBlock item id (see article_models.py's
    // _effective_block_styles()), with its own side padding plus box. Its
    // title (if it has one) shares this same trigger/panel rather than its
    // own -- alignment/font_size/text_color are added at runtime in
    // openPanelFor() when the column actually has one (data-title-block-
    // id), same pattern as multi_column's own column_weight_N fields
    // above. Saved as a second, independent request in recordPendingEdit()
    // (block_id "<column id>-title", block_type "column_title") alongside
    // the column's own side padding/box.
    column: ["side_padding"],
    // title/meta/intro (the article-header group) -- side padding plus
    // box. Alignment/font-size/text-color for these three all live in the
    // shared header editor instead (see article_header below and
    // HEADER_TEXT_COLOR_GROUPS) -- their own individual trigger here is
    // side padding and Box, nothing else.
    title: ["side_padding"],
    meta: ["side_padding"],
    intro: ["side_padding"],
    // not a StreamField block -- the title/intro/meta group above the body,
    // wrapped together so they share one trigger (see article_page.html's
    // .article-header). Alignment/font-size saved via save_header_style,
    // plain ArticlePage fields; text color for each saved as its own
    // separate ArticleBlockStyle row instead (block_id "article-title"/
    // "article-meta"/"article-intro", same rows title/meta/intro's own
    // individual trigger used to write text_color to -- see
    // HEADER_TEXT_COLOR_GROUPS/recordPendingEdit below), since that's a
    // per-block-style concern, not a plain ArticlePage field.
    article_header: [
      "side_padding",
      "title_alignment",
      "title_font_size",
      "title_text_color",
      "meta_alignment",
      "meta_font_size",
      "meta_text_color",
      "intro_alignment",
      "intro_font_size",
      "intro_text_color",
    ],
    // alignment/width/side_padding reuse the exact same generic inputs as
    // "image" -- also not a StreamField block though (hero_image is a set
    // of ArticleStyle fields, see article_models.py), so it needs the same
    // special-cased save endpoint as article_header. boxed/box_color/
    // box_custom_color/box_border_radius have their own small dedicated
    // controls below (not the generic Box section -- that one saves to a
    // per-block ArticleBlockStyle row, these save to ArticleStyle instead,
    // same endpoint as the other three).
    hero_image: ["alignment", "width_rem", "side_padding", "boxed", "box_color", "box_custom_color", "box_border_radius"],
    // not a StreamField block either -- there's only ever one
    // table-of-contents icon on the page (ArticlePage.toc_icon_size), same
    // special-cased save endpoint as article_header/hero_image.
    toc_icon: ["toc_icon_size"],
  };
  // wrapper <div> class prefix for each card block type (article_body_blocks.html/
  // article_column_content.html) -- these blocks' width/height live-preview (below)
  // sets CSS custom properties on the wrapper (--card-width/--card-height) rather
  // than a literal inline width/height, so a mobile breakpoint's own CSS can
  // override them at normal specificity instead of having to fight an inline style.
  const CARD_WRAPPER_CLASS = {
    article_card: "body-article-card",
    category_card: "body-category-card",
    union_card: "body-union-card",
    tool_card: "body-tool-card",
  };
  const CLASS_SWAP = {
    heading: { alignment: { prefix: "heading--align-", values: ["left", "center", "right"] } },
    paragraph: { alignment: { prefix: "prose--align-", values: ["left", "center", "right"] } },
    image: { alignment: { prefix: "body-image--", values: ["left", "center", "right"] } },
    hero_image: { alignment: { prefix: "hero-image--", values: ["left", "center", "right"] } },
  };


  // box styling (border/background/radius/padding/margin) is available on
  // every one of these -- appended to FIELDS_BY_TYPE at runtime (see
  // openPanelFor/buildSaveRequest below) rather than listed per type above,
  // since it's the same fixed set everywhere it applies. Deliberately not
  // offered on article_header/hero_image -- those are plain ArticlePage
  // fields, not part of the per-block override table box styling lives in.
  const BOX_CAPABLE_TYPES = new Set([
    "heading",
    "paragraph",
    "image",
    "image_caption",
    "multi_column",
    "column",
    "title",
    "meta",
    "intro",
    // the title/meta/intro group as a whole, same as multi_column's own
    // grid wrapper is boxable on top of each of its columns -- its own
    // side padding is deliberately excluded from this (see paddingInput's
    // own "input" listener and applyBoxStyle below, both special-case
    // this type to keep using --header-side-padding instead of margin-
    // left/right, since that CSS custom property's accent-underline
    // reasoning still applies regardless of whether the box itself is on).
    "article_header",
  ]);
  // box_bg_custom_color/box_border_custom_color aren't listed separately --
  // they're not their own panel field, just the value of the "Custom" hex
  // swatch inside box_bg_color/box_border_color (see the mini panel
  // template).
  const BOX_FIELD_NAMES = [
    "box_enabled",
    "box_bg_color",
    "box_border_visible",
    "box_border_width",
    "box_border_color",
    "box_radius",
    "box_padding",
    "box_margin",
  ];
  // every box field except box_enabled itself -- hidden until the box is
  // turned on (see updateBoxFieldVisibility()).
  const BOX_ONLY_FIELDS = BOX_FIELD_NAMES.slice(1);

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
  const fontSizeLabel = document.getElementById("block-style-font-size-label");
  const textColorLabel = document.getElementById("block-style-text-color-label");
  const widthInput = document.getElementById("block-style-width");
  const widthValue = document.getElementById("block-style-width-value");
  const heightInput = document.getElementById("block-style-height");
  const heightValue = document.getElementById("block-style-height-value");
  const listStyleInput = document.getElementById("block-style-list-style");
  const fixedRatioInput = document.getElementById("block-style-fixed-ratio");
  // hero_image only -- see FIELDS_BY_TYPE.hero_image's own comment for why
  // these are separate from the generic Box section's box*Input refs below.
  const heroBoxedInput = document.getElementById("block-style-hero-boxed");
  const heroBoxColorGroup = document.getElementById("block-style-hero-box-color");
  const heroBoxCustomColorInput = document.getElementById("block-style-hero-box-custom-color");
  const heroBoxPickerInput = document.getElementById("block-style-hero-box-picker");
  const heroBoxRadiusInput = document.getElementById("block-style-hero-box-radius");
  const heroBoxRadiusValue = document.getElementById("block-style-hero-box-radius-value");
  const alignmentGroup = document.getElementById("block-style-alignment");
  // opts this block (or, for the merged column panel, the column's own
  // title -- see FIELDS_BY_TYPE.column) out of the Global editor's
  // Alignment "overwrite all blocks" action -- see ArticleBlockStyle.
  // exclude_from_global_alignment, save_quick_style's apply_alignment_to_
  // blocks, and article_quick_style.js's save(). CAPTION_TEXT_GROUPS below
  // each have their own separate one (excludeInput), since image_title/
  // image_caption_body are independently alignment-capable blocks of
  // their own, not the shared "Style" section this one belongs to.
  const excludeGlobalAlignmentInput = document.getElementById("block-style-exclude-global-alignment");
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
  const tocIconSizeInput = document.getElementById("block-style-toc-icon-size");
  const tocIconSizeValue = document.getElementById("block-style-toc-icon-size-value");
  const MAX_COLUMNS = 4;
  const columnWeightInputs = Array.from({ length: MAX_COLUMNS }, (_, i) =>
    document.getElementById(`block-style-column-weight-${i}`)
  );
  const columnWeightValues = Array.from({ length: MAX_COLUMNS }, (_, i) =>
    document.getElementById(`block-style-column-weight-${i}-value`)
  );
  const statusEl = document.getElementById("block-style-mini-panel-status");
  const panelTitle = document.getElementById("block-style-mini-panel-title");

  const boxEnabledInput = document.getElementById("block-style-box-enabled");
  const boxBgColorGroup = document.getElementById("block-style-box-bg-color");
  const boxBgCustomColorInput = document.getElementById("block-style-box-bg-custom-color");
  const boxBgPickerInput = document.getElementById("block-style-box-bg-picker");
  const styleLabel = document.getElementById("block-style-style-label");
  // NOT box-scoped -- applies independent of that block's own box (see
  // applyTextColor below), so these live outside the Box section entirely
  // in the template, in their own "Style" section alongside font-size/
  // alignment.
  const textColorGroup = document.getElementById("block-style-text-color");
  const textCustomColorInput = document.getElementById("block-style-text-custom-color");
  const textPickerInput = document.getElementById("block-style-text-picker");
  const boxBorderVisibleInput = document.getElementById("block-style-box-border-visible");
  const boxBorderWidthInput = document.getElementById("block-style-box-border-width");
  const boxBorderWidthValue = document.getElementById("block-style-box-border-width-value");
  const boxBorderColorGroup = document.getElementById("block-style-box-border-color");
  const boxBorderCustomColorInput = document.getElementById("block-style-box-border-custom-color");
  const boxBorderPickerInput = document.getElementById("block-style-box-border-picker");
  const boxRadiusInput = document.getElementById("block-style-box-radius");
  const boxRadiusValue = document.getElementById("block-style-box-radius-value");
  const boxPaddingInput = document.getElementById("block-style-box-padding");
  const boxPaddingValue = document.getElementById("block-style-box-padding-value");
  const boxMarginInput = document.getElementById("block-style-box-margin");
  const boxMarginValue = document.getElementById("block-style-box-margin-value");

  // an image_caption's own title (alt_text)/caption text -- see
  // article_image_block.html's data-title-*/data-caption-* attributes and
  // BLOCK_STYLE_DEFAULTS["image_title"]/["image_caption_body"] in
  // article_models.py. Two near-identical groups (same shape as the
  // generic alignment/font-size/side-padding/text-color fields used
  // everywhere else), each with its own dedicated panel fields since both
  // need to be visible/editable at once in this one shared panel -- driven
  // generically off this config rather than duplicating the wiring below
  // twice by hand.
  const CAPTION_TEXT_GROUPS = [
    {
      datasetPrefix: "title",
      styleFieldPrefix: "caption_title",
      blockType: "image_title",
      defaultsKey: "image_title",
      spanSelector: ":scope > .image-title",
      alignmentGroup: document.getElementById("block-style-caption-title-alignment"),
      excludeInput: document.getElementById("block-style-caption-title-exclude-global-alignment"),
      fontSizeInput: document.getElementById("block-style-caption-title-font-size"),
      fontSizeValue: document.getElementById("block-style-caption-title-font-size-value"),
      paddingInput: document.getElementById("block-style-caption-title-padding"),
      paddingValue: document.getElementById("block-style-caption-title-padding-value"),
      colorGroup: document.getElementById("block-style-caption-title-text-color"),
      customColorInput: document.getElementById("block-style-caption-title-custom-color"),
      pickerInput: document.getElementById("block-style-caption-title-picker"),
    },
    {
      datasetPrefix: "caption",
      styleFieldPrefix: "caption_body",
      blockType: "image_caption_body",
      defaultsKey: "image_caption_body",
      spanSelector: ":scope > .image-caption",
      alignmentGroup: document.getElementById("block-style-caption-body-alignment"),
      excludeInput: document.getElementById("block-style-caption-body-exclude-global-alignment"),
      fontSizeInput: document.getElementById("block-style-caption-body-font-size"),
      fontSizeValue: document.getElementById("block-style-caption-body-font-size-value"),
      paddingInput: document.getElementById("block-style-caption-body-padding"),
      paddingValue: document.getElementById("block-style-caption-body-padding-value"),
      colorGroup: document.getElementById("block-style-caption-body-text-color"),
      customColorInput: document.getElementById("block-style-caption-body-custom-color"),
      pickerInput: document.getElementById("block-style-caption-body-picker"),
    },
  ];

  // title/meta/intro's own text color -- edited from the shared
  // article_header panel now (see FIELDS_BY_TYPE.title/meta/intro above,
  // now empty besides box), but still saved as each one's own separate
  // ArticleBlockStyle row (block_id "article-title"/"article-meta"/
  // "article-intro", block_type "title"/"meta"/"intro" -- the exact same
  // rows their own individual trigger used to write to), alongside
  // article_header's own save_header_style request -- see
  // recordPendingEdit below. targetSelector picks the live-preview target
  // out of currentBlockEl (.article-header while this group is being
  // edited), same idea as CAPTION_TEXT_GROUPS' spanSelector.
  const HEADER_TEXT_COLOR_GROUPS = [
    {
      datasetPrefix: "title",
      blockId: "article-title",
      blockType: "title",
      targetSelector: ":scope > h1",
      colorGroup: document.getElementById("block-style-title-text-color"),
      customColorInput: document.getElementById("block-style-title-text-custom-color"),
      pickerInput: document.getElementById("block-style-title-text-picker"),
    },
    {
      datasetPrefix: "meta",
      blockId: "article-meta",
      blockType: "meta",
      targetSelector: ":scope > .article-meta",
      colorGroup: document.getElementById("block-style-meta-text-color"),
      customColorInput: document.getElementById("block-style-meta-text-custom-color"),
      pickerInput: document.getElementById("block-style-meta-text-picker"),
    },
    {
      datasetPrefix: "intro",
      blockId: "article-intro",
      blockType: "intro",
      targetSelector: ":scope > .intro",
      colorGroup: document.getElementById("block-style-intro-text-color"),
      customColorInput: document.getElementById("block-style-intro-text-custom-color"),
      pickerInput: document.getElementById("block-style-intro-text-picker"),
    },
  ];

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

    // hero_image isn't a StreamField block either -- ArticleStyle fields
    // (hero_image_position/width_rem/side_padding/boxed/box_color/
    // box_custom_color/box_border_radius), same reasoning as article_header
    // above.
    if (blockType === "hero_image") {
      return {
        url: panel.dataset.heroImageSaveUrl,
        payload: {
          alignment: alignmentGroup.dataset.value,
          width_rem: widthInput.value,
          side_padding: paddingInput.value,
          boxed: heroBoxedInput.checked,
          box_color: heroBoxColorGroup.dataset.value,
          box_custom_color: heroBoxCustomColorInput.value,
          box_border_radius: heroBoxRadiusInput.value,
        },
      };
    }

    // not a StreamField block either -- there's only ever one
    // table-of-contents icon on the page (ArticlePage.toc_icon_size).
    if (blockType === "toc_icon") {
      return {
        url: panel.dataset.tocIconSaveUrl,
        payload: {
          toc_icon_size: tocIconSizeInput.value,
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
    const boxCapable = BOX_CAPABLE_TYPES.has(blockType);
    return {
      url: panel.dataset.saveUrl,
      payload: {
        block_id: targetIdInput.value,
        block_type: blockType,
        side_padding: visibleFields.includes("side_padding") ? paddingInput.value : null,
        alignment: visibleFields.includes("alignment") ? alignmentGroup.dataset.value : null,
        exclude_from_global_alignment: visibleFields.includes("exclude_from_global_alignment")
          ? excludeGlobalAlignmentInput.checked
          : null,
        font_size: visibleFields.includes("font_size") ? fontSizeInput.value : null,
        width_rem: visibleFields.includes("width_rem") ? widthInput.value : null,
        height_rem: visibleFields.includes("height_rem") ? heightInput.value : null,
        list_style: visibleFields.includes("list_style") ? listStyleInput.checked : null,
        fixed_ratio: visibleFields.includes("fixed_ratio") ? fixedRatioInput.checked : null,
        gap: visibleFields.includes("gap") ? gapInput.value : null,
        column_weights: columnWeights,
        text_color: visibleFields.includes("text_color") ? textColorGroup.dataset.value : null,
        text_custom_color: visibleFields.includes("text_color") ? textCustomColorInput.value : null,
        box_enabled: boxCapable ? boxEnabledInput.checked : null,
        box_bg_color: boxCapable ? boxBgColorGroup.dataset.value : null,
        box_bg_custom_color: boxCapable ? boxBgCustomColorInput.value : null,
        box_border_visible: boxCapable ? boxBorderVisibleInput.checked : null,
        box_border_width: boxCapable ? boxBorderWidthInput.value : null,
        box_border_color: boxCapable ? boxBorderColorGroup.dataset.value : null,
        box_border_custom_color: boxCapable ? boxBorderCustomColorInput.value : null,
        box_radius: boxCapable ? boxRadiusInput.value : null,
        box_padding: boxCapable ? boxPaddingInput.value : null,
        box_margin: boxCapable ? boxMarginInput.value : null,
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

    // a column's title is saved as its own separate ArticleBlockStyle row
    // (block_id "<column id>-title", block_type "column_title") even
    // though it now shares the column's own trigger/panel (see
    // FIELDS_BY_TYPE.column) -- record a second, independent pending edit
    // for it alongside the column's own, keyed by its own block_id so it
    // survives switching to a different block same as any other pending
    // edit (see pendingEdits above).
    if (targetTypeInput.value === "column" && currentBlockEl && currentBlockEl.dataset.titleBlockId) {
      const titleId = currentBlockEl.dataset.titleBlockId;
      pendingEdits.set(titleId, {
        url: panel.dataset.saveUrl,
        payload: {
          block_id: titleId,
          block_type: "column_title",
          alignment: alignmentGroup.dataset.value,
          exclude_from_global_alignment: excludeGlobalAlignmentInput.checked,
          font_size: fontSizeInput.value,
          text_color: textColorGroup.dataset.value,
          text_custom_color: textCustomColorInput.value,
        },
      });
    }

    // an image_caption's own title/caption text are each saved as their
    // own separate ArticleBlockStyle row too (block_id "<image id>-cap-
    // title"/"-cap-body", see CAPTION_TEXT_GROUPS above), alongside the
    // figcaption's own box -- same reasoning as column's title above.
    if (targetTypeInput.value === "image_caption" && currentBlockEl) {
      CAPTION_TEXT_GROUPS.forEach((group) => {
        const textId = currentBlockEl.dataset[`${group.datasetPrefix}TextId`];
        if (!textId) {
          return;
        }
        pendingEdits.set(textId, {
          url: panel.dataset.saveUrl,
          payload: {
            block_id: textId,
            block_type: group.blockType,
            alignment: group.alignmentGroup.dataset.value,
            exclude_from_global_alignment: group.excludeInput.checked,
            font_size: group.fontSizeInput.value,
            side_padding: group.paddingInput.value,
            text_color: group.colorGroup.dataset.value,
            text_custom_color: group.customColorInput.value,
          },
        });
      });
    }

    // title/meta/intro's own text color, edited from this same shared
    // article_header panel now (see HEADER_TEXT_COLOR_GROUPS above), is
    // still saved as each one's own separate ArticleBlockStyle row --
    // block_id "article-title"/"article-meta"/"article-intro", the exact
    // same rows their own individual trigger used to write text_color to
    // -- alongside article_header's own save_header_style request above.
    if (targetTypeInput.value === "article_header") {
      HEADER_TEXT_COLOR_GROUPS.forEach((group) => {
        pendingEdits.set(group.blockId, {
          url: panel.dataset.saveUrl,
          payload: {
            block_id: group.blockId,
            block_type: group.blockType,
            text_color: group.colorGroup.dataset.value,
            text_custom_color: group.customColorInput.value,
          },
        });
      });

      // the header group's own box (background/border/radius/padding/
      // margin, wrapping title+meta+intro together -- see BOX_CAPABLE_
      // TYPES above) is a fourth, independent ArticleBlockStyle row, same
      // block_id "article-header" the save_header_style request above
      // uses -- a distinct pendingEdits *key* ("article-header-box", not
      // "article-header") so it doesn't overwrite that primary request in
      // the map, since they go to two different endpoints entirely.
      pendingEdits.set("article-header-box", {
        url: panel.dataset.saveUrl,
        payload: {
          block_id: "article-header",
          block_type: "article_header",
          box_enabled: boxEnabledInput.checked,
          box_bg_color: boxBgColorGroup.dataset.value,
          box_bg_custom_color: boxBgCustomColorInput.value,
          box_border_visible: boxBorderVisibleInput.checked,
          box_border_width: boxBorderWidthInput.value,
          box_border_color: boxBorderColorGroup.dataset.value,
          box_border_custom_color: boxBorderCustomColorInput.value,
          box_radius: boxRadiusInput.value,
          box_padding: boxPaddingInput.value,
          box_margin: boxMarginInput.value,
        },
      });
    }

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

  // alignment/font-size/text-color normally read/write directly on
  // currentBlockEl's own dataset -- but a multi_column column's title has
  // no separate trigger/panel of its own any more (see FIELDS_BY_TYPE.column
  // below): these same three fields describe the *title* instead while a
  // "column" is what's open. Both the dataset key they're stored under (so
  // reopening this same column later in the same page load picks the right
  // value back up, see openPanelFor) and the live-preview target (the
  // title, not the column) need to shift accordingly.
  const TITLE_DATASET_KEYS = {
    alignment: "titleAlignment",
    excludeFromGlobalAlignment: "titleExcludeFromGlobalAlignment",
    fontSize: "titleFontSize",
    textColor: "titleTextColor",
    textCustomColor: "titleTextCustomColor",
  };
  const styleDatasetKey = (key) =>
    targetTypeInput.value === "column" && TITLE_DATASET_KEYS[key] ? TITLE_DATASET_KEYS[key] : key;

  // alignment positions the title via its wrapping <div> -- column-title is
  // display:inline-block (so its border-bottom underline hugs just the
  // text, see article_multicolumn.css), which leaves its own text-align
  // nothing to align within its own tightly-fit box (see
  // article_body_blocks.html's own comment on .column-title-wrap). Font-
  // size/color apply directly to the title text itself instead.
  const columnTitleWrapEl = () =>
    currentBlockEl ? currentBlockEl.querySelector(":scope > .column-title-wrap") : null;
  const columnTitleEl = () =>
    currentBlockEl ? currentBlockEl.querySelector(":scope > .column-title-wrap > .column-title") : null;

  const wireButtonGroup = (group, field, dataAttr) => {
    group.querySelectorAll("button").forEach((button) => {
      button.addEventListener("click", () => {
        if (!currentBlockEl) {
          return;
        }
        const value = button.dataset[dataAttr];
        group.dataset.value = value;
        currentBlockEl.dataset[styleDatasetKey(field)] = value;
        if (field === "alignment" && targetTypeInput.value === "column") {
          const wrap = columnTitleWrapEl();
          if (wrap) {
            wrap.style.textAlign = value;
          }
        } else {
          swapClass(currentBlockEl, targetTypeInput.value, field, value);
        }
        group.querySelectorAll("button").forEach((b) => {
          b.classList.toggle("active", b === button);
        });
        positionTextTriggers();
        recordPendingEdit();
      });
    });
  };

  // live-preview mirror of _block_box_style.html's own logic: while the box
  // is off, padding-left/right come from the block's own side_padding (see
  // paddingInput's own listener below) -- no visible border to offset, so
  // indenting the block just means indenting its content. While it's on,
  // side_padding switches to margin-left/right instead, so it's the box's
  // *border* (not just empty space inside it) that ends up indented --
  // box.padding becomes the space between that border and the content on
  // all four sides, box.margin the vertical space outside it, side_padding
  // the horizontal counterpart to box.margin, not to box.padding. Skipped
  // entirely for article_header -- its own side padding always goes
  // through --header-side-padding instead (paddingInput's own listener
  // special-cases this same type), regardless of whether its box is on.
  const applyBoxStyle = () => {
    if (!currentBlockEl) {
      return;
    }
    const enabled = boxEnabledInput.checked;
    const managesSidePadding = targetTypeInput.value !== "article_header";
    currentBlockEl.classList.toggle("block-box", enabled);
    if (!enabled) {
      currentBlockEl.style.padding = "";
      currentBlockEl.style.marginTop = "";
      currentBlockEl.style.marginBottom = "";
      if (managesSidePadding) {
        currentBlockEl.style.marginLeft = "";
        currentBlockEl.style.marginRight = "";
      }
      currentBlockEl.style.backgroundColor = "";
      currentBlockEl.style.borderRadius = "";
      currentBlockEl.style.boxShadow = "";
      currentBlockEl.style.border = "";
      currentBlockEl.style.display = "";
      if (managesSidePadding) {
        currentBlockEl.style.paddingLeft = `${paddingInput.value}rem`;
        currentBlockEl.style.paddingRight = `${paddingInput.value}rem`;
      }
      return;
    }
    currentBlockEl.style.padding = `${boxPaddingInput.value}rem`;
    currentBlockEl.style.marginTop = `${boxMarginInput.value}rem`;
    currentBlockEl.style.marginBottom = `${boxMarginInput.value}rem`;
    if (managesSidePadding) {
      currentBlockEl.style.marginLeft = `${paddingInput.value}rem`;
      currentBlockEl.style.marginRight = `${paddingInput.value}rem`;
    }
    // multi_column's own grid wrapper needs to stay "display: flex" (set in
    // article_multicolumn.css) for its columns to lay out side by side --
    // "flow-root" would silently replace that outright (same property,
    // same element) and collapse them into a single stacked column. Every
    // other box-capable element is a plain block box to begin with, where
    // flow-root is purely additive float containment, so only this one
    // type needs to skip it (see _block_box_style.html's keep_display,
    // same reasoning for the server-rendered version of this).
    if (targetTypeInput.value !== "multi_column") {
      currentBlockEl.style.display = "flow-root";
    }
    currentBlockEl.style.borderRadius = `${boxRadiusInput.value}rem`;
    currentBlockEl.style.boxShadow = "0 2px 8px var(--color-shadow)";
    const bgColor = boxBgColorGroup.dataset.value;
    currentBlockEl.style.backgroundColor =
      bgColor === "custom"
        ? boxBgCustomColorInput.value || "var(--color-bg-light)"
        : `var(--color-${bgColor})`;
    if (boxBorderVisibleInput.checked) {
      const borderColor = boxBorderColorGroup.dataset.value;
      const resolvedBorderColor =
        borderColor === "custom"
          ? boxBorderCustomColorInput.value || "var(--color-black)"
          : `var(--color-${borderColor})`;
      currentBlockEl.style.border = `${boxBorderWidthInput.value}rem solid ${resolvedBorderColor}`;
    } else {
      currentBlockEl.style.border = "";
    }
  };

  // independent of applyBoxStyle above -- text color applies regardless of
  // whether that block's own box is on (see _effective_heading_style() in
  // article_models.py). Blank ("" -- no swatch selected) leaves the text
  // color alone, same as BLOCK_STYLE_DEFAULTS["heading"]["text_color"]'s
  // own meaning server-side.
  const applyTextColor = () => {
    if (!currentBlockEl) {
      return;
    }
    const target = targetTypeInput.value === "column" ? columnTitleEl() : currentBlockEl;
    if (!target) {
      return;
    }
    const textColor = textColorGroup.dataset.value;
    if (textColor) {
      target.style.color =
        textColor === "custom" ? textCustomColorInput.value || "inherit" : `var(--color-${textColor})`;
    } else {
      target.style.color = "";
    }
  };

  // hero_image only -- draws a border/box around the image, title and
  // caption. Mirrors article_page.html's own server-rendered version of
  // this exact logic (--box-bg custom property + border-radius, gated by
  // .image-figure--boxed -- see article_image.css); box-color--<color> is
  // separate from --box-bg itself, only used for text contrast when the
  // box is black (see .box-color--black .image-title in that same file),
  // so it needs stripping/re-adding as its own step, not just a plain
  // classList.toggle the way image-figure--boxed itself is.
  const applyHeroImageBox = () => {
    if (!currentBlockEl) {
      return;
    }
    Array.from(currentBlockEl.classList)
      .filter((cls) => cls.startsWith("box-color--"))
      .forEach((cls) => currentBlockEl.classList.remove(cls));
    const boxed = heroBoxedInput.checked;
    currentBlockEl.classList.toggle("image-figure--boxed", boxed);
    if (!boxed) {
      currentBlockEl.style.removeProperty("--box-bg");
      currentBlockEl.style.borderRadius = "";
      return;
    }
    const boxColor = heroBoxColorGroup.dataset.value;
    currentBlockEl.classList.add(`box-color--${boxColor}`);
    currentBlockEl.style.setProperty(
      "--box-bg",
      boxColor === "custom"
        ? heroBoxCustomColorInput.value || "var(--color-bg-light)"
        : `var(--color-${boxColor})`
    );
    currentBlockEl.style.borderRadius = `${heroBoxRadiusInput.value}rem`;
  };

  // a collapsible section's own header (see the panel template's "block-
  // style-caption-header" divs -- Layout, Style, Column weights, Title/
  // Intro/Meta) only makes sense to show while at least one real field
  // inside its own fields wrapper (the very next sibling) is currently
  // visible -- computed by reading the DOM directly (not a static "which
  // fields does this type have" list) so it stays correct even when a
  // field's visibility changes *after* the panel opened for reasons
  // besides block type, like side_padding hiding once Box gets switched on
  // (see updateBoxFieldVisibility below) -- without this, a section whose
  // only field was side_padding would keep showing its own header with an
  // empty section underneath once Box is checked. Box's own header (data-
  // style-field="box_enabled") isn't a bare label like these, so it's
  // excluded by this selector and keeps its own boxCapable-driven
  // visibility untouched.
  const updateSectionHeaders = () => {
    panel.querySelectorAll('[data-style-field$="_label"]').forEach((header) => {
      const wrapper = header.nextElementSibling;
      if (!wrapper || !wrapper.classList.contains("block-style-box-fields")) {
        return;
      }
      const hasVisibleField = Array.from(wrapper.querySelectorAll("[data-style-field]")).some(
        (field) => !field.hidden
      );
      header.hidden = !hasVisibleField;
    });
  };

  // toggles which box-related fields are showing: everything but the
  // "Box" checkbox itself stays hidden until it's on, and the border
  // width/color only show while the border itself is visible. side_padding
  // stays visible regardless -- its own live effect is still superseded by
  // box_padding while the box is on (see applyBoxStyle/paddingInput's own
  // "input" listener), but the field itself stays put rather than
  // vanishing (and, with it, Layout as a whole for types where it's the
  // only field in that section -- see updateSectionHeaders below).
  const updateBoxFieldVisibility = () => {
    if (!BOX_CAPABLE_TYPES.has(targetTypeInput.value)) {
      return;
    }
    const enabled = boxEnabledInput.checked;
    BOX_ONLY_FIELDS.forEach((name) => {
      const field = panel.querySelector(`[data-style-field="${name}"]`);
      if (field) {
        field.hidden = !enabled;
      }
    });
    const borderWidthField = panel.querySelector('[data-style-field="box_border_width"]');
    if (borderWidthField) {
      borderWidthField.hidden = !enabled || !boxBorderVisibleInput.checked;
    }
    const borderColorField = panel.querySelector('[data-style-field="box_border_color"]');
    if (borderColorField) {
      borderColorField.hidden = !enabled || !boxBorderVisibleInput.checked;
    }
    updateSectionHeaders();
  };

  // #rgb -> #rrggbb, lowercased; null if `value` isn't valid hex at all.
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

  // black or white, whichever reads better on top of `hex` -- so the hex
  // text inside the custom swatch itself (see article_block_style.css)
  // stays legible regardless of how light or dark the picked color is.
  // Standard relative-luminance threshold, not exact WCAG contrast math --
  // good enough for picking between exactly two options.
  const contrastTextColor = (hex) => {
    const int = parseInt(hex.slice(1), 16);
    const r = (int >> 16) & 255;
    const g = (int >> 8) & 255;
    const b = int & 255;
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.6 ? "#000000" : "#ffffff";
  };

  // sets the custom hex swatch's own value + live color preview together
  // (and its paired color-wheel picker button's own value, so opening it
  // starts from whatever's currently picked rather than always white) --
  // shared by openPanelFor (restoring a saved value), the reset button, and
  // the input's own live-typing handler below.
  const setCustomSwatch = (input, hex, pickerInput) => {
    input.value = hex || "";
    if (hex) {
      input.style.backgroundColor = hex;
      input.style.color = contrastTextColor(hex);
    } else {
      input.style.backgroundColor = "";
      input.style.color = "";
    }
    if (pickerInput) {
      pickerInput.value = hex || "#ffffff";
    }
  };

  // every box control below writes back to currentBlockEl.dataset (not
  // just the panel's own controls + live CSS via applyBoxStyle) -- same
  // reasoning as every other field's own handler (e.g. wireButtonGroup's
  // currentBlockEl.dataset[field] = value): without it, the *element*
  // never actually remembers the edit, only its current on-screen look
  // does, so reopening this same block's panel later in the same page
  // load (openPanelFor reads blockEl.dataset.box*) would show it as
  // unchanged even though the live preview clearly isn't.
  // shared by both the five fixed-color buttons and the "Custom" hex
  // swatch -- whichever one just changed becomes the group's active
  // choice, every other swatch in the group loses its own active state.
  // applyFn defaults to applyBoxStyle (every other color group is box-
  // scoped) -- text color passes applyTextColor instead, and skips
  // updateBoxFieldVisibility entirely, since it isn't a box field.
  const selectSwatch = (group, swatch, datasetKey, applyFn = applyBoxStyle) => {
    if (!currentBlockEl) {
      return;
    }
    group.dataset.value = swatch.dataset.color;
    currentBlockEl.dataset[styleDatasetKey(datasetKey)] = swatch.dataset.color;
    group.querySelectorAll(".color-swatch").forEach((s) => {
      s.classList.toggle("active", s === swatch);
    });
    if (applyFn === applyBoxStyle) {
      updateBoxFieldVisibility();
    }
    applyFn();
    recordPendingEdit();
  };

  const wireColorGroup = (group, datasetKey, applyFn = applyBoxStyle) => {
    group.querySelectorAll("button.color-swatch").forEach((button) => {
      button.addEventListener("click", () => selectSwatch(group, button, datasetKey, applyFn));
    });
  };
  wireColorGroup(boxBgColorGroup, "boxBgColor");
  wireColorGroup(boxBorderColorGroup, "boxBorderColor");
  wireColorGroup(textColorGroup, "textColor", applyTextColor);
  wireColorGroup(heroBoxColorGroup, "boxColor", applyHeroImageBox);

  // the "Custom" swatch is a plain hex text input (see the mini panel
  // template) -- typing a valid hex both selects "custom" for the group
  // (same as clicking any other swatch) and colors the input's own
  // background/text to preview it right there, recording the actual
  // picked hex (box_bg_custom_color/box_border_custom_color) alongside the
  // group's color *choice* ("custom"). The color-wheel picker button next
  // to it (a real, visually-hidden <input type="color">, see the mini
  // panel template) feeds the exact same hex swatch -- picking a color
  // there fires "input" just like typing does, just from a different
  // source.
  [
    [boxBgCustomColorInput, boxBgPickerInput, boxBgColorGroup, "boxBgColor", "boxBgCustomColor"],
    [boxBorderCustomColorInput, boxBorderPickerInput, boxBorderColorGroup, "boxBorderColor", "boxBorderCustomColor"],
    [textCustomColorInput, textPickerInput, textColorGroup, "textColor", "textCustomColor", applyTextColor],
    [heroBoxCustomColorInput, heroBoxPickerInput, heroBoxColorGroup, "boxColor", "boxCustomColor", applyHeroImageBox],
  ].forEach(([hexInput, pickerInput, group, groupDatasetKey, customDatasetKey, applyFn = applyBoxStyle]) => {
    // custom isn't active yet -- a plain click always immediately focuses a
    // text input (or, for the picker label, forwards straight into opening
    // the native color dialog), with no "just select it" step in between
    // the way clicking any of the five fixed swatches has. So: while custom
    // isn't the group's active choice, the whole outer box (the hex chip,
    // the picker button, and the gap/border between them -- see
    // .color-swatch-custom-group in article_block_style.css) acts as one
    // big "select custom" button on its *first* click, same as clicking a
    // fixed swatch reapplies its own color, and blocks whichever default
    // action that click would otherwise have triggered. Once custom *is*
    // active, clicks go back to behaving normally -- type in the hex field,
    // or open the picker. Two listeners, not one, because a text input
    // grabs focus on mousedown (before "click" even fires), while a
    // <label>'s default forwarding to its color input happens on "click" --
    // an input's focus can only be blocked by catching the earlier event.
    const customGroupEl = hexInput.closest(".color-swatch-custom-group");
    customGroupEl.addEventListener("mousedown", (event) => {
      if (!currentBlockEl || group.dataset.value === "custom") {
        return;
      }
      event.preventDefault();
    });
    customGroupEl.addEventListener("click", (event) => {
      if (!currentBlockEl || group.dataset.value === "custom") {
        return;
      }
      event.preventDefault();
      selectSwatch(group, hexInput, groupDatasetKey, applyFn);
    });

    hexInput.addEventListener("input", () => {
      const hex = normalizeHex(hexInput.value);
      if (!currentBlockEl || !hex) {
        // still typing a partial/invalid value -- wait for it to resolve
        // to something valid rather than fighting the user's cursor with a
        // premature style change.
        return;
      }
      setCustomSwatch(hexInput, hex, pickerInput);
      currentBlockEl.dataset[styleDatasetKey(customDatasetKey)] = hex;
      selectSwatch(group, hexInput, groupDatasetKey, applyFn);
    });

    pickerInput.addEventListener("input", () => {
      if (!currentBlockEl) {
        return;
      }
      setCustomSwatch(hexInput, pickerInput.value, pickerInput);
      currentBlockEl.dataset[styleDatasetKey(customDatasetKey)] = pickerInput.value;
      selectSwatch(group, hexInput, groupDatasetKey, applyFn);
    });
  });

  // the element a caption-text group's fields actually preview/apply to --
  // the title/caption span itself, inside the currently-open image_caption
  // block's figcaption (see CAPTION_TEXT_GROUPS above).
  const captionTextTargetEl = (group) =>
    currentBlockEl ? currentBlockEl.querySelector(group.spanSelector) : null;

  const wireCaptionTextGroup = (group) => {
    group.alignmentGroup.querySelectorAll("button").forEach((button) => {
      button.addEventListener("click", () => {
        if (!currentBlockEl) {
          return;
        }
        const value = button.dataset.align;
        group.alignmentGroup.dataset.value = value;
        currentBlockEl.dataset[`${group.datasetPrefix}Alignment`] = value;
        const target = captionTextTargetEl(group);
        if (target) {
          target.style.textAlign = value;
        }
        group.alignmentGroup.querySelectorAll("button").forEach((b) => {
          b.classList.toggle("active", b === button);
        });
        recordPendingEdit();
      });
    });

    group.excludeInput.addEventListener("change", () => {
      if (!currentBlockEl) {
        return;
      }
      currentBlockEl.dataset[`${group.datasetPrefix}ExcludeFromGlobalAlignment`] = group.excludeInput.checked
        ? "true"
        : "false";
      recordPendingEdit();
    });

    group.fontSizeInput.addEventListener("input", () => {
      if (!currentBlockEl) {
        return;
      }
      const target = captionTextTargetEl(group);
      if (target) {
        target.style.fontSize = `${group.fontSizeInput.value * currentFontSizeMultiplier()}rem`;
      }
      currentBlockEl.dataset[`${group.datasetPrefix}FontSize`] = group.fontSizeInput.value;
      group.fontSizeValue.textContent = group.fontSizeInput.value;
      recordPendingEdit();
    });

    group.paddingInput.addEventListener("input", () => {
      if (!currentBlockEl) {
        return;
      }
      const target = captionTextTargetEl(group);
      if (target) {
        target.style.paddingLeft = `${group.paddingInput.value}rem`;
        target.style.paddingRight = `${group.paddingInput.value}rem`;
      }
      currentBlockEl.dataset[`${group.datasetPrefix}SidePadding`] = group.paddingInput.value;
      group.paddingValue.textContent = group.paddingInput.value;
      recordPendingEdit();
    });

    const applyColor = () => {
      const target = captionTextTargetEl(group);
      if (!target) {
        return;
      }
      const color = group.colorGroup.dataset.value;
      if (color) {
        target.style.color =
          color === "custom" ? group.customColorInput.value || "inherit" : `var(--color-${color})`;
      } else {
        target.style.color = "";
      }
    };
    group.applyColor = applyColor;

    const colorDatasetKey = `${group.datasetPrefix}TextColor`;
    const customDatasetKey = `${group.datasetPrefix}TextCustomColor`;
    wireColorGroup(group.colorGroup, colorDatasetKey, applyColor);

    // same "click anywhere in the custom swatch's shared outer box selects
    // it" handling as the generic box/text custom swatches above, just
    // scoped to this one group's own hex input/picker.
    const customGroupEl = group.customColorInput.closest(".color-swatch-custom-group");
    customGroupEl.addEventListener("mousedown", (event) => {
      if (!currentBlockEl || group.colorGroup.dataset.value === "custom") {
        return;
      }
      event.preventDefault();
    });
    customGroupEl.addEventListener("click", (event) => {
      if (!currentBlockEl || group.colorGroup.dataset.value === "custom") {
        return;
      }
      event.preventDefault();
      selectSwatch(group.colorGroup, group.customColorInput, colorDatasetKey, applyColor);
    });
    group.customColorInput.addEventListener("input", () => {
      const hex = normalizeHex(group.customColorInput.value);
      if (!currentBlockEl || !hex) {
        return;
      }
      setCustomSwatch(group.customColorInput, hex, group.pickerInput);
      currentBlockEl.dataset[customDatasetKey] = hex;
      selectSwatch(group.colorGroup, group.customColorInput, colorDatasetKey, applyColor);
    });
    group.pickerInput.addEventListener("input", () => {
      if (!currentBlockEl) {
        return;
      }
      setCustomSwatch(group.customColorInput, group.pickerInput.value, group.pickerInput);
      currentBlockEl.dataset[customDatasetKey] = group.pickerInput.value;
      selectSwatch(group.colorGroup, group.customColorInput, colorDatasetKey, applyColor);
    });
  };
  CAPTION_TEXT_GROUPS.forEach(wireCaptionTextGroup);

  // title/meta/intro's own text color, edited from the shared
  // article_header panel now (see HEADER_TEXT_COLOR_GROUPS above) --
  // color-only, so a lighter version of wireCaptionTextGroup above (no
  // alignment/font-size/padding, those still live on their own dedicated
  // title_alignment/title_font_size/etc fields elsewhere in this panel).
  const wireHeaderTextColorGroup = (group) => {
    const applyColor = () => {
      if (!currentBlockEl) {
        return;
      }
      const target = currentBlockEl.querySelector(group.targetSelector);
      if (!target) {
        return;
      }
      const color = group.colorGroup.dataset.value;
      if (color) {
        target.style.color =
          color === "custom" ? group.customColorInput.value || "inherit" : `var(--color-${color})`;
      } else {
        target.style.color = "";
      }
    };
    group.applyColor = applyColor;

    const colorDatasetKey = `${group.datasetPrefix}TextColor`;
    const customDatasetKey = `${group.datasetPrefix}TextCustomColor`;
    wireColorGroup(group.colorGroup, colorDatasetKey, applyColor);

    const customGroupEl = group.customColorInput.closest(".color-swatch-custom-group");
    customGroupEl.addEventListener("mousedown", (event) => {
      if (!currentBlockEl || group.colorGroup.dataset.value === "custom") {
        return;
      }
      event.preventDefault();
    });
    customGroupEl.addEventListener("click", (event) => {
      if (!currentBlockEl || group.colorGroup.dataset.value === "custom") {
        return;
      }
      event.preventDefault();
      selectSwatch(group.colorGroup, group.customColorInput, colorDatasetKey, applyColor);
    });
    group.customColorInput.addEventListener("input", () => {
      const hex = normalizeHex(group.customColorInput.value);
      if (!currentBlockEl || !hex) {
        return;
      }
      setCustomSwatch(group.customColorInput, hex, group.pickerInput);
      currentBlockEl.dataset[customDatasetKey] = hex;
      selectSwatch(group.colorGroup, group.customColorInput, colorDatasetKey, applyColor);
    });
    group.pickerInput.addEventListener("input", () => {
      if (!currentBlockEl) {
        return;
      }
      setCustomSwatch(group.customColorInput, group.pickerInput.value, group.pickerInput);
      currentBlockEl.dataset[customDatasetKey] = group.pickerInput.value;
      selectSwatch(group.colorGroup, group.customColorInput, colorDatasetKey, applyColor);
    });
  };
  HEADER_TEXT_COLOR_GROUPS.forEach(wireHeaderTextColorGroup);

  boxEnabledInput.addEventListener("change", () => {
    if (!currentBlockEl) {
      return;
    }
    currentBlockEl.dataset.boxEnabled = boxEnabledInput.checked ? "true" : "false";
    updateBoxFieldVisibility();
    applyBoxStyle();
    positionTextTriggers();
    recordPendingEdit();
  });

  // every collapsible section header in the panel (Layout, Style, Column
  // weights, Title/Intro/Meta, Image title/Image caption, Box) is wired the
  // same generic way -- purely whether that section's own fields are
  // showing right now, not (for Box) whether it's enabled. Not reset when
  // switching to a different block's panel, so collapsing one once keeps
  // it collapsed for whatever you open next too. data-controls points each
  // toggle at its own fields wrapper's id (see the panel template) --
  // there's no per-section JS beyond this one loop, so adding another
  // section there needs no matching code here.
  panel.querySelectorAll("[data-controls]").forEach((toggle) => {
    const wrapper = document.getElementById(toggle.dataset.controls);
    if (!wrapper) {
      return;
    }
    toggle.addEventListener("click", (event) => {
      event.preventDefault();
      const expanded = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", expanded ? "false" : "true");
      wrapper.hidden = expanded;
    });
  });

  boxBorderVisibleInput.addEventListener("change", () => {
    if (!currentBlockEl) {
      return;
    }
    currentBlockEl.dataset.boxBorderVisible = boxBorderVisibleInput.checked ? "true" : "false";
    updateBoxFieldVisibility();
    applyBoxStyle();
    recordPendingEdit();
  });

  [
    [boxBorderWidthInput, boxBorderWidthValue, "boxBorderWidth"],
    [boxRadiusInput, boxRadiusValue, "boxRadius"],
    [boxPaddingInput, boxPaddingValue, "boxPadding"],
    [boxMarginInput, boxMarginValue, "boxMargin"],
  ].forEach(([input, valueEl, datasetKey]) => {
    input.addEventListener("input", () => {
      if (!currentBlockEl) {
        return;
      }
      currentBlockEl.dataset[datasetKey] = input.value;
      valueEl.textContent = input.value;
      applyBoxStyle();
      recordPendingEdit();
    });
  });

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
    if (blockType === "column" && blockEl.dataset.titleBlockId) {
      visibleFields = visibleFields.concat(["alignment", "exclude_from_global_alignment", "font_size", "text_color"]);
    }
    if (blockType === "image_caption") {
      CAPTION_TEXT_GROUPS.forEach((group) => {
        if (blockEl.dataset[`${group.datasetPrefix}TextId`]) {
          visibleFields = visibleFields.concat([
            `${group.styleFieldPrefix}_label`,
            `${group.styleFieldPrefix}_alignment`,
            `${group.styleFieldPrefix}_exclude_from_global_alignment`,
            `${group.styleFieldPrefix}_font_size`,
            `${group.styleFieldPrefix}_side_padding`,
            `${group.styleFieldPrefix}_text_color`,
          ]);
        }
      });
    }
    const boxCapable = BOX_CAPABLE_TYPES.has(blockType);
    if (boxCapable) {
      visibleFields = visibleFields.concat(BOX_FIELD_NAMES);
    }

    panel.querySelectorAll("[data-style-field]").forEach((field) => {
      field.hidden = !visibleFields.includes(field.dataset.styleField);
    });
    updateSectionHeaders();

    targetIdInput.value = blockEl.dataset.blockId;
    targetTypeInput.value = blockType;
    statusEl.textContent = "";
    statusEl.classList.remove("is-error");
    styleLabel.textContent =
      blockType === "column" ? styleLabel.dataset.labelTitle : styleLabel.dataset.labelDefault;
    panelTitle.textContent = BLOCK_TYPE_LABELS[blockType] || panelTitle.dataset.labelDefault;

    if (visibleFields.includes("side_padding")) {
      paddingInput.value = blockEl.dataset.sidePadding;
      paddingValue.textContent = blockEl.dataset.sidePadding;
    }
    if (boxCapable) {
      boxEnabledInput.checked = blockEl.dataset.boxEnabled === "true";
      boxBgColorGroup.dataset.value = blockEl.dataset.boxBgColor;
      boxBgColorGroup.querySelectorAll(".color-swatch").forEach((b) => {
        b.classList.toggle("active", b.dataset.color === blockEl.dataset.boxBgColor);
      });
      setCustomSwatch(boxBgCustomColorInput, blockEl.dataset.boxBgCustomColor, boxBgPickerInput);
      boxBorderVisibleInput.checked = blockEl.dataset.boxBorderVisible === "true";
      boxBorderWidthInput.value = blockEl.dataset.boxBorderWidth;
      boxBorderWidthValue.textContent = blockEl.dataset.boxBorderWidth;
      boxBorderColorGroup.dataset.value = blockEl.dataset.boxBorderColor;
      boxBorderColorGroup.querySelectorAll(".color-swatch").forEach((b) => {
        b.classList.toggle("active", b.dataset.color === blockEl.dataset.boxBorderColor);
      });
      setCustomSwatch(boxBorderCustomColorInput, blockEl.dataset.boxBorderCustomColor, boxBorderPickerInput);
      boxRadiusInput.value = blockEl.dataset.boxRadius;
      boxRadiusValue.textContent = blockEl.dataset.boxRadius;
      boxPaddingInput.value = blockEl.dataset.boxPadding;
      boxPaddingValue.textContent = blockEl.dataset.boxPadding;
      boxMarginInput.value = blockEl.dataset.boxMargin;
      boxMarginValue.textContent = blockEl.dataset.boxMargin;
      updateBoxFieldVisibility();
    }
    if (visibleFields.includes("exclude_from_global_alignment")) {
      excludeGlobalAlignmentInput.checked =
        blockEl.dataset[styleDatasetKey("excludeFromGlobalAlignment")] === "true";
    }
    if (visibleFields.includes("font_size")) {
      const fontVal = blockEl.dataset[styleDatasetKey("fontSize")];
      fontSizeInput.value = fontVal;
      fontSizeValue.textContent = fontVal;
      fontSizeLabel.textContent =
        blockType === "column" ? fontSizeLabel.dataset.labelTitle : fontSizeLabel.dataset.labelDefault;
    }
    if (visibleFields.includes("text_color")) {
      const colorVal = blockEl.dataset[styleDatasetKey("textColor")] || "";
      textColorGroup.dataset.value = colorVal;
      textColorGroup.querySelectorAll(".color-swatch").forEach((b) => {
        b.classList.toggle("active", b.dataset.color === colorVal);
      });
      setCustomSwatch(textCustomColorInput, blockEl.dataset[styleDatasetKey("textCustomColor")], textPickerInput);
      textColorLabel.textContent =
        blockType === "column" ? textColorLabel.dataset.labelTitle : textColorLabel.dataset.labelDefault;
    }
    if (blockType === "image_caption") {
      CAPTION_TEXT_GROUPS.forEach((group) => {
        if (!blockEl.dataset[`${group.datasetPrefix}TextId`]) {
          return;
        }
        const alignVal = blockEl.dataset[`${group.datasetPrefix}Alignment`];
        group.alignmentGroup.dataset.value = alignVal;
        group.alignmentGroup.querySelectorAll("button").forEach((b) => {
          b.classList.toggle("active", b.dataset.align === alignVal);
        });
        group.excludeInput.checked = blockEl.dataset[`${group.datasetPrefix}ExcludeFromGlobalAlignment`] === "true";
        const fontVal = blockEl.dataset[`${group.datasetPrefix}FontSize`];
        group.fontSizeInput.value = fontVal;
        group.fontSizeValue.textContent = fontVal;
        const paddingVal = blockEl.dataset[`${group.datasetPrefix}SidePadding`];
        group.paddingInput.value = paddingVal;
        group.paddingValue.textContent = paddingVal;
        const colorVal = blockEl.dataset[`${group.datasetPrefix}TextColor`] || "";
        group.colorGroup.dataset.value = colorVal;
        group.colorGroup.querySelectorAll(".color-swatch").forEach((b) => {
          b.classList.toggle("active", b.dataset.color === colorVal);
        });
        setCustomSwatch(
          group.customColorInput,
          blockEl.dataset[`${group.datasetPrefix}TextCustomColor`],
          group.pickerInput
        );
      });
    }
    if (visibleFields.includes("width_rem")) {
      widthInput.value = blockEl.dataset.widthRem;
      widthValue.textContent = blockEl.dataset.widthRem;
    }
    if (visibleFields.includes("height_rem")) {
      heightInput.value = blockEl.dataset.heightRem;
      heightValue.textContent = blockEl.dataset.heightRem;
    }
    if (visibleFields.includes("list_style")) {
      listStyleInput.checked = blockEl.dataset.listStyle === "true";
    }
    if (visibleFields.includes("fixed_ratio")) {
      fixedRatioInput.checked = blockEl.dataset.fixedRatio === "true";
    }
    if (visibleFields.includes("boxed")) {
      heroBoxedInput.checked = blockEl.dataset.boxed === "true";
    }
    if (visibleFields.includes("box_color")) {
      heroBoxColorGroup.dataset.value = blockEl.dataset.boxColor;
      heroBoxColorGroup.querySelectorAll(".color-swatch").forEach((b) => {
        b.classList.toggle("active", b.dataset.color === blockEl.dataset.boxColor);
      });
      setCustomSwatch(heroBoxCustomColorInput, blockEl.dataset.boxCustomColor, heroBoxPickerInput);
    }
    if (visibleFields.includes("box_border_radius")) {
      heroBoxRadiusInput.value = blockEl.dataset.boxBorderRadius;
      heroBoxRadiusValue.textContent = blockEl.dataset.boxBorderRadius;
    }
    if (visibleFields.includes("gap")) {
      gapInput.value = blockEl.dataset.gap;
      gapValue.textContent = blockEl.dataset.gap;
    }
    if (visibleFields.includes("toc_icon_size")) {
      tocIconSizeInput.value = blockEl.dataset.tocIconSize;
      tocIconSizeValue.textContent = blockEl.dataset.tocIconSize;
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
      const alignVal = blockEl.dataset[styleDatasetKey("alignment")];
      alignmentGroup.dataset.value = alignVal;
      alignmentGroup.querySelectorAll("button").forEach((b) => {
        b.classList.toggle("active", b.dataset.align === alignVal);
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
    if (blockType === "article_header") {
      HEADER_TEXT_COLOR_GROUPS.forEach((group) => {
        const colorVal = blockEl.dataset[`${group.datasetPrefix}TextColor`] || "";
        group.colorGroup.dataset.value = colorVal;
        group.colorGroup.querySelectorAll(".color-swatch").forEach((b) => {
          b.classList.toggle("active", b.dataset.color === colorVal);
        });
        setCustomSwatch(
          group.customColorInput,
          blockEl.dataset[`${group.datasetPrefix}TextCustomColor`],
          group.pickerInput
        );
      });
    }

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
    } else if (BOX_CAPABLE_TYPES.has(targetTypeInput.value) && boxEnabledInput.checked) {
      // while the box is on, side_padding indents the box itself (margin)
      // instead of the space inside it (padding, which box.padding governs
      // instead) -- see applyBoxStyle/_block_box_style.html.
      currentBlockEl.style.marginLeft = `${paddingInput.value}rem`;
      currentBlockEl.style.marginRight = `${paddingInput.value}rem`;
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
    const target = targetTypeInput.value === "column" ? columnTitleEl() : currentBlockEl;
    if (target) {
      target.style.fontSize = `${fontSizeInput.value * currentFontSizeMultiplier()}rem`;
    }
    currentBlockEl.dataset[styleDatasetKey("fontSize")] = fontSizeInput.value;
    fontSizeValue.textContent = fontSizeInput.value;
    positionTextTriggers();
    recordPendingEdit();
  });

  widthInput.addEventListener("input", () => {
    if (!currentBlockEl) {
      return;
    }
    // Card blocks (CARD_WRAPPER_CLASS above) drive their width from a
    // --card-width custom property instead of a literal inline width --
    // everything else (just "image" today) keeps the plain inline style.
    if (CARD_WRAPPER_CLASS[currentBlockEl.dataset.blockType]) {
      currentBlockEl.style.setProperty("--card-width", `${widthInput.value}rem`);
    } else {
      currentBlockEl.style.width = `${widthInput.value}rem`;
    }
    currentBlockEl.dataset.widthRem = widthInput.value;
    widthValue.textContent = widthInput.value;
    positionTextTriggers();
    recordPendingEdit();
  });

  // card blocks only -- 0 means auto (drop the fixed-height custom property
  // and its modifier class entirely, back to the card's own natural
  // content-driven height).
  heightInput.addEventListener("input", () => {
    if (!currentBlockEl) {
      return;
    }
    const height = parseFloat(heightInput.value);
    const wrapperClass = CARD_WRAPPER_CLASS[currentBlockEl.dataset.blockType];
    if (wrapperClass) {
      if (height > 0) {
        currentBlockEl.style.setProperty("--card-height", `${heightInput.value}rem`);
        currentBlockEl.classList.add(`${wrapperClass}--fixed-height`);
      } else {
        currentBlockEl.style.removeProperty("--card-height");
        currentBlockEl.classList.remove(`${wrapperClass}--fixed-height`);
      }
    } else if (height > 0) {
      currentBlockEl.style.height = `${heightInput.value}rem`;
      currentBlockEl.style.overflow = "hidden";
    } else {
      currentBlockEl.style.height = "";
      currentBlockEl.style.overflow = "";
    }
    currentBlockEl.dataset.heightRem = heightInput.value;
    heightValue.textContent = heightInput.value;
    positionTextTriggers();
    recordPendingEdit();
  });

  // article_card only -- toggles .articlecard--list on the <a> itself
  // (currentBlockEl is its wrapping div, see article_body_blocks.html).
  listStyleInput.addEventListener("change", () => {
    if (!currentBlockEl) {
      return;
    }
    const cardEl = currentBlockEl.querySelector(".articlecard");
    if (cardEl) {
      cardEl.classList.toggle("articlecard--list", listStyleInput.checked);
    }
    currentBlockEl.dataset.listStyle = listStyleInput.checked ? "true" : "false";
    recordPendingEdit();
  });

  // article_card only -- toggles .articlecard--unlocked-ratio (dropping
  // the image's fixed 8:5 ratio in favor of "Height" above) -- unchecked
  // means unlocked, since the checkbox itself reads "Lock image ratio".
  fixedRatioInput.addEventListener("change", () => {
    if (!currentBlockEl) {
      return;
    }
    const cardEl = currentBlockEl.querySelector(".articlecard");
    if (cardEl) {
      cardEl.classList.toggle("articlecard--unlocked-ratio", !fixedRatioInput.checked);
    }
    currentBlockEl.dataset.fixedRatio = fixedRatioInput.checked ? "true" : "false";
    recordPendingEdit();
  });

  // heading/paragraph/image, and (via styleDatasetKey) a column's own
  // title -- see ArticleBlockStyle.exclude_from_global_alignment. Purely a
  // meta-flag, no live-preview visual to update, just the dataset marker
  // openPanelFor reads back on reopen and recordPendingEdit sends on save.
  excludeGlobalAlignmentInput.addEventListener("change", () => {
    if (!currentBlockEl) {
      return;
    }
    currentBlockEl.dataset[styleDatasetKey("excludeFromGlobalAlignment")] = excludeGlobalAlignmentInput.checked
      ? "true"
      : "false";
    recordPendingEdit();
  });

  // hero_image only -- see applyHeroImageBox's own comment.
  heroBoxedInput.addEventListener("change", () => {
    if (!currentBlockEl) {
      return;
    }
    currentBlockEl.dataset.boxed = heroBoxedInput.checked ? "true" : "false";
    applyHeroImageBox();
    recordPendingEdit();
  });

  heroBoxRadiusInput.addEventListener("input", () => {
    if (!currentBlockEl) {
      return;
    }
    currentBlockEl.dataset.boxBorderRadius = heroBoxRadiusInput.value;
    heroBoxRadiusValue.textContent = heroBoxRadiusInput.value;
    applyHeroImageBox();
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

  // the ToC icon and its own button circle scale together (article_toc.css's
  // .toc-open-icon/.toc-open-button/.article-page--has-toc all key off this
  // one variable) -- set on .article-page, not currentBlockEl itself, since
  // that's the wrapper around just the button+trigger, not the icon.
  tocIconSizeInput.addEventListener("input", () => {
    if (!currentBlockEl) {
      return;
    }
    const articlePage = document.querySelector(".article-page");
    if (articlePage) {
      articlePage.style.setProperty("--toc-icon-size", `${tocIconSizeInput.value}rem`);
    }
    currentBlockEl.dataset.tocIconSize = tocIconSizeInput.value;
    tocIconSizeValue.textContent = tocIconSizeInput.value;
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
  const applyColorGroup = (group, value) => {
    if (value === undefined || !group) {
      return;
    }
    const button = group.querySelector(`button[data-color="${value}"]`);
    if (button) {
      button.click();
    }
  };
  // for a color group whose default is blank (text color, unlike bg/border,
  // has no fixed color of its own to click through -- see
  // BLOCK_STYLE_DEFAULTS["box"]["text_color"]) -- clears it back to "no
  // swatch selected" directly instead.
  const clearColorGroup = (group) => {
    group.dataset.value = "";
    group.querySelectorAll(".color-swatch").forEach((s) => s.classList.remove("active"));
  };
  const applyToggle = (input, value) => {
    if (value === undefined || !input) {
      return;
    }
    input.checked = value;
    input.dispatchEvent(new Event("change"));
  };
  resetButton.addEventListener("click", () => {
    const blockType = targetTypeInput.value;
    const defaults = BLOCK_STYLE_DEFAULTS[blockType];
    // column/image_caption/title/meta/intro have no BLOCK_STYLE_DEFAULTS
    // entry of their own -- side padding (see FIELDS_BY_TYPE above) always
    // defaults to plain 0 for these, handled in the fallback below rather
    // than needing a whole defaults dict just for one field.
    const boxCapable = BOX_CAPABLE_TYPES.has(blockType);
    if (!blockType || (!defaults && !boxCapable)) {
      return;
    }
    if (!window.confirm("Reset this block's style to its default values? Unsaved changes to it will be lost.")) {
      return;
    }

    if (defaults) {
      applySlider(paddingInput, defaults.side_padding);
      applyButtonGroup(alignmentGroup, defaults.alignment);
      applySlider(fontSizeInput, defaults.font_size);
      applySlider(widthInput, defaults.width_rem);
      applySlider(heightInput, defaults.height_rem);
      if (defaults.list_style !== undefined) {
        applyToggle(listStyleInput, defaults.list_style);
      }
      if (defaults.fixed_ratio !== undefined) {
        applyToggle(fixedRatioInput, defaults.fixed_ratio);
      }
      applySlider(gapInput, defaults.gap);
      applySlider(tocIconSizeInput, defaults.toc_icon_size);

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
    }

    // title/meta/intro's own text color, edited from this same shared
    // article_header panel now (see HEADER_TEXT_COLOR_GROUPS above) --
    // every type that offers text color defaults to blank (inherit the
    // page's normal text color), same as the generic text_color field's
    // own reset elsewhere.
    if (blockType === "article_header") {
      HEADER_TEXT_COLOR_GROUPS.forEach((group) => {
        clearColorGroup(group.colorGroup);
        setCustomSwatch(group.customColorInput, "", group.pickerInput);
        group.applyColor();
      });
    }

    // column/image_caption/title/meta/intro's own side padding -- no
    // BLOCK_STYLE_DEFAULTS entry of their own (see above), always resets
    // to plain 0.
    if (!defaults && (FIELDS_BY_TYPE[blockType] || []).includes("side_padding")) {
      applySlider(paddingInput, 0);
    }

    // a column's title shares this same trigger/panel/reset button now
    // (see FIELDS_BY_TYPE.column above) -- reset it back to heading's own
    // defaults (column_title has no separate BLOCK_STYLE_DEFAULTS entry,
    // it always shared heading's -- see article_models.py) alongside the
    // column's own box, below.
    if (blockType === "column" && currentBlockEl && currentBlockEl.dataset.titleBlockId) {
      const titleDefaults = BLOCK_STYLE_DEFAULTS.heading || {};
      applyButtonGroup(alignmentGroup, titleDefaults.alignment);
      applySlider(fontSizeInput, titleDefaults.font_size);
      clearColorGroup(textColorGroup);
      setCustomSwatch(textCustomColorInput, "", textPickerInput);
      applyTextColor();
    }

    // an image_caption's own title/caption text share this same trigger/
    // panel/reset button too (see CAPTION_TEXT_GROUPS above) -- reset each
    // one back to its own BLOCK_STYLE_DEFAULTS entry, independent of the
    // figcaption's own box below.
    if (blockType === "image_caption" && currentBlockEl) {
      CAPTION_TEXT_GROUPS.forEach((group) => {
        if (!currentBlockEl.dataset[`${group.datasetPrefix}TextId`]) {
          return;
        }
        const groupDefaults = BLOCK_STYLE_DEFAULTS[group.defaultsKey] || {};
        applyButtonGroup(group.alignmentGroup, groupDefaults.alignment);
        applySlider(group.fontSizeInput, groupDefaults.font_size);
        applySlider(group.paddingInput, groupDefaults.side_padding);
        clearColorGroup(group.colorGroup);
        setCustomSwatch(group.customColorInput, "", group.pickerInput);
        group.applyColor();
      });
    }

    // text color is independent of box (see FIELDS_BY_TYPE) -- every type
    // that offers it defaults to blank (inherit the page's normal text
    // color), so there's no per-type default value to look up.
    if ((FIELDS_BY_TYPE[blockType] || []).includes("text_color")) {
      clearColorGroup(textColorGroup);
      setCustomSwatch(textCustomColorInput, "", textPickerInput);
      applyTextColor();
    }

    if (boxCapable) {
      const boxDefaults = BLOCK_STYLE_DEFAULTS.box;
      if (boxDefaults) {
        applyColorGroup(boxBgColorGroup, boxDefaults.bg_color);
        setCustomSwatch(boxBgCustomColorInput, boxDefaults.bg_custom_color, boxBgPickerInput);
        applyColorGroup(boxBorderColorGroup, boxDefaults.border_color);
        setCustomSwatch(boxBorderCustomColorInput, boxDefaults.border_custom_color, boxBorderPickerInput);
        applySlider(boxBorderWidthInput, boxDefaults.border_width);
        applySlider(boxRadiusInput, boxDefaults.radius);
        applySlider(boxPaddingInput, boxDefaults.padding);
        applySlider(boxMarginInput, boxDefaults.margin);
        applyToggle(boxBorderVisibleInput, boxDefaults.border_visible);
        // applied last: its own change handler re-derives box field
        // visibility from every other box field's current value, so it
        // needs to run after they've all already been reset above.
        applyToggle(boxEnabledInput, boxDefaults.enabled);
      }
    }

    // hero_image's own box -- separate from the generic box mechanism
    // above (hero_image isn't in BOX_CAPABLE_TYPES, see applyHeroImageBox's
    // own comment), so it needs its own reset here.
    if (blockType === "hero_image" && defaults) {
      applyToggle(heroBoxedInput, defaults.boxed);
      applyColorGroup(heroBoxColorGroup, defaults.box_color);
      setCustomSwatch(heroBoxCustomColorInput, defaults.box_custom_color, heroBoxPickerInput);
      applySlider(heroBoxRadiusInput, defaults.box_border_radius);
    }
  });
});
