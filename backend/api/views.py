from dataclasses import asdict, dataclass

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, AllowAny, IsAuthenticated
from rest_framework.response import Response
from djoser.views import UserViewSet

from recipes.models import (Ingredient, Recipe, Selected,
                            ShoppingList, Tag)
from users.models import CustomUser, Follow
from api.filters import RecipeFilter, IngredientSearchFilter
from api.permissions import IsAuthorOrReadOnly
from api.services import get_shopping_list
from . import paginations, serializers


class UserViewSet(UserViewSet):
    @dataclass
    class ErrorMessages:
        USER_NOT_FOUND: str = 'Такого пользователя не существует!'
        UNAUTHORIZED: str = 'Необходимо авторизоваться!'
        SUBSCRIBE_SELF: str = 'Невозможно подписаться на самого себя!'
        ALREADY_SUBSCRIBED: str = 'Вы уже подписаны на этого пользователя!'

    error_messages = asdict(ErrorMessages())

    permission_classes = (AllowAny,)
    pagination_class = paginations.LimitPageNumberPagination

    def get_permissions(self):
        if self.request.path.endswith('me/'):
            return (IsAuthenticated(),)
        elif self.action in ('retrieve', 'list'):
            return (AllowAny(),)
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'subscribe':
            return serializers.FollowSerializer
        return super().get_serializer_class()

    @action(detail=True, methods=('post',), pagination_class=None)
    def subscribe(self, request, id):
        if not CustomUser.objects.filter(pk=id).exists():
            return Response(
                {'errors': self.error_messages['USER_NOT_FOUND']},
                status=status.HTTP_404_NOT_FOUND
            )
        author = CustomUser.objects.get(pk=id)
        user = request.user

        if not user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        if user == author:
            return Response(
                {'errors': self.error_messages['SUBSCRIBE_SELF']},
                status=status.HTTP_400_BAD_REQUEST
            )
        if Follow.objects.filter(user=user, author=author).exists():
            return Response(
                {'errors': self.error_messages['ALREADY_SUBSCRIBED']},
                status=status.HTTP_400_BAD_REQUEST
            )

        Follow.objects.create(user=user, author=author)
        serializer = serializers.FollowSerializer(
            author, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, id):
        if not CustomUser.objects.filter(pk=id).exists():
            return Response(
                {'errors': self.error_messages['USER_NOT_FOUND']},
                status=status.HTTP_404_NOT_FOUND
            )
        author = CustomUser.objects.get(pk=id)
        user = request.user

        if not user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        connection = Follow.objects.filter(user=user, author=author)
        if connection.exists():
            connection.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(
            {'errors': self.error_messages['ALREADY_SUBSCRIBED']},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=False, methods=('GET',),
        pagination_class=paginations.LimitPageNumberPagination,
    )
    def subscriptions(self, request):
        queryset = CustomUser.objects.filter(author__user=self.request.user)
        serializer = serializers.FollowSerializer(
            self.paginate_queryset(queryset),
            context=dict(request=request),
            many=True,
        )
        return self.get_paginated_response(serializer.data)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = serializers.TagSerializer
    permission_classes = (AllowAny, )
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = serializers.IngredientSerializer
    permission_classes = (AllowAny, )
    filter_backends = (IngredientSearchFilter,)
    search_fields = ('^name',)
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthorOrReadOnly,)
    filterset_class = RecipeFilter
    filter_backends = (DjangoFilterBackend,)
    pagination_class = paginations.LimitPageNumberPagination
    http_method_names = ['get', 'post', 'delete', 'patch']

    def get_queryset(self):
        user = self.request.user
        if user and user.is_authenticated:
            return Recipe.objects.with_annotations(user).select_related(
                'author'
            )
        return Recipe.objects.select_related('author').prefetch_related('tags')

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return serializers.RecipeListSerializer
        return serializers.AddUpdateDeleteRecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def create_connection(self, model, user, pk):
        if not Recipe.objects.filter(id=pk).exists():
            return Response(
                {'errors': 'Рецепт не существует!'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if model.objects.filter(author=user, recipe__id=pk).exists():
            return Response(
                {'errors': 'Рецепт уже в списке!'},
                status=status.HTTP_400_BAD_REQUEST
            )
        recipe = Recipe.objects.get(pk=pk)
        model.objects.create(author=user, recipe=recipe)
        serializer = serializers.RecipeFollowSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete_connection(self, model, user, pk):
        if not Recipe.objects.filter(id=pk).exists():
            return Response(
                {'errors': 'Рецепт не существует!'},
                status=status.HTTP_404_NOT_FOUND
            )
        connection = model.objects.filter(author=user, recipe__id=pk)
        if connection.exists():
            connection.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'errors': 'Рецепт был удален ранее!'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=('POST', 'DELETE'),)
    def favorite(self, request, pk=None):
        if request.method == 'POST':
            return self.create_connection(
                Selected, request.user, pk
            )
        return self.delete_connection(
            Selected, request.user, pk
        )

    @action(detail=True, methods=('POST', 'DELETE'),)
    def shopping_cart(self, request, pk=None):
        if request.method == 'POST':
            return self.create_connection(
                ShoppingList, request.user, pk
            )
        return self.delete_connection(
            ShoppingList, request.user, pk
        )

    @action(detail=False,
            methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        author = CustomUser.objects.get(id=self.request.user.pk)

        return get_shopping_list(self, request, author)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)
