"""Database models for publications, categories and locations."""
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()
TITLE_MAX_LENGTH = 256


class PublishedModel(models.Model):
    """Common publication status and creation timestamp."""

    is_published = models.BooleanField(
        'Опубликовано', default=True,
        help_text='Снимите галочку, чтобы скрыть публикацию.',
    )
    created_at = models.DateTimeField('Добавлено', auto_now_add=True)

    class Meta:
        """Keep shared fields in the child models only."""

        abstract = True


class Category(PublishedModel):
    """Thematic category for publications."""

    title = models.CharField('Заголовок', max_length=TITLE_MAX_LENGTH)
    description = models.TextField('Описание')
    slug = models.SlugField(
        'Идентификатор', unique=True,
        help_text=('Идентификатор страницы для URL; разрешены символы '
                   'латиницы, цифры, дефис и подчёркивание.'),
    )

    class Meta:
        """Localized category names."""

        verbose_name = 'категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        """Return the category title."""
        return self.title


class Location(PublishedModel):
    """Optional geographic label for a publication."""

    name = models.CharField('Название места', max_length=TITLE_MAX_LENGTH)

    class Meta:
        """Localized location names."""

        verbose_name = 'местоположение'
        verbose_name_plural = 'Местоположения'

    def __str__(self):
        """Return the location name."""
        return self.name


class Post(PublishedModel):
    """Publication with an author, category and scheduled publication date."""

    title = models.CharField('Заголовок', max_length=TITLE_MAX_LENGTH)
    text = models.TextField('Текст')
    image = models.ImageField('Изображение', upload_to='posts/', blank=True)
    pub_date = models.DateTimeField(
        'Дата и время публикации',
        help_text=('Если установить дату и время в будущем — '
                   'можно делать отложенные публикации.'),
    )
    author = models.ForeignKey(
        User, verbose_name='Автор публикации', on_delete=models.CASCADE,
        related_name='posts',
    )
    location = models.ForeignKey(
        Location, verbose_name='Местоположение', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='posts',
    )
    category = models.ForeignKey(
        Category, verbose_name='Категория', on_delete=models.SET_NULL,
        null=True, related_name='posts',
    )

    class Meta:
        """Show the most recent publications first."""

        ordering = ('-pub_date', '-pk')
        verbose_name = 'публикация'
        verbose_name_plural = 'Публикации'

    def __str__(self):
        """Return the publication title."""
        return self.title


class Comment(models.Model):
    """A comment belongs to a post and its author."""

    text = models.TextField('Текст')
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name='comments',
        verbose_name='Публикация',
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='comments',
        verbose_name='Автор',
    )
    created_at = models.DateTimeField('Добавлено', auto_now_add=True)

    class Meta:
        ordering = ('created_at', 'pk')
        verbose_name = 'комментарий'
        verbose_name_plural = 'Комментарии'

    def __str__(self):
        return self.text[:50]
