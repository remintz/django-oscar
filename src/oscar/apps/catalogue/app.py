from django.conf.urls import url

from oscar.core.application import Application
from oscar.core.loading import get_class


class BaseCatalogueApplication(Application):
    name = 'catalogue'
    detail_view = get_class('catalogue.views', 'ProductDetailView')
    catalogue_view = get_class('catalogue.views', 'CatalogueView')
    category_view = get_class('catalogue.views', 'ProductCategoryView')
    ajax_recommendations_view=get_class('catalogue.views', 'RecommendationsView')
    ajax_jobs_view=get_class('catalogue.views', 'JobsView')
    range_view = get_class('offer.views', 'RangeDetailView')

    def get_urls(self):
        urlpatterns = super().get_urls()
        urlpatterns += [
            url(r'^$', self.catalogue_view.as_view(), name='index'),
            url(r'^(?P<product_slug>[\w-]*)_(?P<pk>\d+)/$',
                self.detail_view.as_view(), name='detail'),
            url(r'^category/(?P<category_slug>[\w-]+(/[\w-]+)*)_(?P<pk>\d+)/$',
                self.category_view.as_view(), name='category'),
            url(r'^ranges/(?P<slug>[\w-]+)/$',
                self.range_view.as_view(), name='range'),
            url(r'^ajax/recommendations', self.ajax_recommendations_view.as_view(), name='ajax_recommendation'),
            url(r'^ajax/jobs', self.ajax_jobs_view.as_view(), name='ajax_job'),
        ]
        return self.post_process_urls(urlpatterns)


class ReviewsApplication(Application):
    name = None
    reviews_app = get_class('catalogue.reviews.app', 'application')

    def get_urls(self):
        urlpatterns = super().get_urls()
        urlpatterns += [
            url(r'^(?P<product_slug>[\w-]*)_(?P<product_pk>\d+)/reviews/',
                self.reviews_app.urls)
        ]
        return self.post_process_urls(urlpatterns)


class CatalogueApplication(BaseCatalogueApplication, ReviewsApplication):
    """
    Composite class combining Products with Reviews
    """


application = CatalogueApplication()
