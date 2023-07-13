from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.db.models.expressions import Exists, OuterRef, Value
from django.http.response import FileResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response

from api.utils import get_shopping_cart
from recipes.models import (Favorite, Ingredient, IngredientRecipe, Recipe,
                            ShoppingCart, Tag)
from users.models import Follow
from .filters import IngredientFilter, RecipeFilter
from .pagination import CustomPagination
from .permissions import AuthorOrReadOnlyPermission
from .serializers import (CreateRecipeSerializer, FavoriteSerializer,
                          IngredientSerializer, RecipeReadSerializer,
                          ShoppingCartSerializer, TagSerializer,
                          UserSerializer, SubscribeListSerializer)

User = get_user_model()


class UserViewSet(DjoserUserViewSet):
    """
    Вьюсет для работы с пользователями. Для авторизованных
    пользователей возможность подписаться/отписаться.
    """
    serializer_class = UserSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        qs = User.objects.prefetch_related('follower', 'following')
        if self.request.user.is_authenticated:
            qs = qs.annotate(is_subscribed=Exists(
                self.request.user.follower
                .filter(author=OuterRef('id'))))
            return qs
        return qs.annotate(is_subscribed=Value(False))

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated],
    )
    def subscribe(self, request, pk=id):
        user = request.user
        author = get_object_or_404(User, pk=pk)
        if user == author:
            return Response({
                'errors': 'Вы не можете подписываться на самого себя!'
            }, status=status.HTTP_400_BAD_REQUEST)
        if Follow.objects.filter(user=user, author=author).exists():
            return Response({
                'errors': 'Вы уже подписаны на данного пользователя!'
            }, status=status.HTTP_400_BAD_REQUEST)
        serializer = SubscribeListSerializer(
            author, data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        Follow.objects.create(user=user, author=author)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscription(self, request, pk=id):
        subscription = get_object_or_404(Follow,
                                         user=request.user,
                                         author=get_object_or_404(
                                             User, pk=pk))
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(following__user=user)
        pages = self.paginate_queryset(queryset)
        serializer = SubscribeListSerializer(
            pages, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для отображения ингридиентов."""
    serializer_class = IngredientSerializer
    queryset = Ingredient.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly, )
    filter_backends = (IngredientFilter, )
    search_fields = ('^name', )


class TagViewSet(viewsets.ModelViewSet):
    """Вьюсет для работы с тегами."""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, )


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для работы с рецептами."""
    serializer_class = CreateRecipeSerializer
    permission_classes = (AuthorOrReadOnlyPermission, )
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend, )
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RecipeReadSerializer
        return CreateRecipeSerializer

    def get_queryset(self):
        qs = (
            Recipe
            .objects
            .select_related('author')
            .prefetch_related('tags', 'ingredients'))
        if self.request.user.is_authenticated:
            is_favorited = (
                Favorite
                .objects
                .filter(
                    user=self.request.user,
                    recipe=OuterRef('id'))),
            is_in_shopping_cart = (
                ShoppingCart
                .objects
                .filter(
                    user=self.request.user,
                    recipe=OuterRef('id')))
            qs = qs.annotate(
                is_favorited=Exists(is_favorited),
                is_in_shopping_cart=Exists(is_in_shopping_cart))
            return qs
        return qs.annotate(
            is_in_shopping_cart=Value(False),
            is_favorited=Value(False))

    @action(detail=False, methods=['GET'])
    def download_shopping_cart(self, request):
        ingredients = IngredientRecipe.objects.filter(
            recipe__shopping_list__user=request.user
        ).order_by('ingredient__name').values(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(amount=Sum('amount'))
        file = 'shopping_list.txt'
        response = FileResponse(
            get_shopping_cart(ingredients),
            content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{file}.txt"'
        return response

    @action(
        detail=True,
        methods=('POST',),
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        data = {
            'user': request.user.id,
            'recipe': recipe.id
        }
        serializer = ShoppingCartSerializer(
            data=data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def destroy_shopping_cart(self, request, pk):
        get_object_or_404(
            ShoppingCart,
            user=request.user.id,
            recipe=get_object_or_404(Recipe, id=pk)
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=('POST',),
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        data = {
            'user': request.user.id,
            'recipe': recipe.id
        }
        serializer = FavoriteSerializer(
            data=data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def destroy_favorite(self, request, pk):
        get_object_or_404(
            Favorite,
            user=request.user,
            recipe=get_object_or_404(Recipe, id=pk)
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
