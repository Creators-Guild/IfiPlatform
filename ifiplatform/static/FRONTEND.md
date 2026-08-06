# Static Folder structure
- One global static folder
- One per-app static folder

Try to avoid long files with lots of scrolling. Instead seperate into new and more spesific files
## CSS
### Structure of files: ITCSS (Inverted Triangle CSS)

! actual numbering in the project might differ from below !
    
    styles/
        01-settings/     # Variables, tokens (colors, spacing, fonts)
        02-tools/        # Mixins, functions (if using Sass)
        03-generic/      # Reset, normalize, box-sizing
        04-elements/     # Bare HTML tags (h1, a, p)
        05-objects/      # Layout patterns (container, grid)
        06-components/   # UI components (card, nav, button)
        07-utilities/    # Overrides, helpers (.hidden, .text-center)
    
- load order follows numbering
- load necessary with one or a few CSS files ex.

        @import "01_generic/reset.css";
        @import "02_settings/tokens.css";
        @import "03_elements/elements.css";
        @import "04_objects/base_layout.css";
        @import "05_components/card.css";

- then in the relevant html head
    - {% load static %}
    - `<link rel="stylesheet" href="{% static 'path to file relative to static folder as root' %}">`
### Structure within files: BEM (Block Element Modifier)
Example:

    /* Block */
    .card { }

    /* Element */
    .card__title { }
    .card__image { }
    
    /* Modifier */
    .card--featured { }
    .card__title--large { }

