from django.contrib import admin

# Register your models here.
from .models import User, Item, Bid, Comments, Watchlist

admin.site.register(User)
admin.site.register(Item)
admin.site.register(Bid)
admin.site.register(Comments)
admin.site.register(Watchlist)
