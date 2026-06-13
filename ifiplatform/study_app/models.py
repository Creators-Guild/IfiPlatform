from django.db import models
from django.conf import settings
from typing import TYPE_CHECKING

# Create your models here.
class Deck(models.Model):
    # one-to-many with one user
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # if user deleted, keep deck
        null=True,
        related_name="decks" # how to access all decks to user
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    class Meta:
        # make sure that the same user can't have mutiple deck with same name
        # diffrent user can still have decks sharing the same name
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"],
                name="unique_deck_name_per_owner",
            )
        ]
    
    if TYPE_CHECKING:
        # This is only for Pylance / type checkers, not used at runtime
        # Just used to remove errorline when ex. 'deck.cards.all()'
        from django.db.models.manager import RelatedManager
        cards: RelatedManager["Card"]

    def __str__(self):
        return self.name


class Card(models.Model):
    deck = models.ForeignKey(
        Deck,
        on_delete=models.SET_NULL,
        null=True,
        related_name="cards"
    )
    front = models.TextField() # question
    back = models.TextField() # answer
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_reviewed = models.DateTimeField(null=True, blank=True)
    times_correct = models.PositiveIntegerField(default=0)
    times_incorrect = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.front[:50]