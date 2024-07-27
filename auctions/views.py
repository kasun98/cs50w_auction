from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.db.models import OuterRef, Subquery
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Max
import math

from .models import User, Item, Bid, Comments, Watchlist


def index(request):
    items = Item.objects.annotate(current_bid_price=Max('bid__current_bid')).order_by('-id')
    try:
        watchlists = Watchlist.objects.filter(uid=request.user).count()
    except:
        watchlists = None
  
    return render(request, "auctions/index.html", {
        "items":items,
        "basket":watchlists})


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")
    
def watchlist(request):
    try:
        watchlists=get_watchlist_with_current_bids(request)
        
        if request.method == "POST":
            item_id = request.POST.get('item_id')
            watchlist = Watchlist.objects.filter(item_id=item_id, uid=request.user)
            watchlist.delete()

        return render(request, "auctions/watchlist.html", {
            "basket":watchlists.count(),
            "basket_items":watchlists.order_by('-time')
        })
    except:
        return HttpResponseRedirect(reverse("index"))


def get_watchlist_with_current_bids(request):
    # Query for the latest bid for each item
    latest_bid_subquery = Bid.objects.filter(item_id=OuterRef('item_id')).order_by('-id').values('current_bid')[:1]

    # Get the watchlist items for the current user with the latest bid prices
    watchlists = Watchlist.objects.filter(uid=request.user).select_related('item_id')
    watchlists = watchlists.annotate(current_bid=Subquery(latest_bid_subquery))

    return watchlists

@login_required
def create_listing(request):

    if request.method == "POST":
        name = request.POST["name"]
        description = request.POST["description"]
        start_bid = request.POST["start_bid"]
        img_url = request.POST.get("img_url", "")
        category = request.POST.get("category", "")
        
        item = Item.objects.create(
            owner=request.user,
            name=name,
            description = description,
            start_bid=start_bid,
            img_url = img_url if img_url else None, # Set to None if empty
            category=category if category else None,  # Set to None if empty
            status = "Y"
        )
        messages.success(request, 'Item is created successfully!')
        return redirect("index")
    
    try:
        watchlists = Watchlist.objects.filter(uid=request.user).count()
    except:
        watchlists = None

    return render(request, "auctions/create.html", {
        "basket":watchlists
    })

def categories(request):
    try:
        watchlists = Watchlist.objects.filter(uid=request.user).count()
    except:
        watchlists = None
    
    return render(request, "auctions/categories.html", {
        "basket":watchlists})

def category(request, name):
    
    try:
        watchlists = Watchlist.objects.filter(uid=request.user).count()
    except:
        watchlists = None

    list = ["Electronics","Fashion","Home","Toys","Other"]
    if name in list:
        items = Item.objects.filter(category=name).annotate(current_bid_price=Max('bid__current_bid')).order_by('-created_at')
        return render(request, "auctions/category.html", {
            "items":items,
            "basket":watchlists,
            "name":name})
    
    else:
        messages.warning(request, 'Not a category')
        return redirect("categories")


# listing view
def listings(request, id):

    item = get_object_or_404(Item, id=id)
    bid =  Bid.objects.filter(item_id=item).order_by('-current_bid').first()
    comments = Comments.objects.filter(item_id=item).order_by('-time')
    try:
        watchlist = Watchlist.objects.filter(item_id=item, uid=request.user).first()
    except:
        watchlist = None

    if request.method == "POST":
        form_type = request.POST.get('form_type')
        if form_type == 'Place Bid':
            return handle_bid(request, item, bid)
        elif form_type == 'watchlist_button':
            return handle_watchlist(request, item, watchlist)
        elif form_type == 'Finish Sale':
            return handle_finish(request, item, bid)
        elif form_type == 'Delete Item':
            return handle_delete(request, item, bid)
        elif form_type == 'Post Comment':
            return handle_comments(request, item)
       
    try:
        try:
            watchlists = Watchlist.objects.filter(uid=request.user).count()
        except:
            watchlists = None
            
        if bid:
            current_bid = round(float(bid.current_bid),2)
            min_bid = round(current_bid + 0.01, 2)
        
        else:
            current_bid = round(float(item.start_bid),2)
            min_bid = round(current_bid, 2)

        return render(request, "auctions/listings.html", {
            "item":item,
            "Bid":bid,
            "current_bid": current_bid,
            "min_bid": min_bid,
            "comments": comments,
            "watchlist": watchlist,
            "basket":watchlists
        })
    except:
        return HttpResponseRedirect(reverse("index"))
    
def handle_bid(request, item, bid):
    bid_amount = request.POST["bid"]
    sprice = item.start_bid
    cstatus = item.status

    try:
        if bid == None and cstatus=="Y" and round(float(bid_amount),2)>=round(sprice,2):
            bid = Bid.objects.create(
                item_id=item,
                n_bids=1,
                current_bid = bid_amount,
                current_bidder_id=request.user
            )
            return redirect("listings", id=item.id)
        elif bid == None and cstatus=="Y" and math.isclose(float(bid_amount), sprice, rel_tol=1e-9):
            bid = Bid.objects.create(
                item_id=item,
                n_bids=1,
                current_bid = bid_amount,
                current_bidder_id=request.user
            )
            return redirect("listings", id=item.id)
        
        elif cstatus=="Y" and round(float(bid_amount),2)>round(bid.current_bid,2):
            bid.n_bids=bid.n_bids+1
            bid.current_bid = bid_amount
            bid.current_bidder_id=request.user
            bid.save()
            return redirect("listings", id=item.id)
        
        elif cstatus=="Y" and round(float(bid_amount),2)<=round(bid.current_bid,2):
            messages.warning(request, 'Increase your Bid amount')
            return redirect("listings", id=item.id)
        
        elif cstatus=="N":
            messages.warning(request, 'Auction closed!')
            return redirect("listings", id=item.id)
        
    except:
        messages.warning(request, 'Error')
        return redirect("listings", id=item.id)

@login_required
def handle_watchlist(request, item, watchlist):
    try:
        if watchlist == None:
            watchlist = Watchlist.objects.create(
                uid = request.user,
                item_id=item,
                watch = "Y"
            )
            messages.success(request, 'Added to watchlist')
            return redirect("listings", id=item.id)
        
        elif watchlist.watch == "Y":
            watchlist.delete()
            messages.success(request, 'Removed from watchlist')
            return redirect("listings", id=item.id)
        
    except:
        messages.warning(request, 'Error')
        return redirect("listings", id=item.id)

def handle_finish(request, item, bid):
    if item.owner == request.user and bid != None:
        item.status = "N"
        item.save()
        messages.success(request, 'Item Sold!')
        return redirect("listings", id=item.id)
    else:
        messages.warning(request, 'No bids Yet')
        return redirect("listings", id=item.id)
    
def handle_delete(request, item, bid):
    if item.owner == request.user:
        item.delete()
        messages.success(request, 'Item Deleted!')
        return redirect("index")
    else:
        messages.warning(request, 'Something went wrong')
        return redirect("listings", id=item.id)

@login_required   
def handle_comments(request, item):
    comnt = str(request.POST["comment"]).strip()
    if comnt:
        comment = Comments.objects.create(
                item_id=item,
                commenter_id=request.user,
                comment = comnt
            )
        messages.success(request, 'Comment added')
        return redirect("listings", id=item.id)
    
    else:
        messages.warning(request, 'Cannot add empty comments')
        return redirect("listings", id=item.id)

# end of listing view