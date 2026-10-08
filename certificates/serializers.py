from django.urls import reverse
from rest_framework import request, serializers
from .models import GenerationJob, RecipientCertificate

class RecipientInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, allow_blank=False, trim_whitespace=True)
    email = serializers.EmailField(required=False, allow_blank=True)


class GenerationJobCreateSerializer(serializers.Serializer):
    course_name = serializers.CharField(max_length=255, allow_blank=False, trim_whitespace=True)
    completion_date = serializers.DateField()
    issuer_name = serializers.CharField(max_length=255, allow_blank=False, trim_whitespace=True)
    recipients = RecipientInputSerializer(many=True, allow_empty=False)

    def validate_recipients(self, value):
        if len(value) > 1000:
            raise serializers.ValidationError("A maximum of 1000 recipients is supported per job.")
        return value


class RecipientCertificateSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = RecipientCertificate
        fields = ["id", "name", "email", "status", "error_message", "download_url"]

    def get_download_url(self, obj):
        if obj.status != RecipientCertificate.Status.GENERATED or not obj.file:
            return None

        request = self.context.get("request")

        url = reverse(
            "certificate-download",
            kwargs={
                "job_id": obj.job_id,
                "recipient_id": obj.id,
            },
        )

        return request.build_absolute_uri(url) if request else url


class GenerationJobSerializer(serializers.ModelSerializer):
    progress_percent = serializers.SerializerMethodField()
    recipients = RecipientCertificateSerializer(many=True, read_only=True)

    class Meta:
        model = GenerationJob
        fields = [
            "id", "course_name", "completion_date", "issuer_name", "status",
            "total_count", "success_count", "failure_count", "progress_percent",
            "created_at", "completed_at", "recipients",
        ]

    def get_progress_percent(self, obj):
        return round(
            ((obj.success_count + obj.failure_count) / obj.total_count) * 100,
            2,
        ) if obj.total_count else 0
