from colorfield.fields import ColorField
from django.conf import settings
from django.core.validators import (MaxValueValidator, MinValueValidator,
                                    RegexValidator)
from django.db import models


class Tag(models.Model):
    """Модель для тегов."""
    name = models.CharField(
        max_length=200,
        verbose_name='Название тега',
        unique=True,
    )
    color = ColorField(
        max_length=7,
        verbose_name='HEX-код цвета',
        format='hex',
        unique=True,
        validators=[
            RegexValidator(
                regex="^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$",
                message='Проверьте корректность вводимых данных',
            )
        ],
    )
    slug = models.SlugField(
        max_length=200,
        verbose_name='Slug',
        unique=True,
    )

    class Meta:
        ordering = ['-id']
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Модель для ингридиентов."""
    name = models.CharField(
        max_length=200,
        verbose_name='Название ингридиента',
        db_index=True,
    )
    measurement_unit = models.CharField(
        max_length=200,
        verbose_name='Еденица измерения',
    )

    class Meta:
        ordering = ['-id']
        verbose_name = 'Ингридиент'
        verbose_name_plural = 'Ингридиенты'
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_name_measurement_unit'
            )
        ]

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}.'


class Recipe(models.Model):
    """Модель для рецептов."""
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Автор рецепта',
        on_delete=models.CASCADE,
        related_name='recipes',
    )
    name = models.CharField(
        verbose_name='Название рецепта',
        max_length=200,
    )
    image = models.ImageField(
        verbose_name='Изображение рецепта',
        upload_to='recipes/image/',
    )
    text = models.TextField(
        verbose_name='Описание рецепта',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        verbose_name='Ингридиенты',
        through='IngredientRecipe',
        related_name='recipes',
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Теги'
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время готовки',
        validators=[
            MinValueValidator(
                1,
                message=(
                    'Время приготовления не '
                    'может быть меньше 1 минуты!')
            ),
            MaxValueValidator(
                180,
                message=(
                    'Время приготовления не '
                    'может быть больше 3 часов!')
            )
        ],
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата публикации',
        auto_now_add=True,
    )

    class Meta:
        ordering = ['-pub_date']
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class IngredientRecipe(models.Model):
    """Модель для связи ингридиентов и рецепта."""
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name='Ингридиент',
        on_delete=models.CASCADE,
    )
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт',
        on_delete=models.CASCADE,
        related_name='ingredient_list',
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество',
        validators=[
            MinValueValidator(
                1, message='Количество ингридиентов не может быть меньше 1!'
            )],
    )

    class Meta:
        ordering = ['-id']
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'
        constraints = [
            models.UniqueConstraint(
                fields=['ingredient', 'recipe'],
                name='unique_ingredients_recipe'
            )
        ]

    def __str__(self):
        return (
            f'{self.ingredient.name} - {self.amount}'
            f'{self.ingredient.measurement_unit}.'
        )


class ShoppingCartFavorites(models.Model):
    """Общая модель для списка покупок и избранного."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Пользователь',
        on_delete=models.CASCADE,

    )
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт',
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='%(app_label)s_%(class)s_unique_user_recipe'
            )
        ]

    def __str__(self):
        return f'{self.user}, {self.recipe}.'


class Favorite(ShoppingCartFavorites):
    """Модель для добавления рецептов в избранное."""
    class Meta(ShoppingCartFavorites.Meta):
        default_related_name = 'favorites'
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'


class ShoppingCart(ShoppingCartFavorites):
    """Модель для добавления ингридиентов в список покупок."""
    class Meta(ShoppingCartFavorites.Meta):
        default_related_name = 'shopping_cart'
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзина'
