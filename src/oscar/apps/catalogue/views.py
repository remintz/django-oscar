from django.contrib import messages
from django.core.paginator import InvalidPage
from django.http import HttpResponsePermanentRedirect, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import urlquote
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, TemplateView
from django.views import View
from django.core import serializers
from django.template import Context
from django.template import Template
from django.conf import settings

from oscar.apps.catalogue.signals import product_viewed
from oscar.core.loading import get_class, get_model

from easyrec.utils import get_gateway

import logging
logger = logging.getLogger(__name__)

import json
import pprint

Product = get_model('catalogue', 'product')
Category = get_model('catalogue', 'category')
ProductAlert = get_model('customer', 'ProductAlert')
ProductAlertForm = get_class('customer.forms', 'ProductAlertForm')
get_product_search_handler_class = get_class(
    'catalogue.search_handlers', 'get_product_search_handler_class')


class RecommendationsView(View):
    '''
        This is not actually a presentation layer view, but just server proxy to a client AJAX call to avoid the CORS problem
    '''
    easyrec = get_gateway()

    def get(self, request, **kwargs):
        logger.debug('RecommendationsView.get')
        params = request.GET.dict()
        logger.debug('request params: %s' % params)
        response = self.easyrec.get_user_recommendations(
            params.get('rec_type'), 
            params.get('user_id'), 
            params.get('user_age'), 
            params.get('user_gender'), 
            params.get('user_school_level'), 
            params.get('item_id'), 
            params.get('item_categories'), 
            max_results=None,
            requested_item_type=None,
            action_type=None, 
            recommendation_type=None)
        logger.debug('RecommendationsView - response returned: %s' % pprint.pformat(response))
        new_response = {}
        new_response["job_id"] = response.get('job_id')
        recommendations = response.get('recommendations')
        if recommendations:
            result = []
            for recommendation in recommendations:
                product = recommendation.get('product')
                primary_image_url = '/media/image_not_found.jpg'
                try:
                    primary_image_url = product.primary_image().original.url
                except:
                    pass
                result.append({
                    'product_title': product.title,
                    'product_url': product.get_absolute_url(),
                    'product_image_url': primary_image_url,
                    'score': recommendation.get('score')
                })
            logger.debug('recommendations result: %s' % pprint.pformat(result))
            new_response["recommendations"] = result
        return HttpResponse(json.dumps(new_response))

class JobsView(View):
    '''
        This is not actually a presentation layer view, but just server proxy to a client AJAX call to avoid the CORS problem
    '''
    easyrec = get_gateway()
    def get(self, request, **kwargs):
        logger.debug('JobsView.get')
        params = request.GET.dict()
        logger.debug('request params: %s' % params)
        recommendations = self.easyrec.get_job_status(
            params.get('job_id')
        )
        logger.debug('JobsView - recommendations returned: %s' % pprint.pformat(recommendations))
        result = []
        for recommendation in recommendations:
            product = recommendation.get('product')
            primary_image_url = '/media/image_not_found.jpg'
            try:
                primary_image_url = product.primary_image().original.url
            except:
                pass
            result.append({
                'product_title': product.title,
                'product_url': product.get_absolute_url(),
                'product_image_url': primary_image_url,
                'score': recommendation.get('score')
            })
        logger.debug('recommendations result: %s' % pprint.pformat(result))
        return HttpResponse(json.dumps(result))

class ProductDetailView(DetailView):
    context_object_name = 'product'
    model = Product
    view_signal = product_viewed
    template_folder = "catalogue"

    # Whether to redirect to the URL with the right path
    enforce_paths = True

    # Whether to redirect child products to their parent's URL. If it's disabled,
    # we display variant product details on the separate page. Otherwise, details
    # displayed on parent product page.
    enforce_parent = False

    def get(self, request, **kwargs):
        """
        Ensures that the correct URL is used before rendering a response
        """
        self.object = product = self.get_object()

        redirect = self.redirect_if_necessary(request.path, product)
        if redirect is not None:
            return redirect

        response = super().get(request, **kwargs)
        self.send_signal(request, response, product)
        return response

    def get_object(self, queryset=None):
        # Check if self.object is already set to prevent unnecessary DB calls
        if hasattr(self, 'object'):
            return self.object
        else:
            return super().get_object(queryset)

    def redirect_if_necessary(self, current_path, product):
        if self.enforce_parent and product.is_child:
            return HttpResponsePermanentRedirect(
                product.parent.get_absolute_url())

        if self.enforce_paths:
            expected_path = product.get_absolute_url()
            if expected_path != urlquote(current_path):
                return HttpResponsePermanentRedirect(expected_path)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['alert_form'] = self.get_alert_form()
        ctx['has_active_alert'] = self.get_alert_status()
        # store string with list of categories separated by ||
        product_categories = self.object.get_categories().all()
        category_names = ""
        for cat in product_categories:
            category_names += str(cat) + "||"
        if (len(category_names) > 0):
            category_names = category_names[:-2]
        ctx['product_category_list'] = category_names
        return ctx

    def get_alert_status(self):
        # Check if this user already have an alert for this product
        has_alert = False
        if self.request.user.is_authenticated:
            alerts = ProductAlert.objects.filter(
                product=self.object, user=self.request.user,
                status=ProductAlert.ACTIVE)
            has_alert = alerts.exists()
        return has_alert

    def get_alert_form(self):
        return ProductAlertForm(
            user=self.request.user, product=self.object)

    def send_signal(self, request, response, product):
        self.view_signal.send(
            sender=self, product=product, user=request.user, request=request,
            response=response)

    def get_template_names(self):
        """
        Return a list of possible templates.

        If an overriding class sets a template name, we use that. Otherwise,
        we try 2 options before defaulting to catalogue/detail.html:
            1). detail-for-upc-<upc>.html
            2). detail-for-class-<classname>.html

        This allows alternative templates to be provided for a per-product
        and a per-item-class basis.
        """
        if self.template_name:
            return [self.template_name]

        return [
            '%s/detail-for-upc-%s.html' % (
                self.template_folder, self.object.upc),
            '%s/detail-for-class-%s.html' % (
                self.template_folder, self.object.get_product_class().slug),
            '%s/detail.html' % self.template_folder]


class CatalogueView(TemplateView):
    """
    Browse all products in the catalogue
    """
    context_object_name = "products"
    template_name = 'catalogue/browse.html'

    def get(self, request, *args, **kwargs):
        try:
            self.search_handler = self.get_search_handler(
                self.request.GET, request.get_full_path(), [])
        except InvalidPage:
            # Redirect to page one.
            messages.error(request, _('The given page number was invalid.'))
            return redirect('catalogue:index')
        return super().get(request, *args, **kwargs)

    def get_search_handler(self, *args, **kwargs):
        return get_product_search_handler_class()(*args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = {}
        ctx['summary'] = _("All products")
        search_context = self.search_handler.get_search_context_data(
            self.context_object_name)
        ctx.update(search_context)
        return ctx


class ProductCategoryView(TemplateView):
    """
    Browse products in a given category
    """
    context_object_name = "products"
    template_name = 'catalogue/category.html'
    enforce_paths = True

    def get(self, request, *args, **kwargs):
        # Fetch the category; return 404 or redirect as needed
        self.category = self.get_category()
        potential_redirect = self.redirect_if_necessary(
            request.path, self.category)
        if potential_redirect is not None:
            return potential_redirect

        try:
            self.search_handler = self.get_search_handler(
                request.GET, request.get_full_path(), self.get_categories())
        except InvalidPage:
            messages.error(request, _('The given page number was invalid.'))
            return redirect(self.category.get_absolute_url())

        return super().get(request, *args, **kwargs)

    def get_category(self):
        return get_object_or_404(Category, pk=self.kwargs['pk'])

    def redirect_if_necessary(self, current_path, category):
        if self.enforce_paths:
            # Categories are fetched by primary key to allow slug changes.
            # If the slug has changed, issue a redirect.
            expected_path = category.get_absolute_url()
            if expected_path != urlquote(current_path):
                return HttpResponsePermanentRedirect(expected_path)

    def get_search_handler(self, *args, **kwargs):
        return get_product_search_handler_class()(*args, **kwargs)

    def get_categories(self):
        """
        Return a list of the current category and its ancestors
        """
        return self.category.get_descendants_and_self()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        search_context = self.search_handler.get_search_context_data(
            self.context_object_name)
        context.update(search_context)
        return context
