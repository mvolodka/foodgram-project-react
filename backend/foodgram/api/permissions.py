from rest_framework.permissions import SAFE_METHODS, BasePermission


class AuthorOrReadOnlyPermission(BasePermission):
    """Права доступа для автора рецепта. Автор может изменять
    и удалять объекты, созданные им."""

    def has_object_permission(self, request, view, obj):
        return (request.method in SAFE_METHODS
                or obj.author == request.user)
