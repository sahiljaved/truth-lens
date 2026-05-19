from django.urls import path
from .views import NewsSearchView, VerifyTextView

app_name = "fact_check"

urlpatterns = [
    # Search GNews for articles related to a query
    path("fact-check/search/", NewsSearchView.as_view(), name="news-search"),

    # Score extracted text against articles (auto-fetches if none provided)
    path("fact-check/verify/", VerifyTextView.as_view(), name="verify-text"),
]
