from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from django.http import HttpResponse
# from .models import Article, Content, Issue , Subscriber# '.' signifies the current directory
from .models import Article, Content, Image, Issue, Contributor, ShopItem # '.' signifies the current directory
from .forms import UploadShopItemForm
from blog.models import Post, Author
from collections import OrderedDict
from itertools import chain
import json
import stripe
from django.conf import settings
import random
import re
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import MultipleObjectsReturned
from advertisement.helper import getAds

from haystack.query import SearchQuerySet
from haystack.views import SearchView
from haystack.forms import SearchForm
from django.shortcuts import redirect
from itertools import chain
import logging


logger = logging.getLogger("magazine")

# Create your views here.
def index(request):
  issue = Issue.objects.last()

  # for each article with this issue id
  articles_in_issue = Article.objects.published().filter(issue=issue)
  data = {
    'blog': { },
    'sections': { },
    'issue': issue,
  }
  # Put articles into their respective sections
  for article in articles_in_issue:
    SectionName = str(article.section).lower()
    if SectionName not in data['sections']:
      data['sections'][SectionName] = [article]
    else:
        data['sections'][SectionName].append(article)
  data['sections']['art'] =  Image.objects.published().filter(issue=issue)

  all_issues = Issue.objects.all()
  season = {'Winter': 0, 'Spring': 1, 'Commencement': 2, 'Fall': 3}

  #all_issues_sorted = reversed(sorted(all_issues, key=lambda i: i.year))
  all_issues_sorted = reversed(sorted(all_issues, key=lambda i: i.year * 10 + season[i.issue]))

  data['issues'] = all_issues_sorted

  # Randomly choice an article for every section
  for key in data['sections']:
    if data['sections'][key]:
      data['sections'][key]= random.choice(data['sections'][key]) 
  posts = Post.objects.all()
  recent_blog = list(reversed(sorted(posts, key=lambda i: i.created)))[:3 ]
  data['blog']['post1'] = recent_blog[0]
  data['blog']['post2'] = recent_blog[1]
  data['blog']['post3'] = recent_blog[2]


  data['toplist'] = [{'title' : "article one", 'url' : "google.com", 'author' : "samantha"}, {'title' : "article two", 'url' : "google.com", 'author' : "cameron"}, {'title' : "article three", 'url' : "google.com", 'author' : "joe"}]

  data['ads'] = getAds('home')

  template_name = 'index.html'
  return render_to_response(template_name, data, context_instance=RequestContext(request))

def article(request, id, slug):
  article = get_object_or_404(Article, id=id)
  data = {
    'article': article
  }
  template_name = 'article.html'
  return render_to_response(template_name, data, context_instance=RequestContext(request))

def content_piece(request, slug):
  if slug.isdigit():
    image = get_object_or_404(Content, id=slug)
  else: # handle legacy links in the form of /content/short-slug
    try:
      image = Content.objects.get(slug__iexact=slug)
    except ObjectDoesNotExist:
      # check if linked slug is simply shortened and missing words
      slug_regex = r"[a-zA-Z\d_\-]*" + slug.replace("-", r"-([a-zA-Z\d_\-]+-)?") + r"[a-zA-Z\d_\-]*"
      try:
        image = Content.objects.get(slug__iregex=slug_regex)
      except (MultipleObjectsReturned, ObjectDoesNotExist):
        # search the words instead if there isn't exactly one match
        slug = slug.replace("-","+")
        return redirect('/search/?q=' + slug)
  # print image.contributors
  data = {
    'art_content': image
  }
  template_name = 'content.html'
  # if not data['art_content']:
  #   print "here"
  return render_to_response(template_name, data, context_instance=RequestContext(request))

def contributor_page(request, author_id, name):
  author =  get_object_or_404( Contributor, id=author_id, name = name.replace("_", " "))
  # author.name = name.replace("_", " ")
  # author.id = author_id
  data = {}
  data["author"] = author.name
  data["articles"] =  chain( Article.objects.filter(contributors=author) , Image.objects.filter(contributors=author))
  template_name = 'contributor.html'
  return render_to_response(template_name, data, context_instance=RequestContext(request))


def issues(request):
  all_issues = Issue.objects.all()
  season = {'Winter': 0, 'Spring': 1, 'Commencement': 2, 'Fall': 3}

  #all_issues_sorted = reversed(sorted(all_issues, key=lambda i: i.year))
  all_issues_sorted = reversed(sorted(all_issues, key=lambda i: i.year * 10 + season[i.issue]))
  data = {
    'issues': all_issues_sorted
  }
  template_name = 'issues.html'
  return render_to_response(template_name, data, context_instance=RequestContext(request))



def masthead(request):
  template_name = 'about_us.html'
  return render_to_response(template_name, context_instance=RequestContext(request))

def singleissue(request, season, year):
  template_name = 'singleissue.html'
  issue = get_object_or_404(Issue, issue__iexact=season, year=year)

  # TODO: Once we figure out contenttypes, bring back this line!
  # issue_content = Content.objects.filter(issue=issue)

  content = OrderedDict()

  articles_in_issue = Article.objects.published().filter(issue=issue)

  for article in articles_in_issue:
    SectionName = str(article.section).lower()
    if SectionName not in content:
     content[SectionName] = [article]
    else:
       content[SectionName].append(article)
  content['art'] =  Image.objects.published().filter(issue=issue)

  # issue_content = Article.objects.filter(issue=issue)
  # section = ('Features','Fiction','Poetry')

  # content = OrderedDict()
  # for s in section:
  #   content[s] = issue_content.published().filter(section__name=s)
  # content['Art'] =  Image.objects.published().filter(issue=issue)
  data = {
    'issue' : issue,
    'content_list' : content
    }

  return render_to_response(template_name, data, context_instance=RequestContext(request))

class FilterSearchView(SearchView):
        template_name = 'search/search.html'
        queryset = SearchQuerySet().all()
        form_class = SearchForm
        type_filter = 'all'

        def __call__(self, request, type_filter = None):

                self.request = request

                self.form = self.build_form()
                self.query = self.get_query()
                self.results = self.get_results()

                if type_filter is not None:
                        self.results = self.results.filter(section=type_filter)
                        self.type_filter = type_filter
                else:
                        self.type_filter = 'all'

                return self.create_response()

        def extra_context(self):
                return {'type_filter' : self.type_filter}

        def create_response(self):
                (pageinator, page) = self.build_page()

                context = {
                        'query' : self.query,
                        'form' : self.form,
                        'page' : page,
                        'pageinator' : pageinator,
                        'suggestion' : None,
                }

                context['suggestion'] = self.form.get_suggestion()

                #for dict in Contributor.objects.all():
                #        if (dict['name'] == self.query):
                #                print dict

                try:
                        return redirect(Article.objects.get(title = self.query))
                except Article.DoesNotExist:
                        pass

                try:
                        return redirect(Contributor.objects.get(name = self.query))
                except Contributor.DoesNotExist:
                        pass
                try:
                        return redirect(Post.objects.get(title = self.query))
                except Post.DoesNotExist:
                        pass
                try:
                        return redirect(Author.objects.get(name = self.query))
                except Author.DoesNotExist:
                        pass

                context.update(self.extra_context())
                return render_to_response(self.template, context, context_instance=self.context_class(self.request))


def subscribe(request):
  template_name = 'subscribe.html'
  return render_to_response(template_name, context_instance=RequestContext(request))

def gala(request):
  template_name = 'gala.html'
  return render_to_response(template_name, context_instance=RequestContext(request))

def financialaid(request):
  template_name = 'financialaid.html'
  return render_to_response(template_name, context_instance=RequestContext(request))


def stripeSubmit(request):
  # Get the credit card details submitted by the form
  token = request.POST['stripeToken']
  stripe.api_key = settings.STRIPE_SECRET_KEY
  # Create the charge on Stripe's servers - this will charge the user's card
  try:
    charge = stripe.Charge.create(
      amount=123, # amount in cents, again
      currency="usd",
      card=token,
      description="payinguser@example.com",
    )

    subscriber = Subscriber.objects.create(
      name=request.POST['name'],
      email=request.POST['email'],
      streetAddress1=request.POST['streetAddress1'],
      streetAddress2=request.POST['streetAddress2'],
      city=request.POST['city'],
      state=request.POST['state'],
      country=request.POST['country'],
      zipCode=request.POST['zipCode'],
      renew=request.POST['renew'],
      subscriptionType=request.POST['subscriptionType'],
    )
    return subscribe(request)
  except stripe.CardError, e:
    # The card has been declined
    pass

def sections(request):
  section = request.path
  section = section.replace("/","")

  # For all issues
  all_issues = Issue.objects.all()
  season = {'Winter': 0, 'Spring': 1, 'Commencement': 2, 'Fall': 3}
  all_issues = reversed(sorted(all_issues, key=lambda i: i.year))
  #all_issues_sorted = reversed(sorted(all_issues, key=lambda i: i.year * 10 + season[i.issue]))
  data = {
    "name":section,
    "issues": []
  }

  for issue in all_issues:
    articles_in_issue = Article.objects.published().filter(issue=issue, section__name =section)
    if section == "art":
      if articles_in_issue:
        articles_in_issue = list(chain(articles_in_issue,Image.objects.published().filter(issue=issue, section__name =section) ))
      else:
        articles_in_issue = Image.objects.published().filter(issue=issue, section__name =section)

    datum = {
      'obj':issue,
      'articles': articles_in_issue
      }

    data["issues"].append(datum)


    data['ads'] = getAds(section)

  # for issue in data["issues"]:
  #   for article in issue["articles"]:
  #     print article.contributors.all()

  template_name = 'section.html'
  return render_to_response(template_name, data, context_instance=RequestContext(request))

def submit(request):
  template_name = 'submit.html'
  return render_to_response(template_name, context_instance=RequestContext(request))

def contact(request):
  template_name = 'contact_us.html'
  return render_to_response(template_name, context_instance=RequestContext(request))

def alumni(request):
  template_name = 'alumni.html'
  return render_to_response(template_name, context_instance=RequestContext(request))

def advertise(request):
  template_name = 'advertise.html'
  return render_to_response(template_name, context_instance=RequestContext(request))

def adSubmit(request):
  template_name = 'adSubmit.html'
  return render_to_response(template_name, context_instance=RequestContext(request))

def shop(request):
  all_items = ShopItem.objects.all()
  data = {
    'items': all_items,
    'page': 'shop',
  }
  template_name = 'shop.html'
  return render_to_response(template_name, data, context_instance=RequestContext(request))

def shopItemView(request, id):
  item = ShopItem.objects.filter(id=id)
  if item:
    data = {
      'item': item[0],
      'page': 'shopItemView',
    }
    template_name = 'shop_item_view.html'
    return render_to_response(template_name, data, context_instance=RequestContext(request))
  else: # item does not exist
    return HttpResponse('404: Page not found.')


def shop_admin(request):
  if request.method == 'GET':
    form = UploadShopItemForm()
    return render_to_response('shop-admin.html', {'shop_items': ShopItem.objects.all(), 'form': form}, context_instance=RequestContext(request))
  #return HttpResponse("")
  return HttpResponse("<script>window.location = window.location.origin + '/shop-admin';</script>")

def shop_upload(request):
  if request.method == 'POST':
    item_name = request.POST['name']
    item_description = request.POST['description']
    item_price = request.POST['price']
    item_imagefile = request.POST['imagefile']
    new_item = ShopItem(name=item_name, description=item_description, price=item_price)#, profile_image=item_imagefile)
    new_item.save()
    return render_to_response('shop-admin.html', {}, context_instance=RequestContext(request))
  return HttpResponse("There's nothing here.")

def shop_delete(request):
  if request.method == 'POST':
    print "request.POST:"
    print dir(request.POST)
    print "keys"
    print request.POST.keys()
    print "token"
    print request.POST['csrfmiddlewaretoken']
    ShopItem.objects.filter(id=request.POST['id']).delete()
    return HttpResponse("success!")

def cart(request):
  if request.method == 'GET':
    cartSession = request.session.get('cartItems', False)
    if cartSession:
      all_items = ShopItem.objects.filter(id__in=cartSession)
      purchase_description = [itm.title for itm in all_items]
      purchase_description = ', '.join(purchase_description)
      purchase_description = purchase_description.replace('"', "'")
      total = int(sum([item.price for item in all_items])*100)
      totalStr = str(total)
      totalStr = totalStr[:-2] + "." + totalStr[-2:]
      data = {'items': all_items, 'page': 'cart', 'total': total, 'totalStr': totalStr, 'purchaseDescription': purchase_description}
      return render_to_response("cart.html", data, context_instance=RequestContext(request))
    else:
      data = {'items': [], 'page': 'cart'}
      return render_to_response("cart.html", data, context_instance=RequestContext(request))
  if request.method == 'POST':
    if request.POST['itemId']:
      cartSession = request.session.get('cartItems', False)
      # insert request
      if request.POST['action'] == "insert":
        if cartSession:
          if request.POST['itemId'] in cartSession:
            return HttpResponse('{"code": 1, "responseText": "Item already added."}')
          else:
            request.session['cartItems'].append(request.POST['itemId'])
            request.session.modified = True
        else:
          request.session['cartItems'] = [request.POST['itemId']]
          request.session.modified = True
        return HttpResponse('{"code": 0, "responseText": "success!"}')
      # delete request
      elif request.POST['action'] == "delete":
        if request.POST['itemId'] in cartSession:
          cartSession = [i for i in cartSession if i != request.POST['itemId']]
          request.session['cartItems'] = cartSession
          request.session.modified = True
          return HttpResponse('{"code": 0, "responseText": "success!"}')
        else:
          return HttpResponse('{"code": 0, "responseText": "nothing to delete."}')
      else:
        return HttpResponse('{"code": 4, "responseText": "Invalid action"}')
    else:
      return HttpResponse('{"code": 2, "responseText": "Invalid post data."}')
  return HttpResponse('{"code": 3, "responseText": "Invalid request"}')

def onefifty(request):
  template_name = '150th.html'
  return render_to_response(template_name, context_instance=RequestContext(request))

def comp(request):
  template_name = 'comp.html'
  return render_to_response(template_name, context_instance=RequestContext(request))
