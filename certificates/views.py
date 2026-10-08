from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import GenerationJob, RecipientCertificate
from .serializers import GenerationJobCreateSerializer, GenerationJobSerializer
from .services import process_generation_job

class GenerationJobListCreateView(APIView):
    def post(self, request):
        serializer = GenerationJobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        recipients = data.pop("recipients")
        job = GenerationJob.objects.create(**data, total_count=len(recipients))
        RecipientCertificate.objects.bulk_create(
            [RecipientCertificate(job=job, **recipient) for recipient in recipients]
        )
        process_generation_job(job)
        job.refresh_from_db()
        return Response(
            GenerationJobSerializer(job, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

class GenerationJobDetailView(APIView):
    def get(self, request, job_id):
        job = get_object_or_404(
            GenerationJob.objects.prefetch_related("recipients"), pk=job_id
        )
        return Response(GenerationJobSerializer(job, context={"request": request}).data)

class CertificateDownloadView(APIView):
    def get(self, request, job_id, recipient_id):
        recipient = get_object_or_404(
            RecipientCertificate, pk=recipient_id, job_id=job_id
        )
        if recipient.status != RecipientCertificate.Status.GENERATED or not recipient.file:
            raise Http404("Certificate is not available.")
        return FileResponse(
            recipient.file.open("rb"),
            content_type="application/pdf",
            as_attachment=True,
            filename="certificate-%s.pdf" % recipient.id,
        )
