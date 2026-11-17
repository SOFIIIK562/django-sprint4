"""Forms expose only the fields visitors may change."""
from django import forms
from django.contrib.auth import get_user_model

from .models import Comment, Post


class PostForm(forms.ModelForm):
    """Create or update a post without changing its author."""

    class Meta:
        model = Post
        fields = ('title', 'text', 'pub_date', 'category', 'location', 'image')
        widgets = {
            'pub_date': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'},
            ),
        }


class CommentForm(forms.ModelForm):
    """Accept comment text; assign post and author on the server."""

    class Meta:
        model = Comment
        fields = ('text',)


class ProfileForm(forms.ModelForm):
    """Allow the account owner to edit public profile details."""

    class Meta:
        model = get_user_model()
        fields = ('first_name', 'last_name', 'username', 'email')
