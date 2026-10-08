from io import BytesIO
from django.core.files.base import ContentFile
from django.utils import timezone
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from .models import GenerationJob, RecipientCertificate

def render_certificate(job, recipient):
    """Render the single predefined certificate design as a PDF."""
    output = BytesIO()
    page_width, page_height = landscape(A4)
    pdf = canvas.Canvas(output, pagesize=(page_width, page_height))
    pdf.setTitle("Certificate - %s" % recipient.name)
    pdf.setStrokeColorRGB(0.12, 0.28, 0.48)
    pdf.setLineWidth(4)
    pdf.rect(28, 28, page_width - 56, page_height - 56)
    pdf.setFillColorRGB(0.12, 0.28, 0.48)
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawCentredString(page_width / 2, page_height - 115, "CERTIFICATE OF COMPLETION")
    pdf.setFillColorRGB(0.15, 0.15, 0.15)
    pdf.setFont("Helvetica", 16)
    pdf.drawCentredString(page_width / 2, page_height - 170, "This certificate is proudly presented to")
    pdf.setFillColorRGB(0.12, 0.28, 0.48)
    pdf.setFont("Helvetica-Bold", 30)
    pdf.drawCentredString(page_width / 2, page_height - 225, recipient.name)
    pdf.setFillColorRGB(0.15, 0.15, 0.15)
    pdf.setFont("Helvetica", 16)
    pdf.drawCentredString(page_width / 2, page_height - 275, "for successfully completing")
    pdf.setFont("Helvetica-Bold", 21)
    pdf.drawCentredString(page_width / 2, page_height - 315, job.course_name)
    pdf.setFont("Helvetica", 13)
    pdf.drawString(80, 85, "Date: %s" % job.completion_date.strftime("%B %d, %Y"))
    pdf.drawRightString(page_width - 80, 85, "Issued by: %s" % job.issuer_name)
    pdf.showPage()
    pdf.save()
    return output.getvalue()

def process_generation_job(job):
    job.status = GenerationJob.Status.PROCESSING
    job.save(update_fields=["status"])
    for recipient in job.recipients.all():
        try:
            content = render_certificate(job, recipient)
            filename = "certificate-%s.pdf" % recipient.id
            recipient.file.save(filename, ContentFile(content), save=False)
            recipient.status = RecipientCertificate.Status.GENERATED
            recipient.error_message = ""
            recipient.save(update_fields=["file", "status", "error_message"])
        except Exception as exc:
            recipient.status = RecipientCertificate.Status.FAILED
            recipient.error_message = str(exc)[:1000]
            recipient.save(update_fields=["status", "error_message"])
    job.success_count = job.recipients.filter(status=RecipientCertificate.Status.GENERATED).count()
    job.failure_count = job.recipients.filter(status=RecipientCertificate.Status.FAILED).count()
    job.status = (
        GenerationJob.Status.COMPLETED
        if job.failure_count == 0
        else GenerationJob.Status.COMPLETED_WITH_ERRORS
    )
    job.completed_at = timezone.now()
    job.save(update_fields=["success_count", "failure_count", "status", "completed_at"])
