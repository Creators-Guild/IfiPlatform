"""Models for the wiki feature, including articles, categories, tags and authors."""
from django.db import models
from django.contrib.auth.models import User


# category object with support for tree structure
# Example of getting every subcategory:
#     cat = Category.objects.get(name='Programming')
#     cat.subcategories.all()
# Example of getting parent of a category:
#     sub = Category.objects.get(name='Django')
#     sub.parent  # Category object
class WikiCategory(models.Model):
    """Wiki category with optional parent for tree structure support."""
    name = models.CharField(max_length=100)

    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="subcategories",
        null=True,
        blank=True,
    )

    def __str__(self):
        """Return category name as string."""
        return self.name


class WikiTag(models.Model):
    """Simple tag that can be applied to wiki articles."""
    name = models.CharField(max_length=20)

    def __str__(self):
        """Return tag name as string."""
        return self.name


class WikiAuthor(models.Model):
    """Wrapper around User so author info is preserved if the user is deleted."""
    user = models.OneToOneField(
        User, on_delete=models.SET_NULL, related_name="author", null=True
    )
    name = models.CharField(max_length=200)

    def save(self, *args, **kwargs):
        """Sync author name with username on every save if user still exists."""
        if self.user is not None:
            self.name = self.user.username
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        """Return author name as string."""
        return self.name

 # TODO: Implement edit history (currently commented out)
# # Edit history
# class WikiArticle_Edit(models.Model):
#     editer = models.ForeignKey(
#         WikiAuthor,
#         on_delete=models.SET_NULL
#     )
#     date = models.DateTimeField()


# simple model for a wikiArticle
class WikiArticle(models.Model):
    """A wiki article with a title, intro text, body and optional image."""
    title = models.CharField(max_length=200)
    intro_text = models.TextField()
    body = models.TextField()
    image_name = models.CharField(max_length=100, blank=True)

    def __str__(self):
        """Return article title as string."""
        return f"{self.title}"


# simple model for a metadata for a wikiarticle
class WikiArticle_Meta(models.Model):
    """Metadata for a wiki article including views, timestamps, authors and tags."""
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_edited = models.DateTimeField(
        auto_now=True
    )  # updates everytime the object is updated
    views = models.PositiveIntegerField(default=0)
    last_viewed = models.DateTimeField(null=True, blank=True)

    categories = models.ManyToManyField(WikiCategory, related_name="categories")

    tags = models.ManyToManyField(WikiTag, related_name="tags")

    article = models.OneToOneField(
        WikiArticle, on_delete=models.CASCADE, related_name="meta_data"
    )

    authors = models.ManyToManyField(WikiAuthor, related_name="authors")

    def __str__(self):
        """Return a string identifying which article this metadata belongs to."""
        return f"Metadata for {self.article.title}"
