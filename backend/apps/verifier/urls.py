from django.urls import path
from .views import UploadView, VerifyView, ResultView, UploadDetailView

app_name = "verifier"

urlpatterns = [
    # Upload a file or text snippet
    path("upload/", UploadView.as_view(), name="upload"),

    # Retrieve a specific upload + its embedded result (polling)
    path("upload/<uuid:pk>/", UploadDetailView.as_view(), name="upload-detail"),

    # Trigger the verification pipeline
    path("verify/", VerifyView.as_view(), name="verify"),

    # Fetch the structured verification result
    # Accepts both result UUID and upload UUID
    path("result/<uuid:pk>/", ResultView.as_view(), name="result"),
]
