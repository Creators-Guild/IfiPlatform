"""Norwegian Bokmaal -> English term pairs DeepL must translate exactly this
way (or not translate at all -- source == target means "leave as-is"), e.g.
proper nouns (tool names, student union names) DeepL otherwise tends to
guess-translate. Pushed to a DeepL glossary by
`manage.py sync_deepl_glossary` -- see that command's docstring for the full
setup. Edit this list and re-run the command whenever a new word needs
locking down; no code changes needed beyond that.

Keys/values are matched by DeepL as exact substrings, so keep them as the
specific proper noun (e.g. "Fadderuke") rather than a whole sentence."""

GLOSSARY_TERMS = {
    # IFI-tools named in README.md -- proper nouns, never translate.
    "Peoply": "Peoply",
    "Trix": "Trix",
    "IFI Rom": "IFI Rom",
    # Recurring event name (see ifi_home_app/management/commands/
    # seed_dev_data.py) -- a Norwegian term kept as-is in the English UI
    # rather than translated (e.g. NOT "Godparent week").
    "Fadderuke": "Orientation Week",
    "Fadder":"Buddy",
    "Fadderbarn":"Buddychild", # please find a better translation ahah
    "Fadderstyret":"The Buddy Council(Fadderstyret)",
    "dagen@ifi": "dagen@ifi",
}
