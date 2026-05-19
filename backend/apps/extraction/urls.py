from django.urls import path
from .views import ImageExtractView, VideoExtractView

app_name = "extraction"

urlpatterns = [
    # Direct OCR: POST multipart/form-data with `file` (image)
    path("extract/image/", ImageExtractView.as_view(), name="extract-image"),

    # Direct STT: POST multipart/form-data with `file` (video)
    path("extract/video/", VideoExtractView.as_view(), name="extract-video"),
]
