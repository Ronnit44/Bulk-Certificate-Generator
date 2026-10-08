from django.urls import path
from .views import CertificateDownloadView, GenerationJobDetailView, GenerationJobListCreateView

urlpatterns = [
    path("jobs/", GenerationJobListCreateView.as_view(), name="job-list-create"),
    path("jobs/<uuid:job_id>/", GenerationJobDetailView.as_view(), name="job-detail"),
    path(
        "jobs/<uuid:job_id>/certificates/<uuid:recipient_id>/download/",
        CertificateDownloadView.as_view(),
        name="certificate-download",
    ),
]
