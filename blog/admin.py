from django.contrib import admin
from .models import *

admin.site.register(Post)
admin.site.register(Tag)
admin.site.register(Category)
admin.site.register(Author)
admin.site.register(Theme)