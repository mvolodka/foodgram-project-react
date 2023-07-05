from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from djoser.serializers import (
    UserCreateSerializer as DjoserUserCreateSerializer)
from djoser.serializers import UserSerializer as DjoserUserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField

from recipes.models import (
    Ingredient, Tag, Recipe, IngredientRecipe,
    Favorite, ShoppingCart
)

User = get_user_model()


class UserSerializer(DjoserUserSerializer):
    """Сериализатор модели пользователя."""
    is_subscribed = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
        ]

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request.user.is_anonymous:
            return False
        return obj.following.filter(user=request.user).exists()


class UserCreateSerializer(DjoserUserCreateSerializer):
    """Сериализатор для создания пользователя."""

    class Meta:
        model = User
        fields = [
            'email',
            'username',
            'first_name',
            'last_name',
            'password'
        ]


class RecipeShortSerializer(serializers.ModelSerializer):
    """Сериализатор для полей избранных рецептов и покупок."""

    class Meta:
        model = Recipe
        fields = ['id', 'name', 'image', 'cooking_time']


class SubscribeListSerializer(UserSerializer):
    """Сериализатор для получения подписок."""
    recipes_count = SerializerMethodField()
    recipes = SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ['recipes_count', 'recipes']
        read_only_fields = ['email', 'username', 'first_name', 'last_name']

    def validate(self, data):
        author_id = self.context.get(
            'request').parser_context.get('kwargs').get('id')
        author = get_object_or_404(User, id=author_id)
        user = self.context.get('request').user
        if user.follower.filter(author=author_id).exists():
            raise ValidationError(
                detail='Подписка на этого автора уже существует!',
                code=status.HTTP_400_BAD_REQUEST,
            )
        if user == author:
            raise ValidationError(
                detail='Нельзя подписаться на самого себя!',
                code=status.HTTP_400_BAD_REQUEST,
            )
        return data

    @staticmethod
    def get_recipes_count(obj):
        return obj.recipes.count()

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        recipes = obj.recipes.all()
        if limit:
            recipes = recipes[: int(limit)]
        serializer = RecipeShortSerializer(recipes, many=True, read_only=True)
        return serializer.data


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра тегов."""

    class Meta:
        model = Tag
        fields = ['id', 'name', 'color', 'slug']


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра ингридиентов."""

    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'measurement_unit']


class IngredientRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор модели, связывающей ингредиенты и рецепт."""
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientRecipe
        fields = ['id', 'name', 'amount', 'measurement_unit']


class IngredientsEditSerializer(serializers.ModelSerializer):

    id = serializers.IntegerField()
    amount = serializers.IntegerField()

    class Meta:
        model = Ingredient
        fields = ['id', 'amount']


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра рецептов."""
    tags = TagSerializer(many=True)
    author = UserSerializer(read_only=True)
    ingredients = IngredientsEditSerializer(many=True)
    is_favorited = serializers.BooleanField(read_only=True)
    is_in_shopping_cart = serializers.BooleanField(read_only=True)
    image = Base64ImageField(max_length=None)

    class Meta:
        model = Recipe
        fields = [
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time'
        ]


class CreateRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для создания/обновления рецепта."""
    ingredients = IngredientRecipeSerializer(
        many=True,
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        error_messages={'does_not_exist': 'Данного тега не существует!'}
    )
    image = Base64ImageField(max_length=None)
    author = UserSerializer(read_only=True)
    cooking_time = serializers.IntegerField()

    class Meta:
        model = Recipe
        fields = [
            'id', 'tags', 'author', 'ingredients',
            'name', 'image', 'text', 'cooking_time']

    @staticmethod
    def validate_tags(tags):
        tags_list = []
        for tag in tags:
            if tag.id in tags_list:
                raise serializers.ValidationError(
                    'Тег повторяется!')
            tags_list.append(tag.id)

        if len(tags_list) == 0:
            raise serializers.ValidationError(
                'Список тегов не должен быть пустым!')

        all_tags = Tag.objects.all().values_list('id', flat=True)
        if not set(tags_list).issubset(all_tags):
            raise serializers.ValidationError(
                'Данного тега не существует!')
            return tags

    @staticmethod
    def validate_cooking_time(cooking_time):
        if cooking_time < 1:
            raise serializers.ValidationError(
                'Время готовки не может быть меньше одной минуты!')
        return cooking_time

    @staticmethod
    def validate_ingredients(ingredients):
        ingredients_list = []
        for ingredient in ingredients:
            ingredient = ingredient['ingredient'].get('id')
            if ingredient in ingredients:
                raise serializers.ValidationError(
                    'Ингредиент повторяется!')
            ingredients.append(ingredient)
        all_ingredients = Ingredient.objects.all().values_list(
            'id', flat=True)
        if not set(ingredients_list).issubset(all_ingredients):
            raise serializers.ValidationError(
                'Указанного ингредиента не существует!')
        if len(ingredients_list) == 0:
            raise serializers.ValidationError(
                'Список ингредиентов не должен быть пустым!')
        return ingredients

    @staticmethod
    def create_ingredients(recipe, ingredients):
        ingredient_list = []
        for ingredient_data in ingredients:
            ingredient_list.append(
                IngredientRecipe(
                    ingredient=ingredient_data.pop('id'),
                    amount=ingredient_data.pop('amount'),
                    recipe=recipe,
                )
            )
        IngredientRecipe.objects.bulk_create(ingredient_list)

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get('request', None)
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(author=request.user, **validated_data)
        recipe.tags.set(tags)
        self.create_ingredients(recipe, ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        instance.tags.clear()
        IngredientRecipe.objects.filter(recipe=instance).delete()
        instance.tags.set(validated_data.pop('tags'))
        ingredients = validated_data.pop('ingredients')
        self.create_ingredients(instance, ingredients)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context={
            'request': self.context.get('request')
        }).data


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для избранных рецептов."""

    class Meta:
        model = Favorite
        fields = ['user', 'recipe']

    def validate(self, data):
        user = data['user']
        if user.favorites.filter(recipe=data['recipe']).exists():
            raise serializers.ValidationError(
                'Рецепт уже был добавлен в избранное!'
            )
        return data

    def to_representation(self, instance):
        return RecipeShortSerializer(
            instance.recipe,
            context={'request': self.context.get('request')}
        ).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для списка покупок."""

    class Meta:
        model = ShoppingCart
        fields = ['user', 'recipe']

    def validate(self, data):
        user = data['user']
        if user.shopping_list.filter(recipe=data['recipe']).exists():
            raise serializers.ValidationError(
                'Рецепт уже добавлен в список покупок!'
            )
        return data

    def to_representation(self, instance):
        return RecipeShortSerializer(
            instance.recipe,
            context={'request': self.context.get('request')}
        ).data
