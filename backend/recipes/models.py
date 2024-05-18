from colorfield.fields import ColorField

from django.db import models
from django.db.models import OuterRef, Exists

from users.models import CustomUser


class Ingredient(models.Model):

    name = models.CharField(
        max_length=150,
        verbose_name='Название ингредиента',
    )

    measurement_unit = models.CharField(
        max_length=150,
        verbose_name='Единица измерения',
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class Tag(models.Model):

    name = models.CharField(
        max_length=150,
        unique=True,
        verbose_name='Тег',
    )

    color = ColorField(
        max_length=150,
        unique=True,
        verbose_name='Цвет тега',
    )

    slug = models.SlugField(
        max_length=150,
        unique=True,
        verbose_name='Слаг тега',
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class RecipeQuerySet(models.QuerySet):
    def with_annotations(self, user):
        return self.annotate(
            is_favorited=Exists(
                Selected.objects.filter(
                    recipe_id=OuterRef('pk'), author=user
                )
            ),
            is_in_shopping_cart=Exists(
                ShoppingList.objects.filter(
                    recipe_id=OuterRef('pk'), author=user
                )
            ),
        )


class RecipeManager(models.Manager):

    def get_queryset(self):
        return RecipeQuerySet(self.model, using=self._db)


class Recipe(models.Model):

    objects = RecipeQuerySet.as_manager()

    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name='Автор'
    )

    name = models.CharField(
        max_length=200,
        verbose_name='Название рецепта',
    )

    image = models.ImageField(
        upload_to='recipes/images',
        verbose_name='Изображение',
        null=False,
        blank=False,
    )

    text = models.CharField(
        max_length=150,
        verbose_name='Описание рецепта',
    )

    ingredients = models.ManyToManyField(
        Ingredient,
        verbose_name='Ингредиенты',
    )

    tags = models.ManyToManyField(
        Tag,
        verbose_name='Теги'
    )

    cooking_time = models.PositiveIntegerField(
        null=False,
        verbose_name='Время приготовления блюда',
    )

    pub_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата публикации',
    )

    class Meta:
        ordering = ('-pub_date',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def get_queryset(self):
        return Recipe.objects.all()

    def __str__(self):
        return self.name


class IngredientRecipe(models.Model):

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )

    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент',
    )

    amount = models.PositiveIntegerField(
        null=False,
        verbose_name='Количество',
    )

    class Meta:
        default_related_name = 'ingredientrecipes'
        verbose_name = 'Ингредиенты для рецепта'
        verbose_name_plural = 'Ингредиенты для рецепта'

    def __str__(self):
        return f'{self.ingredient} {self.amount}'


class ShoppingList(models.Model):

    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='shopping_cart_author',
        verbose_name='Автор',
    )

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='shopping_cart_recipe',
        verbose_name='Рецепт',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['author', 'recipe'],
                name='unique_shopping_list_pair'
            )
        ]
        default_related_name = 'shoppinglists'
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Список покупок'

    def __str__(self):
        return f'{self.user} добавил: {self.recipe}'


class Selected(models.Model):

    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name='Автор рецепта',
    )

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['author', 'recipe'],
                name='unique_selected_pair'
            )
        ]
        verbose_name = 'Отмеченные рецепты'
        verbose_name_plural = 'Отмеченные рецепты'

    def __str__(self):
        return self.recipe
