from django.contrib import admin

from article.models import Article, Category, Tag, Comment, CommentModerationKeyword


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'created_at', 'updated_at']
    search_fields = ['name']
    ordering = ['-created_at']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'created_by', 'created_at']
    search_fields = ['name']
    ordering = ['-created_at']


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'category', 'status', 'view_count', 'like_count', 'comment_count', 'published_at', 'created_at']
    list_filter = ['status', 'category', 'tags']
    search_fields = ['title', 'summary']
    ordering = ['-created_at']
    filter_horizontal = ['tags']
    readonly_fields = ['slug', 'view_count', 'like_count', 'comment_count']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'article', 'author', 'status', 'moderation_reason', 'reviewed_by', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['content', 'author__username']
    ordering = ['-created_at']
    readonly_fields = ['moderation_reason', 'reviewed_by', 'reviewed_at', 'content_fingerprint']

    def has_add_permission(self, request):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [*self.readonly_fields, 'article', 'author', 'parent']

    def save_model(self, request, obj, form, change):
        from django.utils import timezone
        from article.services.comment_moderation import moderate_comment

        if 'content' in form.changed_data and 'status' not in form.changed_data:
            obj.status, obj.moderation_reason = moderate_comment(obj.content, author=obj.author)
            obj.reviewed_by = None
            obj.reviewed_at = None
        else:
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(CommentModerationKeyword)
class CommentKeywordAdmin(admin.ModelAdmin):
    list_display = ['word', 'action', 'enabled', 'source', 'description', 'updated_at']
    list_filter = ['action', 'enabled', 'source']
    search_fields = ['word', 'description']
    readonly_fields = ['source', 'created_by', 'updated_by']

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
