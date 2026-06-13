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
    name = models.CharField(max_length=100)
    
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name="subcategories",
        null=True,
        blank=True
    )
    
    def __str__(self):
        return self.name


# simple tag object
class WikiTag(models.Model):
    name = models.CharField(max_length=20)
    
    def __str__(self):
        return self.name


# wrapper object for user incase user is deleted
class WikiAuthor(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        related_name='author',
        null=True
    )
    name = models.CharField(max_length=200)
        
    def save(self, *args, **kwargs):
        # Each time we save, if there is an non-deleted user, sync name
        if self.user is not None:
            self.name = self.user.username
        super().save(*args, **kwargs)
    
    def __str__(self) -> str:
        return self.name

# # Edit history
# class WikiArticle_Edit(models.Model):
#     editer = models.ForeignKey(
#         WikiAuthor,
#         on_delete=models.SET_NULL
#     )
#     date = models.DateTimeField()


# simple model for a wikiArticle
class WikiArticle(models.Model):
    title = models.CharField(max_length=200)
    intro_text = models.TextField()
    body = models.TextField()
    image_name = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f'{self.title}'


# simple model for a metadata for a wikiarticle
class WikiArticle_Meta(models.Model):
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_edited = models.DateTimeField(auto_now=True) # updates everytime the object is updated
    views = models.PositiveIntegerField(default=0)
    last_viewed = models.DateTimeField(null=True, blank=True)
    
    categories = models.ManyToManyField(
        WikiCategory,
        related_name="categories"
    )
    
    tags = models.ManyToManyField(
        WikiTag,
        related_name="tags"
    )
    
    article = models.OneToOneField(
        WikiArticle,
        on_delete=models.CASCADE,
        related_name='meta_data'
    )

    authors = models.ManyToManyField(
        WikiAuthor,
        related_name="authors"
    )

    def __str__(self):
        return f'Metadata for {self.article.title}'

