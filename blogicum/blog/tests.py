"""Regression tests for visibility and author-controlled mutations."""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Category, Comment, Post


class PublicationPermissionsTests(TestCase):
    """Check publication visibility and author permissions."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user('owner')
        cls.other = get_user_model().objects.create_user('other')
        cls.category = Category.objects.create(
            title='Тест', slug='test', description='Описание',
        )
        cls.post = Post.objects.create(
            title='Заголовок', text='Текст', author=cls.owner,
            category=cls.category, pub_date=timezone.now(),
        )

    def post_url(self, name, post=None):
        return reverse('blog:' + name, args=[(post or self.post).pk])

    def test_anonymous_cannot_create(self):
        response = self.client.post(reverse('blog:create_post'), {})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Post.objects.count(), 1)

    def test_other_user_cannot_edit_or_delete(self):
        self.client.force_login(self.other)
        for name in ('edit_post', 'delete_post'):
            response = self.client.post(
                self.post_url(name), {'title': 'Changed'},
            )
            self.assertEqual(response.status_code, 302)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, 'Заголовок')

    def test_delete_get_requires_confirmation(self):
        self.client.force_login(self.owner)
        with patch('blog.views.render', return_value=HttpResponse('confirm')):
            self.client.get(self.post_url('delete_post'))
        self.assertTrue(Post.objects.filter(pk=self.post.pk).exists())
        self.client.post(self.post_url('delete_post'))
        self.assertFalse(Post.objects.filter(pk=self.post.pk).exists())

    def test_future_post_visible_only_to_author(self):
        self.post.pub_date = timezone.now() + timedelta(days=1)
        self.post.save()
        url = self.post_url('post_detail')
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.owner)
        with patch('blog.views.render', return_value=HttpResponse('post')):
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_comment_author_comes_from_session(self):
        self.client.force_login(self.other)
        response = self.client.post(self.post_url('add_comment'), {
            'text': 'Комментарий', 'author': self.owner.pk,
        })
        self.assertEqual(response.status_code, 302)
        comment = Comment.objects.get()
        self.assertEqual(comment.author, self.other)
        self.assertEqual(comment.post, self.post)

    def test_comment_must_belong_to_requested_post(self):
        comment = Comment.objects.create(
            post=self.post, author=self.owner, text='Original',
        )
        another = Post.objects.create(
            title='Другой', text='Текст', author=self.owner,
            category=self.category, pub_date=timezone.now(),
        )
        self.client.force_login(self.owner)
        url = reverse('blog:edit_comment', args=[another.pk, comment.pk])
        response = self.client.post(url, {'text': 'Changed'})
        self.assertEqual(response.status_code,
                         404)
        comment.refresh_from_db()
        self.assertEqual(comment.text, 'Original')

    def test_comment_cannot_be_deleted_by_post_owner(self):
        comment = Comment.objects.create(
            post=self.post, author=self.other, text='Original',
        )
        self.client.force_login(self.owner)
        url = reverse('blog:delete_comment', args=[self.post.pk, comment.pk])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertTrue(Comment.objects.filter(pk=comment.pk).exists())

    def test_feed_page_size_and_comment_count(self):
        for i in range(11):
            Post.objects.create(
                title=str(i), text='Text', author=self.owner,
                category=self.category, pub_date=timezone.now(),
            )
        Comment.objects.create(post=self.post, author=self.other, text='Text')
        with patch(
            'blog.views.render', return_value=HttpResponse('feed'),
        ) as view:
            self.client.get(reverse('blog:index'))
            context = view.call_args.args[2]
            self.assertEqual(len(context['page_obj']), 10)
            self.assertEqual(context['page_obj'].paginator.count, 12)
            self.client.get(reverse('blog:index'), {'page': 2})
            posts = list(view.call_args.args[2]['page_obj'])
            self.assertEqual(len(posts), 2)
            self.assertEqual(posts[-1].comment_count, 1)
